import { useEffect, useRef, useState, type FormEvent } from "react";
import { ApiError, ask, getCase, investigate } from "../api";
import { Markdown } from "../markdown";
import type { AskResponse, Citation, EvidenceItem, HistoryTurn, InvestigationReport } from "../types";

type TranscriptTurn = {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
};

type CaseFact = {
  label: string;
  value: string;
};

function caseFacts(markdown: string): CaseFact[] {
  const facts: CaseFact[] = [];
  for (const line of markdown.split("\n")) {
    const match = /^- \*\*(.+?):\*\*\s+(.+)$/.exec(line.trim());
    if (match) {
      facts.push({ label: match[1], value: match[2] });
    }
  }
  return facts;
}

function determinationLabel(value: InvestigationReport["determination"]): string {
  if (value === "insufficient_evidence") {
    return "Insufficient evidence";
  }
  return "Not determined";
}

function sentences(text: string): string[] {
  const parts = text.match(/[^.!?]+[.!?]+(?:\s|$)|[^.!?]+$/g) ?? [];
  return parts.map((part) => part.trim()).filter((part) => part.length > 0);
}

function openingSentence(text: string): string {
  return sentences(text)[0] ?? text.trim();
}

function executiveSummary(text: string): string {
  const selected = sentences(text).slice(0, 3);
  return selected.length > 0 ? selected.join(" ") : text.trim();
}

function keyFindings(report: InvestigationReport, shownSummary: string): string[] {
  const selected: string[] = [];
  const add = (candidate: string, limit: number) => {
    if (selected.length >= limit) {
      return;
    }
    if (candidate.length === 0 || shownSummary.includes(candidate) || selected.includes(candidate)) {
      return;
    }
    selected.push(candidate);
  };

  for (const item of report.contradicting_evidence) {
    add(openingSentence(item.statement), 4);
  }
  if (selected.length < 3) {
    for (const item of report.missing_information) {
      add(openingSentence(item), 4);
    }
  }
  if (selected.length < 3) {
    for (const item of report.supporting_evidence) {
      add(openingSentence(item.statement), 4);
    }
  }
  return selected;
}

function ErrorNote({ error }: { error: ApiError | Error }) {
  const detail = error instanceof ApiError ? error.detail : null;
  return (
    <div className="banner" role="alert">
      <p>{error.message}</p>
      {detail?.missing && detail.missing.length > 0 && (
        <p>
          Missing: <code>{detail.missing.join(", ")}</code>
        </p>
      )}
      {detail?.command && (
        <p>
          Run <code>{detail.command}</code> from the backend directory.
        </p>
      )}
    </div>
  );
}

function citationLabel(citation: Citation): string {
  const title = citation.document_title;
  const section = citation.section_path;
  if (section === title || section.startsWith(`${title} / `)) {
    return section;
  }
  return `${title} — ${section}`;
}

function EvidenceList({
  items,
  citations,
  selectedId,
  onCite,
}: {
  items: EvidenceItem[];
  citations: Citation[];
  selectedId: string | null;
  onCite: (citation: Citation) => void;
}) {
  if (items.length === 0) {
    return <p className="muted">Nothing in the retrieved chunks was placed here.</p>;
  }
  const byId = new Map(citations.map((citation) => [citation.chunk_id, citation]));
  return (
    <ul className="evidence">
      {items.map((item, index) => (
        <li key={`${item.statement}-${index}`}>
          <p>
            {item.statement}
            {item.citation_ids.length === 0 && <span className="uncited">No source citation</span>}
            {item.citation_ids.length > 0 && (
              <span className="cites">
                {item.citation_ids.map((id, citationIndex) => {
                  const citation = byId.get(id);
                  return (
                    <span key={id}>
                      {citation ? (
                        <a
                          className="cite"
                          href={`#${citation.chunk_id}`}
                          aria-current={selectedId === citation.chunk_id ? "true" : undefined}
                          onClick={(event) => {
                            event.preventDefault();
                            onCite(citation);
                          }}
                        >
                          {citationIndex > 0 && (
                            <span className="cite-sep" aria-hidden="true">
                              ·{" "}
                            </span>
                          )}
                          <span className="cite-label">{citationLabel(citation)}</span>
                        </a>
                      ) : (
                        <span className="uncited">{id}</span>
                      )}
                    </span>
                  );
                })}
              </span>
            )}
          </p>
        </li>
      ))}
    </ul>
  );
}

