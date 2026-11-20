const perspectives = [
  {
    tab: "Investigation",
    perspective: "Business perspective",
    body: "Investigate a customer case using AI and supporting documents.",
  },
  {
    tab: "Knowledge",
    perspective: "Data perspective",
    body: "Explore the source documents and how they are organised into retrievable chunks.",
  },
  {
    tab: "Architecture",
    perspective: "Technical perspective",
    body: "Understand the RAG pipeline, its individual stages and underlying technologies.",
  },
];

export function AboutTab() {
  return (
    <div className="about">
      <div className="about-lead">
        <p>
          This is a RAG-based case investigation application. It uses information from multiple source
          documents to investigate a customer case, identify supporting evidence, concerns,
          inconsistencies and missing information, and recommend next steps.
        </p>
        <p>
          Answers are grounded in the retrieved documents and supported by citations. The application
          does not make the final lending decision.
        </p>
      </div>
      <ul className="about-perspectives">
        {perspectives.map((item) => (
          <li key={item.tab} className="card">
            <p className="eyebrow">{item.perspective}</p>
            <h2>{item.tab}</h2>
            <p>{item.body}</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
