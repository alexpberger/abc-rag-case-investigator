# ABC RAG Case Investigator

A small, inspectable RAG demo. A fictional personal-loan file at Berger Bank is spread across five Markdown sources. The app retrieves the relevant sections, drafts a structured investigation, and cites the chunks it used.

It does not decide the loan. The report can say the evidence is insufficient. It cannot approve or decline the application.

Read [AGENTS.md](AGENTS.md) for the engineering manual: pipeline, data model, and the decisions later changes should not casually reverse.

## What you need

- Docker, for Postgres with pgvector
- Python 3.12 and [uv](https://docs.astral.sh/uv/)
- Node.js 22
- An Azure OpenAI resource with a chat deployment and a `text-embedding-3-small` embedding deployment

The API and the UI run without Azure. Ingest, investigation, follow-up questions, and the retrieval eval do not.

## One-off setup

From the repository root, create `.env`:

```powershell
Copy-Item .env.example .env
```

```bash
cp .env.example .env
```

Edit `.env` at the repository root. Set `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, and the two deployment names. Use an existing Azure OpenAI account, or create one with the Terraform steps below and copy the outputs into `.env`. Leave `DATABASE_URL` as the local default unless Postgres is not on `127.0.0.1:5432`. The password in the example is the published Docker password for this demo, not an Azure secret.

Do not prefix Azure secrets with `VITE_`. Vite reads the same `.env` file and only exposes variables that start with `VITE_`.

Install dependencies. From `backend`:

```powershell
uv sync --all-extras
```

From `frontend`:

```powershell
npm ci
```

From the repository root, start Postgres:

```powershell
docker compose up -d postgres
```

From `backend`, embed the knowledge base once. Ingest calls Azure and writes vectors to the local database. Run it again only after a file in `knowledge/documents` changes. Add `--force` to re-embed every file.

```powershell
uv run python -m app.rag.ingest
```

## Day-to-day

Postgres keeps running until Docker stops it. Start it when it is not already up:

```powershell
docker compose up -d postgres
```

In one shell, from `backend`:

```powershell
uv run uvicorn app.main:app --reload --port 8000
```

In a second shell, from `frontend`:

```powershell
npm run dev
```

Open http://localhost:5173. The Investigation tab runs the case. The Knowledge tab shows the sources and, after ingest, the chunk ids. The Architecture tab explains the pipeline.

Restart the API after changing `.env`. `--reload` picks up code changes, not environment changes.

## Other ways to run

Inside the devcontainer, Postgres is the hostname `postgres`, and the devcontainer sets `DATABASE_URL` for you. Bind the servers to all interfaces so the forwarded ports work:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`docker compose --profile demo up --build` starts Postgres, the API, and the UI in containers. Create `.env` first. The API container overrides `DATABASE_URL` so it points at the `postgres` service.

## Tests

From `backend`:

```powershell
uv run pytest
```

That run does not call Azure and does not need Postgres. The retrieval eval is separate, because it embeds the fixed queries and reads the local index:

```powershell
$env:RUN_RETRIEVAL_EVAL = "1"
uv run pytest -m eval -s
```

Unset the variable afterwards if you do not want later sessions to call Azure. CI runs `pytest -m "not eval"` and `tsc --noEmit`. It has no Azure secrets.

## Azure OpenAI with Terraform

Terraform in `infra/terraform` creates a resource group, an Azure OpenAI account, and two deployments. It does not create a database, and it does not host the app. It does not print access keys.

```powershell
cd infra/terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`. Change the account name so it is globally unique. Confirm the region and the model version strings against the current Azure OpenAI catalog before you apply. `terraform.tfvars` is gitignored.

```powershell
az login
terraform init
terraform apply
```

If Terraform requires a subscription id, set `ARM_SUBSCRIPTION_ID` in your shell. Do not write it into a file that is committed.

Copy `openai_endpoint` into `AZURE_OPENAI_ENDPOINT`. Copy the deployment name outputs into the matching variables in `.env`. Put the key only in `.env`:

```powershell
az cognitiveservices account keys list --name <account> --resource-group <group> --query key1 -o tsv
```

Local Terraform state can contain secrets even though the outputs do not include the key. State stays uncommitted. There is no remote backend in V1.

## Secrets

`.env`, `*.tfvars`, `.terraform/`, and `*.tfstate` are gitignored. `.env.example` and `terraform.tfvars.example` contain placeholders and the local database password only. The people, the address, and the bank in `knowledge/` are fictional.
