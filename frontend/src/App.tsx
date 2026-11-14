import { useEffect, useState } from "react";
import { ArchitectureTab } from "./tabs/ArchitectureTab";
import { InvestigationTab } from "./tabs/InvestigationTab";
import { KnowledgeTab } from "./tabs/KnowledgeTab";

const tabs = [
  ["investigate", "Investigation"],
  ["knowledge", "Knowledge"],
  ["architecture", "Architecture"],
] as const;

type TabId = (typeof tabs)[number][0];

function tabFromHash(): TabId {
  const hash = window.location.hash.replace("#", "");
  if (hash === "knowledge" || hash === "architecture" || hash === "investigate") {
    return hash;
  }
  return "investigate";
}

export function App() {
  const [tab, setTab] = useState<TabId>(tabFromHash);
  const current = tabs.find(([id]) => id === tab) ?? tabs[0];

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  useEffect(() => {
    document.title = `${current[1]} — Case investigator`;
  }, [current]);

  function selectTab(next: TabId) {
    window.location.hash = next;
    setTab(next);
  }

  return (
    <div className="shell">
      <nav className="nav" aria-label="Primary">
        {tabs.map(([id, label]) => (
          <button
            key={id}
            type="button"
            className={tab === id ? "active" : undefined}
            aria-current={tab === id ? "page" : undefined}
            onClick={() => selectTab(id)}
          >
            {label}
          </button>
        ))}
      </nav>
      <div className="main">
        <header className="header">
          <div>
            <p className="section-label">Case investigator</p>
            <p className="brand-line">Northline Example Mutual</p>
          </div>
        </header>
        <div className="intro">
          <h1>{current[1]}</h1>
          <hr className="accent-rule" />
        </div>
        {tab === "investigate" && <InvestigationTab />}
        {tab === "knowledge" && <KnowledgeTab />}
        {tab === "architecture" && <ArchitectureTab />}
      </div>
    </div>
  );
}
