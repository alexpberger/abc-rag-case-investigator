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

  useEffect(() => {
    const onHash = () => setTab(tabFromHash());
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);

  function selectTab(next: TabId) {
    window.location.hash = next;
    setTab(next);
  }

  return (
    <>
      <header className="topbar">
        <div className="brand">
          <p className="brand-kicker">Northline Example Mutual</p>
          <h1>Case investigator</h1>
        </div>
        <nav aria-label="Primary">
          {tabs.map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={tab === id ? "tab selected" : "tab"}
              aria-selected={tab === id}
              onClick={() => selectTab(id)}
            >
              {label}
            </button>
          ))}
        </nav>
      </header>
      <main>
        {tab === "investigate" && <InvestigationTab />}
        {tab === "knowledge" && <KnowledgeTab />}
        {tab === "architecture" && <ArchitectureTab />}
      </main>
    </>
  );
}