export function InvestigationTab() {
  const [brief, setBrief] = useState<string | null>(null);
  const [briefError, setBriefError] = useState<Error | null>(null);
  const [report, setReport] = useState<InvestigationReport | null>(null);
  const [reportError, setReportError] = useState<Error | null>(null);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<Citation | null>(null);
  const [transcript, setTranscript] = useState<TranscriptTurn[]>([]);
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [askError, setAskError] = useState<Error | null>(null);
  const investigationId = useRef(0);

  useEffect(() => {
    let cancelled = false;
    getCase()
      .then((response) => {
        if (!cancelled) {
          setBrief(response.markdown);
        }
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setBriefError(error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  async function onInvestigate() {
    const id = investigationId.current + 1;
    investigationId.current = id;
    setRunning(true);
    setReportError(null);
    setSelected(null);
    setTranscript([]);
    setQuestion("");
    setAskError(null);
    setAsking(false);
    try {
      const next = await investigate();
      if (investigationId.current !== id) {
        return;
      }
      setReport(next);
    } catch (error) {
      if (investigationId.current !== id) {
        return;
      }
      setReport(null);
      setReportError(error as Error);
    } finally {
      if (investigationId.current === id) {
        setRunning(false);
      }
    }
  }

  async function onAsk(event: FormEvent) {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || asking || running || report === null) {
      return;
    }
    const id = investigationId.current;
    setAsking(true);
    setAskError(null);
    const history: HistoryTurn[] = transcript.slice(-6).map((turn) => ({
      role: turn.role,
      content: turn.content,
    }));
    try {
      const response: AskResponse = await ask(trimmed, history);
      if (investigationId.current !== id) {
        return;
      }
      setTranscript((current) => [
        ...current,
        { role: "user", content: trimmed },
        { role: "assistant", content: response.answer, citations: response.citations },
      ]);
      setQuestion("");
    } catch (error) {
      if (investigationId.current !== id) {
        return;
      }
      setAskError(error as Error);
    } finally {
      if (investigationId.current === id) {
        setAsking(false);
      }
    }
  }

  const facts = brief ? caseFacts(brief) : [];
  const shownSummary = report ? executiveSummary(report.summary) : "";
  const findings = report ? keyFindings(report, shownSummary) : [];

  return (
    <div className="split">
      <div className="stack">
        <section className="card">
          <p className="eyebrow">CASE LN-EXAMPLE-2041</p>
          <h2>Case overview</h2>
          <p>
            Imagine you are a case worker reviewing a newly submitted loan application. The following information
            provides an initial overview of the customer and their application, as presented before
            examining the supporting documentation. The information has not yet been independently verified.
          </p>
          {briefError && <ErrorNote error={briefError} />}
          {brief === null && !briefError && <p className="muted">Loading the case overview…</p>}
          {facts.length > 0 && (
            <dl className="facts">
              {facts.map((fact) => (
                <div key={fact.label}>
                  <dt>{fact.label}</dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          )}
          {brief && facts.length === 0 && <Markdown text={brief} />}
        </section>

        <section className="card">
          <p className="eyebrow">Objective</p>
          <h2>Investigation objective</h2>
          <p>
            As the case handler, you are asking the AI assistant to review the loan application against the
            available supporting documents and identify:
          </p>
          <ul className="plain">
            <li>Supporting evidence</li>
            <li>Concerns and inconsistencies</li>
            <li>Missing information</li>
            <li>Recommended next steps</li>
          </ul>
          <p className="disclaimer">The investigation does not make the lending decision.</p>
        </section>

        <section className="card">
          <div className="row">
            <div>
              <h2>Run investigation</h2>
              <p className="muted">Prepare the report from the documents in the file.</p>
            </div>
            <button type="button" className="primary" onClick={onInvestigate} disabled={running}>
              {running ? "Running investigation…" : "Run investigation"}
            </button>
          </div>
          <p className="limit-note">
            The file is fictional. This public demo stops after 100 investigations and 300 follow-up questions in a
            UTC day.
          </p>
          {running && (
            <p className="status" role="status">
              Retrieving sources and drafting the report.
            </p>
          )}
          {reportError && <ErrorNote error={reportError} />}
          {report && (
            <div className="report">
              <section className="report-status" aria-labelledby="investigation-status">
                <p className="eyebrow" id="investigation-status">Investigation status</p>
                <p className="report-status-value">{determinationLabel(report.determination)}</p>
                <p className="disclaimer">This is not a lending decision.</p>
              </section>

              <section className="report-summary" aria-labelledby="executive-summary">
                <h3 id="executive-summary">Executive summary</h3>
                <p className="summary">{shownSummary}</p>
              </section>

              {findings.length > 0 && (
                <section className="report-block report-key" aria-labelledby="key-findings">
                  <h3 id="key-findings">Key findings</h3>
                  <ul className="key-findings">
                    {findings.map((finding) => (
                      <li key={finding}>{finding}</li>
                    ))}
                  </ul>
                </section>
              )}

              <section className="report-block">
                <h3 className="tone-support">Supporting evidence</h3>
                <EvidenceList
                  items={report.supporting_evidence}
                  citations={report.citations}
                  selectedId={selected?.chunk_id ?? null}
                  onCite={setSelected}
                />
              </section>

              <section className="report-block">
                <h3 className="tone-contradict">Concerns, risks and inconsistencies</h3>
                <EvidenceList
                  items={report.contradicting_evidence}
                  citations={report.citations}
                  selectedId={selected?.chunk_id ?? null}
                  onCite={setSelected}
                />
              </section>

              <section className="report-block">
                <h3 className="tone-missing">Missing information</h3>
                {report.missing_information.length === 0 ? (
                  <p className="muted">None listed.</p>
                ) : (
                  <ul className="plain">
                    {report.missing_information.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ul>
                )}
              </section>

              <section className="report-block">
                <h3>Recommended next steps</h3>
                {report.recommended_steps.length === 0 ? (
                  <p className="muted">None listed.</p>
                ) : (
                  <ol>
                    {report.recommended_steps.map((item) => (
                      <li key={item}>{item}</li>
                    ))}
                  </ol>
                )}
              </section>

              <section className="report-block report-reference">
                <details>
                  <summary className="tone-policy">Policy and guidelines</summary>
                  <EvidenceList
                    items={report.policy_and_guidelines}
                    citations={report.citations}
                    selectedId={selected?.chunk_id ?? null}
                    onCite={setSelected}
                  />
                </details>
              </section>
            </div>
          )}
        </section>

        {report && !running && (
          <section className="card">
            <h2>Follow-up</h2>
            <div className="transcript">
              {transcript.length === 0 && (
                <p className="muted">Ask a further question about these findings. Answers stay tied to retrieved chunks.</p>
              )}
              {transcript.map((turn, index) => (
                <article key={`${turn.role}-${index}`} className={turn.role === "user" ? "turn user" : "turn assistant"}>
                  <p className="eyebrow">{turn.role === "user" ? "You" : "Assistant"}</p>
                  <p>{turn.content}</p>
                  {turn.citations && turn.citations.length > 0 && (
                    <div className="chips">
                      {turn.citations.map((citation) => (
                        <button key={citation.chunk_id} type="button" className="chip" onClick={() => setSelected(citation)}>
                          {citation.section_path}
                        </button>
                      ))}
                    </div>
                  )}
                  {turn.role === "assistant" && turn.citations && turn.citations.length === 0 && (
                    <span className="uncited">No source citation</span>
                  )}
                </article>
              ))}
            </div>
            {askError && <ErrorNote error={askError} />}
            <form onSubmit={onAsk} className="ask">
              <label htmlFor="follow-up">Question</label>
              <textarea
                id="follow-up"
                value={question}
                onChange={(event) => setQuestion(event.target.value)}
                rows={3}
                maxLength={2000}
                placeholder="What is still missing before anyone could decide the loan?"
              />
              <button type="submit" className="primary" disabled={asking || question.trim().length === 0}>
                {asking ? "Asking…" : "Ask"}
              </button>
            </form>
          </section>
        )}
      </div>

      <aside className="card citation-panel">
        <h2>Source</h2>
        {selected === null ? (
          <p className="muted">Select a citation to read the chunk the answer used.</p>
        ) : (
          <>
            <p className="eyebrow">{selected.document_title}</p>
            <h3>{selected.section_path}</h3>
            <p className="chunk-id">{selected.chunk_id}</p>
            <blockquote>{selected.content}</blockquote>
          </>
        )}
      </aside>
    </div>
  );
}
