import { useEffect, useState } from "react";
import { ApiError, getDocument, getDocuments } from "../api";
import { Markdown } from "../markdown";
import type { DocumentDetail, DocumentSummary } from "../types";

const documentKinds: Record<string, string> = {
  "credit-policy": "Policy",
  "loan-application": "Application",
  "income-documentation": "Income papers",
  "credit-risk-assessment": "Risk note",
  "customer-correspondence": "Correspondence",
};

function documentKind(id: string): string | null {
  return documentKinds[id] ?? null;
}

export function KnowledgeTab() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [databaseAvailable, setDatabaseAvailable] = useState(true);
  const [listError, setListError] = useState<Error | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [detailError, setDetailError] = useState<Error | null>(null);
  const [chunksOpen, setChunksOpen] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getDocuments()
      .then((response) => {
        if (cancelled) {
          return;
        }
        setDocuments(response.documents);
        setDatabaseAvailable(response.database_available);
        setSelectedId((current) => current ?? response.documents[0]?.id ?? null);
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setListError(error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!selectedId) {
      return;
    }
    let cancelled = false;
    setDetail(null);
    setDetailError(null);
    getDocument(selectedId)
      .then((response) => {
        if (!cancelled) {
          setDetail(response);
        }
      })
      .catch((error: Error) => {
        if (!cancelled) {
          setDetailError(error);
        }
      });
    return () => {
      cancelled = true;
    };
  }, [selectedId]);

  const kind = detail ? documentKind(detail.id) : null;

  return (
    <div className="knowledge">
      <p className="knowledge-lead">
        Explore the source documents available to the RAG system and how they are organised into retrievable chunks.
      </p>

      <nav className="card doc-list" aria-label="Document library">
        <h2>Document library</h2>
        {listError && (
          <p className="banner" role="alert">
            {listError instanceof ApiError ? listError.message : "The source list could not be loaded."}
          </p>
        )}
        {documents.length === 0 && !listError && <p className="muted">Loading the library…</p>}
        <ul className="doc-nav">
          {documents.map((document) => {
            const label = documentKind(document.id);
            const selected = document.id === selectedId;
            return (
              <li key={document.id}>
                <button
                  type="button"
                  className={selected ? "doc-button selected" : "doc-button"}
                  aria-current={selected ? "true" : undefined}
                  onClick={() => setSelectedId(document.id)}
                >
                  <span>{document.title}</span>
                  {label && <small>{label}</small>}
                </button>
              </li>
            );
          })}
        </ul>
      </nav>

      <section className="card reader" aria-labelledby={detail ? "selected-document" : undefined}>
        {detailError && (
          <p className="banner" role="alert">
            {detailError.message}
          </p>
        )}
        {!detail && !detailError && <p className="muted">Loading the source…</p>}
        {detail && (
          <>
            {kind && <p className="eyebrow">{kind}</p>}
            <h2 id="selected-document">{detail.title}</h2>
            <Markdown text={detail.markdown} />
            <details
              className="indexed-chunks"
              open={chunksOpen}
              onToggle={(event) => setChunksOpen(event.currentTarget.open)}
            >
              <summary>View indexed chunks</summary>
              {!databaseAvailable && (
                <p className="banner" role="alert">
                  PostgreSQL is not reachable, so ingested chunk ids cannot be shown. Source text above is read from disk.
                </p>
              )}
              {detail.database_available && detail.chunks.length === 0 && (
                <p className="muted">
                  No chunks ingested yet. From the backend directory, run <code>python -m app.rag.ingest</code>.
                </p>
              )}
              {detail.chunks.length > 0 && (
                <ol className="chunks">
                  {detail.chunks.map((chunk) => (
                    <li key={chunk.id}>
                      <p className="chunk-id">{chunk.id}</p>
                      <p>{chunk.section_path}</p>
                      <pre>{chunk.content}</pre>
                    </li>
                  ))}
                </ol>
              )}
            </details>
          </>
        )}
      </section>
    </div>
  );
}
