const stages = [
  {
    title: "Documents",
    body: (
      <>
        The five sources are split on headings into sections, each with a stable id such as{" "}
        <code>credit-policy/4</code>.
      </>
    ),
  },
  {
    title: "Embeddings",
    body: "Each section, including its heading path, is embedded with Azure OpenAI and stored in Postgres.",
  },
  {
    title: "Retrieval",
    body: "An investigation runs five fixed questions and keeps up to twelve sections. A follow-up question searches on that question alone.",
  },
  {
    title: "Report",
    body: "Azure OpenAI writes the structured investigation from those sections and the case brief: supporting evidence, concerns, policy, missing information, and recommended steps. The status is insufficient evidence or not determined.",
  },
  {
    title: "Citations",
    body: "A citation is kept only when its id was among the retrieved sections. The panel shows the document, the section, and the text.",
  },
];

export function ArchitectureTab() {
  return (
    <div className="architecture">
      <div className="about-lead">
        <p>
          The page is React and TypeScript. The API is Python and FastAPI. An investigation embeds a small set of
          questions, retrieves the closest sections from PostgreSQL with pgvector, and asks Azure OpenAI for a
          structured report.
        </p>
        <p>
          The case file is five Markdown documents shipped with the application: the credit policy, the loan
          application, the income documents, the risk note, and the correspondence. Each section is embedded and stored
          with the application.
        </p>
        <p>
          The public site is one Azure Container App. The page, the API, and Postgres run together. Terraform describes
          those Azure resources. The source is{" "}
          <a href="https://github.com/alexpberger/abc-rag-case-investigator">
            github.com/alexpberger/abc-rag-case-investigator
          </a>
          .
        </p>
      </div>
      <section className="card">
        <h2>How a run works</h2>
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
        <h2>This version</h2>
        <p>One public demonstration of a single fictional case. No sign-in and no document upload.</p>
        <p>
          The investigation organises what the file supports and what is still missing. It does not approve or decline
          the loan.
        </p>
        <p>
          Public use is limited to 100 investigations and 300 follow-up questions per day, with a tighter hourly limit,
          so the demonstration stays available.
        </p>
        <p>Accounts, further cases, other document formats, and other model providers sit outside this version.</p>
      </section>
    </div>
  );
}
