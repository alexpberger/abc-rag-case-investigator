import { useEffect, useState } from "react";
import { ApiError, getDocument, getDocuments } from "../api";
import { Markdown } from "../markdown";
import type { DocumentDetail, DocumentSummary } from "../types";

export function KnowledgeTab() {
  const [documents, setDocuments] = useState<DocumentSummary[]>([]);
  const [databaseAvailable, setDatabaseAvailable] = useState(true);
  const [listError, setListError] = useState<Error | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<DocumentDetail | null>(null);
  const [detailError, setDetailError] = useState<Error | null>(null);

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

  return (
    <div className="knowledge">
      <aside className="card doc-list">
        <h2>Sources</h2>
        {listError && (
          <p className="banner" role="alert">
            {listError instanceof ApiError ? listError.message : "The source list could not be loaded."}
          </p>
        )}
        <ul className="doc-nav">
          {documents.map((document) => (
            <li key={document.id}>
              <button
                type="button"
                className={document.id === selectedId ? "doc-button selected" : "doc-button"}
                onClick={() => setSelectedId(document.id)}
              >
                <span>{document.title}</span>
                <small>{document.id}</small>
              </button>
            </li>
          ))}
        </ul>
      </aside>

      <section className="card reader">
        {detailError && (
          <p className="banner" role="alert">
            {detailError.message}
          </p>
        )}
        {!detail && !detailError && <p className="muted">Loading the source…</p>}
        {detail && (
          <>
            <p className="eyebrow">{detail.source_path}</p>
            <h2>{detail.title}</h2>
            <Markdown text={detail.markdown} />
            <details className="source-file">
              <summary>Source file</summary>
              <pre>{detail.markdown}</pre>
            </details>
          </>
        )}
      </section>

      <aside className="card chunk-list">
        <h2>Ingested chunks</h2>
        {!databaseAvailable && (
          <p className="banner" role="alert">
            PostgreSQL is not reachable, so ingested chunk ids cannot be shown. Source text above is read from disk.
          </p>
        )}
        {detail && detail.database_available && detail.chunks.length === 0 && (
          <p className="muted">
            No chunks ingested yet. From the backend directory, run <code>python -m app.rag.ingest</code>.
          </p>
        )}
        {detail && detail.chunks.length > 0 && (
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
      </aside>
    </div>
  );
}
