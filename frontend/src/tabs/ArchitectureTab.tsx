const stages = [
  {
    title: "Source documents",
    body: "Five Markdown files in the repository: the credit policy, the loan application, the income documents, the risk assessment, and the correspondence. They are fictional, versioned, and readable on GitHub.",
  },
  {
    title: "Markdown parsing and chunking",
    body: "Each file has id and title in front matter. The chunker splits on headings through level 3 and keeps the heading path, such as Eligibility / Verified income and employment. A section under 6,000 characters is one chunk. Longer sections split on blank lines, with no overlap. Chunk ids look like credit-policy/4.",
  },
  {
    title: "Embeddings",
    body: "Azure OpenAI embeds each chunk, including its section path, with text-embedding-3-small (1,536 dimensions). Ingest skips a document whose file hash has not changed. The deployment name comes from the environment, not from the code.",
  },
  {
    title: "PostgreSQL and pgvector",
    body: "Chunks live in local Postgres. The embedding column is vector(1536). There is no approximate index: a few dozen rows are ordered exactly. Azure Database for PostgreSQL is a later option, not part of this demo.",
  },
  {
    title: "Retrieval",
    body: "The investigation runs five fixed queries and merges the closest chunks, keeping at most twelve. A follow-up question uses one query and six chunks. The queries are written in the retrieval module. Nothing plans them at runtime.",
  },
  {
    title: "Azure OpenAI generation",
    body: "The chat deployment writes a structured report: summary, supporting evidence, concerns, risks, and inconsistencies, policy and guidelines, missing information, and recommended steps. The status can be insufficient evidence or not determined. It cannot be approve or decline.",
  },
  {
    title: "Citations",
    body: "The model may cite only chunk ids it was given. The server drops any other id and still keeps the sentence. The citation panel shows the document, the section path, the chunk id, and the text.",
  },
];

export function ArchitectureTab() {
  return (
    <div className="stack architecture">
      <section className="card">
        <p className="eyebrow">How a run works</p>
        <h2>Pipeline</h2>
        <p>
          The corpus is small on purpose so each stage can be inspected. Retrieval still selects a subset of the chunks. The same stages are what you would keep if the library grew.
        </p>
        <ol className="pipeline">
          {stages.map((stage, index) => (
            <li key={stage.title}>
              <span className="stage-index">{index + 1}</span>
              <div>
                <h3>{stage.title}</h3>
                <p>{stage.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </section>
      <section className="card boundary">
        <h2>V1 boundary</h2>
        <p>Local Postgres. No document upload. No lending decision. Azure OpenAI is the only model provider. Authentication, PDF ingestion, hybrid search, and agentic workflows are documented as later work, not built here.</p>
      </section>
    </div>
  );
}
