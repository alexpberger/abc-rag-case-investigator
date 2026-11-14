import pytest
from fastapi.testclient import TestClient

from app.api import routes
from app.main import app
from app.schemas import AskResponse, Citation, EvidenceItem, InvestigationReport


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_reports_database_state(monkeypatch, client):
    monkeypatch.setattr(routes, "database_ok", lambda: True)
    ok = client.get("/api/health")
    assert ok.status_code == 200
    assert ok.json() == {"status": "ok", "database": "ok"}

    monkeypatch.setattr(routes, "database_ok", lambda: False)
    down = client.get("/api/health")
    assert down.status_code == 503
    assert down.json()["detail"]["database"] == "unavailable"


def test_investigate_requires_azure(monkeypatch, client):
    monkeypatch.setattr(routes, "missing_azure", lambda: ["AZURE_OPENAI_API_KEY"])
    response = client.post("/api/investigate")
    assert response.status_code == 503
    detail = response.json()["detail"]
    assert detail["error"] == "azure_not_configured"
    assert detail["missing"] == ["AZURE_OPENAI_API_KEY"]


def test_ask_conflict_when_the_index_is_empty(monkeypatch, client):
    monkeypatch.setattr(routes, "missing_azure", lambda: [])
    monkeypatch.setattr(routes, "ingestion_status", lambda: "empty")
    response = client.post("/api/ask", json={"question": "Who decides coverage?"})
    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["error"] == "knowledge_base_not_ingested"
    assert detail["command"] == "python -m app.rag.ingest"


def test_ask_when_postgres_is_down(monkeypatch, client):
    monkeypatch.setattr(routes, "missing_azure", lambda: [])
    monkeypatch.setattr(routes, "ingestion_status", lambda: "unavailable")
    response = client.post("/api/ask", json={"question": "Who decides coverage?"})
    assert response.status_code == 503
    assert response.json()["detail"]["error"] == "database_unavailable"


def test_investigate_returns_the_grounded_report(monkeypatch, client):
    report = InvestigationReport(
        summary="The file does not establish the cause.",
        determination="insufficient_evidence",
        supporting_evidence=[
            EvidenceItem(statement="The customer reported a sudden leak.", citation_ids=["customer-claim/0"])
        ],
        contradicting_evidence=[],
        policy_and_guidelines=[],
        missing_information=["Pipe age"],
        recommended_steps=["Request maintenance records"],
        citations=[
            Citation(
                chunk_id="customer-claim/0",
                document_id="customer-claim",
                document_title="Customer Claim Statement",
                section_path="What the customer reported",
                content="A sudden leak.",
            )
        ],
    )
    monkeypatch.setattr(routes, "require_retrieval_ready", lambda: None)
    monkeypatch.setattr(routes, "run_investigation", lambda: report)
    response = client.post("/api/investigate")
    assert response.status_code == 200
    body = response.json()
    assert body["determination"] == "insufficient_evidence"
    assert body["summary"] == report.summary
    assert "covered" not in body["determination"]
    assert body["citations"][0]["chunk_id"] == "customer-claim/0"


def test_case_and_documents_are_served_from_disk(client):
    case = client.get("/api/case")
    assert case.status_code == 200
    assert "Northline Example Mutual" in case.json()["markdown"]

    listing = client.get("/api/documents")
    assert listing.status_code == 200
    assert [document["id"] for document in listing.json()["documents"]] == [
        "insurance-policy",
        "claims-guidelines",
        "customer-claim",
        "plumber-report",
        "claims-correspondence",
    ]

    missing = client.get("/api/documents/does-not-exist")
    assert missing.status_code == 404


def test_ask_response_shape(monkeypatch, client):
    monkeypatch.setattr(routes, "require_retrieval_ready", lambda: None)
    monkeypatch.setattr(
        routes,
        "run_ask",
        lambda request: AskResponse(answer="A person decides.", citations=[]),
    )
    response = client.post(
        "/api/ask",
        json={
            "question": "Who makes the coverage decision?",
            "history": [{"role": "user", "content": "Earlier question"}, {"role": "assistant", "content": "Earlier answer"}],
        },
    )
    assert response.status_code == 200
    assert response.json()["answer"] == "A person decides."
