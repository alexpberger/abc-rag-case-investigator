# AGENTS.md

Engineering manual for this repository. Keep changes inside the V1 boundary unless the task explicitly extends it.

## Purpose

A small RAG demo: a case worker investigates a fictional personal-loan application from fragmented Markdown sources. The product rule is one sentence: investigate and cite; do not decide the loan.

The applicant states long continuous employment, one monthly income figure, and modest obligations. The credit policy takes income, tenure, and obligations from documents in the file. Stated income and irregular overtime are not enough on their own. The income papers and the risk note record differences and do not recommend an outcome. The file is incomplete. A grounded report should be able to say the evidence is insufficient. The server does not write that sentence for the model, and the response schema has no approve or decline value.

## V1 in scope

- Static Markdown knowledge base in git
- Heading-based chunking
- Azure OpenAI embeddings and chat
- PostgreSQL with pgvector, run locally
- Citations back to document, section, and chunk id
- Structured investigation plus follow-up questions
- A six-case retrieval eval, opt-in
- Devcontainer, Docker Compose, Terraform for Azure OpenAI and one public Container App

## V1 out of scope

Authentication, user accounts, multi-tenancy, upload, PDF or other parsers, multiple cases, a large evaluation framework, agentic workflows, more than one model provider, Azure AI Search, a second hosted environment, and Azure Database for PostgreSQL.

## Core flow

1. The Investigation tab shows the case brief from `knowledge/case-brief.md`.
2. Run investigation. The API embeds five fixed queries, merges the hits, and asks the chat deployment for a structured report.
3. The UI separates supporting evidence, concerns, risks, and inconsistencies, policy and guidelines, missing information, and recommended steps. Citation chips open the chunk.
4. Follow-up questions retrieve on the question alone. History stays in the browser and is capped at six turns.
5. The Knowledge tab reads source files from disk and chunk rows from Postgres.
6. The Architecture tab is static. It is not an API.

## Principles

- One visible stage per module. Do not wrap the pipeline in LangChain, LlamaIndex, or a provider interface.
- Chunking stays deterministic. No semantic chunker.
- Cite only ids that were in the retrieved set. Filter on the server. Do not call the model again to repair citations.
- Secrets are never committed. Extension ideas stay as notes in this file, not as unused interfaces.

## Current architecture

```text
knowledge/documents/*.md
  -> app/rag/chunk.py
  -> app/rag/embeddings.py
  -> Postgres (schema.sql)
  -> app/rag/retrieve.py
  -> app/rag/generate.py
  -> app/rag/citations.py
  -> FastAPI
  -> React tabs
```

## Repository map

- `knowledge/` — case brief and the five sources
- `backend/app/rag/` — chunk, embed, ingest, retrieve, generate, citations
- `backend/app/schema.sql` — documents and chunks, vector(1536), no ANN index
- `backend/app/api/routes.py` — HTTP
- `backend/tests/eval/cases.yaml` — retrieval cases
- `frontend/src/tabs/` — Investigation, Knowledge, Architecture
- `infra/terraform/` — resource group and two Azure OpenAI deployments
- `.devcontainer/` — Python 3.12, Node 22, uv, Terraform, Azure CLI
- `docker-compose.yml` — Postgres always; `dev` under profile `devcontainer`; API and UI under profile `demo`

## Technology choices

- FastAPI, psycopg, and SQL. Two tables do not need an ORM. The retrieval query should stay readable.
- `schema.sql` applied at startup and ingest. No Alembic.
- Exact `ORDER BY embedding <=> query`. No HNSW on a few dozen rows.
- A hand-written chunker, so parsing, retrieval, and generation can be tested separately.
- uv and `pyproject.toml` for the backend. Vite, React, and TypeScript for the UI. Plain CSS. Hash tabs, no router.
- Pydantic models for the chat response. One validation retry, then HTTP 502.

## RAG pipeline

Ingest (`python -m app.rag.ingest`) hashes each file. Unchanged files are not re-embedded. `--force` re-embeds everything. Documents removed from `knowledge/documents` are deleted from both tables. Embedding input is the section path plus the chunk body.

Investigation retrieval uses these queries, k=4 each, merged by chunk id, capped at 12, closest cosine distance kept:

- What verified income and employment tenure the credit policy requires
- What stated income or irregular overtime cannot establish on its own
- What the applicant says about employment, income, purpose, and obligations
- What the income documents and the risk note record about pay, tenure, and obligations
- What information the credit policy says is still required before a person decides the loan

Follow-up retrieval embeds the user question only, k=6. The case brief is generator context, not an extra query.

## Document, chunk, and database model

Front matter is `id` and `title` only. `id` is a lowercase slug. Headings of level 1–3 start sections. Deeper headings stay in the body. Text before the first heading is a chunk whose section is the document title. `section_path` joins ancestors with ` / `.

A section of at most 6,000 characters is one chunk. Longer sections split on blank lines with no overlap. A single paragraph longer than the limit splits on character boundaries. Chunk id is `{document_id}/{ordinal}` in document order from 0. Empty heading bodies are omitted; the parent name still appears in the child's path.

`documents.content_hash` is the SHA-256 of the normalized file. `chunks.content_hash` is the hash of the chunk body. Newlines are normalized to `\n` before hashing.

The vector column is `vector(1536)`. `EMBEDDING_DIMENSIONS` must match. Ingest and the embedding call fail if the setting or the returned vector does not.

## Citation strategy

