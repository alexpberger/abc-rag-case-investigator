# ABC RAG Case Investigator

A small, inspectable RAG demo. A fictional personal-loan file at Example Bank is spread across five Markdown sources. The app retrieves the relevant sections, drafts a structured investigation, and cites the chunks it used.

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

Postgres is the only service this path runs in Docker. The API and the UI run in ordinary terminals on your machine. Leave the devcontainer unused; that option is under Other ways to run.

1. Start Docker Desktop and wait until the engine is running.
2. From the repository root, start Postgres. The container keeps running until Docker stops it, so this is only needed when it is not already up.

   ```powershell
   docker compose up -d postgres
   ```

3. In one shell, from `backend`, start the API. Leave this terminal running.

   ```powershell
   uv run uvicorn app.main:app --reload --port 8000
   ```

4. In a second shell, from `frontend`, start the UI. Leave this terminal running.

   ```powershell
   npm run dev
   ```

5. Open http://localhost:5173 in a browser. That is the site. Port 8000 is the API and has no page of its own. The Investigation tab runs the case. The Knowledge tab shows the sources and, after ingest, the chunk ids. The Architecture tab explains the pipeline.

Restart the API after changing `.env`. `--reload` picks up code changes, not environment changes.

## Other ways to run

Inside the devcontainer, Postgres is the hostname `postgres`, and the devcontainer sets `DATABASE_URL` for you. Bind the servers to all interfaces so the forwarded ports work:

```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

`docker compose --profile demo up --build` starts Postgres, the API, and the UI in containers. Create `.env` first. The API container waits for Postgres, ingests the knowledge base, then starts the API. Unchanged files are not embedded again. The API container overrides `DATABASE_URL` so it points at the `postgres` service. The UI container in this profile is the Vite dev server, on port 5173.

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

Unset the variable afterwards if you do not want later sessions to call Azure. CI runs `pytest -m "not eval"` and `tsc --noEmit` on every push and pull request. Those jobs do not call Azure. A push to `main` then deploys when the app, the knowledge base, or the infra changed.

## Azure OpenAI with Terraform

Terraform in `infra/terraform` creates a resource group, an Azure OpenAI account, and two deployments. The same stack can host the public demo. It does not print access keys.

```powershell
cd infra/terraform
Copy-Item terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars`. Change the account name and the registry name so they are globally unique. Set `github_repository` to `owner/name` for the repository that deploys `main`. Set `budget_alert_email` to the mailbox that should receive the spend alert. Confirm the region and the model version strings against the current Azure OpenAI catalog before you apply. `terraform.tfvars` is gitignored. Do not put the mailbox in a file that is committed.

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

The Container App reads that key from the account. You do not put it in `terraform.tfvars`.

## Public demo

One environment. The site is a Container App with three containers: nginx, the API, and Postgres with pgvector. Only nginx is on the internet. It serves the built UI and proxies `/api` to the API on localhost. Postgres is not published.

The browser and the API share one host, so the production build uses `VITE_API_BASE_URL=same-origin`. Interactive API docs are off. `POST /api/investigate` stops at 100 calls per UTC day, and `POST /api/ask` at 300. Each network also stops at 10 investigations and 30 questions per hour. The counters are in Postgres. If a counter cannot be written, the API returns 503 and does not call Azure. A resource-group budget of $50 emails at 80 percent of actual spend and at 100 percent of forecast spend. The email does not stop the bill. The counters do.

Chat and embedding capacity stay at 10, which is 10,000 tokens per minute. That is a rate ceiling. One replica is the maximum, so the app cannot scale into more concurrent calls.

Postgres data lives on an empty disk that lasts as long as the replica. Azure Files is not a workable Postgres disk because it does not provide the file locks Postgres needs. A new replica runs ingest on startup. Unchanged source files are not embedded again.

Apply the state backend before the apply that creates the Container App. That state holds the database password and the OpenAI key.

```powershell
cd infra/terraform/bootstrap
terraform init
terraform apply
cd ..
Copy-Item backend.tf.example backend.tf
terraform init -migrate-state
```

`backend.tf` names the storage account and uses Azure AD. It does not contain the budget mailbox. The bootstrap grants Storage Blob Data Contributor to the account that applied it.

Leave `deploy_container_app` false for the first apply of `infra/terraform`. That creates the registry and the GitHub Actions identity. The account that applies must be allowed to create role assignments. Role assignment can take a minute before the first workflow login works.

Copy `github_actions_client_id` into the GitHub secret `AZURE_CLIENT_ID`, `tenant_id` into `AZURE_TENANT_ID`, and `subscription_id` into `AZURE_SUBSCRIPTION_ID`. Add a fourth secret, `TF_VARS`, whose value is the contents of `terraform.tfvars`. The tag in that file is only the bootstrap value.

A push to `main` builds both images tagged with the commit SHA and applies Terraform with that tag. The workflow sets `deploy_container_app` to true for that apply. It deploys when `backend/`, `frontend/`, `knowledge/`, `infra/`, or the workflow file changed. Open `container_app_url`. The first request after a new revision waits while ingest embeds the knowledge base. A new revision replaces the replica, so Postgres starts empty.

To roll a commit from your machine after its images exist, run `terraform apply -var="image_tag=<commit>" -var="deploy_container_app=true"`. `infra/scripts/build-images.ps1 -Tag <commit>` pushes those images when you are not using the workflow. The next push to `main` applies that commit's SHA.

## Secrets

`.env`, `*.tfvars`, `.terraform/`, and `*.tfstate` are gitignored. `.env.example` and `terraform.tfvars.example` contain placeholders and the local database password only. The budget mailbox belongs in `terraform.tfvars` and nowhere else. The people, the address, and the bank in `knowledge/` are fictional.