The prompt shows each chunk as `[chunk_id: ...]`. The model returns ids. `filter_citation_ids` drops ids that were not retrieved, and drops duplicates inside one statement. The statement remains when every id is dropped. The report's `citations` list is the retrieved chunks that survived, in first-seen order, with document title, section path, and content.

## API

- `GET /api/health` — process and database. Does not call Azure.
- `GET /api/case` — the case brief
- `GET /api/documents` and `GET /api/documents/{id}` — files from disk; chunk rows from Postgres, empty until ingest
- `POST /api/investigate` — no body
- `POST /api/ask` — `{question, history}`

Missing Azure configuration is 503 and names the variables. An empty chunk table is 409 and names `python -m app.rag.ingest`. Database down on those two routes is 503. Schema failure after the retry is 502. Over the daily or hourly cap, those two routes return 429 and do not call Azure. If the usage counter cannot be written, they return 503 and do not call Azure. Reading the case and the documents is not capped. The public container sets `EXPOSE_API_DOCS=false`.

## Local development

Host workflow: `docker compose up -d postgres`, then uv and Vite as in the README. Day to day, do not start the `dev` service; it belongs to the devcontainer profile.

Devcontainer: reopen the folder in the container. `composeProfiles` includes `devcontainer`, and `runServices` starts `dev` and `postgres`. `remoteEnv` points `DATABASE_URL` at the `postgres` host. `postCreateCommand` installs Python and Node dependencies.

Demo profile: `docker compose --profile demo up --build` after `.env` exists. The API image waits for Postgres and ingests before it serves. The UI image in that profile is the Vite dev server.

## Public site

One Container App in `infra/terraform`: nginx, the API, and Postgres with pgvector. External ingress is nginx on port 80, with TLS at the platform. The API and Postgres are reached on localhost inside the replica. `min_replicas` and `max_replicas` are 1. The production UI is a static build behind nginx, with `VITE_API_BASE_URL=same-origin`.

`POST /api/investigate` allows 100 calls per UTC day and 10 per network per hour. `POST /api/ask` allows 300 and 30. Counters are rows in `api_usage`. The container entrypoint is `python -m app.serve`: wait for Postgres, ingest, then uvicorn. Local `uv run uvicorn` does not ingest.

A push to `main` deploys after the unit tests and the typecheck pass, when `backend/`, `frontend/`, `knowledge/`, `infra/`, or the workflow file changed. The workflow builds both images with the commit SHA and runs `terraform apply` with that tag. The GitHub identity is a user-assigned identity with a federated credential for `refs/heads/main`. The first apply that creates the identity stays local, with `deploy_container_app` false.

The budget mailbox is only in gitignored `terraform.tfvars`. State for this stack belongs in the bootstrap backend because it holds the OpenAI key and the generated Postgres password. There is no output for either secret.

Postgres data is an emptyDir volume. A replacement replica is empty and ingest embeds files whose hashes changed. Azure Database for PostgreSQL is still out of scope.

## Environment variables and Terraform

See `.env.example`. Required for ingest and generation: `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`. Deployment names default to `gpt-4.1` and `text-embedding-3-small`. Confirm those deployments exist in the subscription before you rely on the defaults.

Terraform variables live in gitignored `terraform.tfvars`. Outputs are the endpoint, the two deployment names, the registry, the public URL once the Container App exists, and the GitHub Actions client id, tenant id, and subscription id. Do not add an output for the access key or the database password. The Container App reads the key from the Cognitive Services account. For local ingest, fetch the key with `az cognitiveservices account keys list` and store it in `.env`. Do not commit `terraform.tfstate`. The deploy workflow reads `TF_VARS`, which is a copy of `terraform.tfvars`, and overrides `image_tag` with the commit SHA.

The local database password in Compose and `.env.example` is a published dev default. The public Postgres password is generated by Terraform and stored as a Container App secret.

## Testing and evaluation

CI runs backend unit tests and `tsc --noEmit`. It does not run the retrieval eval. The test jobs do not call Azure. The deploy job on `main` uses GitHub OIDC and the `TF_VARS` secret.

Unit tests cover the chunker, the citation filter, the fan-out merge, the corpus shape, the 503/409 responses, and the usage-limit responses. They do not call the network. `USAGE_LIMITS_ENABLED` defaults to false under pytest so those tests do not need Postgres.

`pytest -m eval` skips unless `RUN_RETRIEVAL_EVAL=1` and Azure plus a non-empty index are available. Each case must find its expected document in the top 8, and a retrieved section path must contain the optional substring. There is no generation score and no judge model.

## Design decisions that should stay

- The determination enum is only `insufficient_evidence` or `not_determined`.
- The summary text comes from the model. Do not hard-code the investigation's conclusion.
- Sources are Markdown in git. The knowledge tab can show them before ingest.
- Vectors stay in Postgres with pgvector. The public demo runs that database in the Container App. Azure Database for PostgreSQL is still a later move.
- The five investigation queries stay a constant. Do not add a planner.
- Follow-up history is client state, capped at six turns. Do not add a conversations table.

## Extension map

These are notes, not tasks.

- Azure AI Search, including hybrid search, can replace the body of `retrieve` without changing the citation contract.
- An HNSW index can be added later. The `<=>` ordering stays.
- PDF and other formats belong behind the reader that produces the same `ParsedDocument` shape. Do not fork the chunker.
- Upload, multiple cases, and authentication need a real tenancy model. V1 has one static case.
- Generation eval, a retrieval debug view, and OpenTelemetry can sit beside the current tests and logs.
- The public demo is one Container App. Azure Database for PostgreSQL, a second environment, and sign-in are still separate work.
- Agentic investigation would replace the fixed query list. That is a different product.
