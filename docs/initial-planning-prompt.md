You are working in a new, essentially empty Git repository for a project called `abc-rag-case-investigator`.

The repository will be a **public GitHub repository** supporting an independent Data & AI consultancy portfolio.

Your task is to create a detailed implementation plan and architecture for the project based on the requirements below.

# Project purpose

The project is a small but production-minded RAG demo that demonstrates how a case investigator can investigate a complex case using fragmented source documentation.

The goal is:

> **Small demo. Realistic architecture. Clear extension points.**

The project should demonstrate understanding of the RAG pipeline and AI application architecture rather than simply being a "chat with your PDFs" application.

# Demo scenario

The demo is based on a small synthetic home insurance case.

## Domain

A fictional home insurance company.

## Case

A customer submits a claim for water damage in their home.

The customer claims that the damage was caused by a **sudden pipe leak**.

## Central policy tension

The insurance policy covers:

- Sudden and accidental water damage.

The policy excludes:

- Damage resulting from gradual deterioration or leakage over time.

## Available evidence

The eventual knowledge base will contain a small set of synthetic source documents:

1. Insurance policy
2. Claims investigation guidelines
3. Customer claim
4. Plumber report
5. Claims correspondence

The synthetic documents have **not yet been created**.

The planned evidence should support an investigation where:

- The customer claims sudden damage / a sudden leak.
- The plumber report contains technical observations that may indicate that the underlying problem developed over time.
- The available information contains gaps and ambiguities.

## Expected investigation outcome

The system must **not make the final insurance coverage decision**.

Instead, the primary investigation should be able to conclude something along the lines of:

> The available evidence is insufficient to make a definitive coverage determination.

The system should structure and present:

- Evidence supporting potential coverage
- Evidence potentially contradicting coverage
- Relevant policy and guideline information
- Missing information
- Recommended investigation steps

The synthetic source documents will later be designed to support this coherent scenario.

# Scope

The project is intentionally a **small and transparent demo**.

Do not over-engineer it.

## V1 should include

- A small, static, version-controlled knowledge base
- Markdown source documents
- Document ingestion
- Deterministic section/heading-based chunking
- Azure OpenAI embeddings
- PostgreSQL + pgvector for vector storage and similarity search
- Azure OpenAI for answer generation
- Source citations linking answers back to the relevant document and section
- A structured investigation response for the primary case investigation flow
- A small retrieval evaluation suite
- Clear separation between frontend, backend, RAG/retrieval logic and infrastructure
- Local development through a `.devcontainer`
- Docker / Docker Compose
- Terraform for Azure infrastructure

## Explicitly out of scope for V1

- Authentication
- User management
- Multi-tenancy
- Document upload
- Arbitrary user-provided document ingestion
- PDF ingestion
- Multiple cases
- A large evaluation framework
- Agentic workflows
- Multiple LLM providers

These may be documented as future extension possibilities where appropriate.

# Technology decisions

The following decisions are already made.

## Backend

- Python
- FastAPI

## Frontend

- React
- TypeScript
- Vite

## AI

- Azure OpenAI only for V1
- Azure OpenAI chat model for generation
- Azure OpenAI embedding model for embeddings

Azure credentials are required to run the full application.

Supporting multiple AI providers is out of scope for V1.

## Vector store

- PostgreSQL
- pgvector

The initial implementation intentionally uses PostgreSQL + pgvector to make the retrieval pipeline transparent and locally reproducible.

Azure AI Search should be documented as a possible future extension, including potential support for managed vector and hybrid search.

## Source documents

V1 source documents will be Markdown.

Markdown is intentionally chosen because the synthetic knowledge base should be:

- Transparent
- Easy to inspect on GitHub
- Version-controlled
- Deterministic to ingest and chunk

The ingestion architecture should have clear extension points for future document formats such as PDF, but PDF ingestion should not be implemented in V1.

## Chunking

Use a simple, deterministic chunking strategy based on Markdown headings and sections.

Do not introduce unnecessarily complex semantic chunking in V1.

## Infrastructure

Terraform should provision the required Azure infrastructure.

Local infrastructure should run through Docker / Docker Compose.

At minimum, local development should support PostgreSQL + pgvector.

## Development environment

The project should support development inside a `.devcontainer`.

# Public repository and secrets

This repository will be public.

No private, sensitive, or environment-specific information must be committed to the repository.

The project must use `.gitignore` appropriately to prevent secrets and local configuration from being committed.

This includes, at minimum:

- Azure API keys and secrets
- Connection strings containing credentials
- Azure resource credentials
- Environment variable files such as `.env`
- Local configuration containing sensitive values
- Terraform state files and state backups
- Environment-specific Terraform variable files containing sensitive values
- Any other credentials or private deployment information

Provide safe, version-controlled templates where useful, for example:

- `.env.example`
- Example configuration files containing placeholders only

The repository should document the required environment variables and setup steps without exposing actual secret values.

Terraform code must not contain hard-coded secrets.

Terraform state must not be committed to the public repository.

Synthetic demo data must contain only fictional information and must not contain or expose real customer, employer, client, or personal data.

Appropriate `.gitignore` rules and safe configuration patterns should be included as part of the repository foundation.

# RAG architecture

The intended high-level pipeline is:

```text
Source documents
→ Markdown parsing
→ Section/heading-based chunking
→ Embedding generation using Azure OpenAI
→ PostgreSQL + pgvector
→ Vector similarity retrieval
→ Relevant source chunks
→ Azure OpenAI generation
→ Grounded response with citations
```

The architecture should make the individual steps understandable and independently testable.

# Citations

The backend should be designed so that generated answers can be traced back to source material.

At minimum, citations should contain enough information to identify:

- Source document
- Relevant section
- Relevant chunk/source identifier

The frontend should present source references clearly.

The exact UI design can be proposed during planning.

# Primary UI

The application should have three primary tabs.

## 1. Case Investigation

This is the primary demo experience.

The user should be able to:

- Understand the basic case
- Trigger the main case investigation
- Receive a structured investigation result
- See supporting and contradicting evidence
- See missing information
- See recommended next steps
- Inspect source references
- Ask follow-up questions

The structured output should distinguish between the different investigation categories rather than presenting only a free-form chatbot response.

## 2. Knowledge Base

This tab should make the underlying RAG knowledge base transparent.

The user should be able to inspect the available source documents and understand what information the system is working with.

The design should prioritise transparency and simplicity.

## 3. Architecture

This tab should explain the architecture and RAG pipeline.

It should visually and textually explain:

1. Source documents
2. Markdown parsing and chunking
3. Embeddings
4. PostgreSQL + pgvector
5. Retrieval
6. Azure OpenAI generation
7. Citations

The architecture tab should help someone viewing the demo understand how the system works without needing to inspect the backend code.

# Evaluation

V1 should include a **small retrieval evaluation**.

Keep this intentionally lightweight.

The evaluation should contain a small number of predefined queries and expected relevant documents and/or sections.

The goal is to demonstrate that retrieval quality can be tested independently of answer generation.

Do not build a large RAG evaluation framework.

# AGENTS.md

The project should contain an `AGENTS.md` that serves as the engineering and development manual for humans and AI coding agents working on the repository.

As part of the planning process, propose a clear structure and contents for this file.

It should cover at least:

- Project purpose and scope
- Core user flow
- Architecture principles
- Current architecture
- Technology choices and rationale
- RAG pipeline
- Data and document model
- Citation strategy
- Local development
- Infrastructure and Terraform
- Testing and evaluation principles
- Public repository and secret management
- Important design decisions
- Explicit V1 scope boundaries
- Future extension possibilities

The file should provide enough architectural guidance to keep future development consistent without becoming unnecessarily long or bureaucratic.

# Future extension possibilities

The architecture and `AGENTS.md` should document sensible extension paths without implementing them.

Examples include:

- Azure AI Search
- Hybrid search
- PDF ingestion
- Additional document formats
- Document upload
- Multiple cases
- More advanced RAG evaluation
- Retrieval/debug/observability views
- Authentication
- Agentic investigation workflows

These should remain clearly separated from the V1 scope.

# Your task

Based on the requirements above:

1. Analyse the requirements and identify any contradictions, ambiguities or missing technical decisions that materially affect implementation.
2. Propose a pragmatic repository structure suitable for a small but production-minded demo.
3. Propose the architecture in enough detail to guide implementation.
4. Propose the structure and key contents of `AGENTS.md`.
5. Propose a phased implementation plan with clear milestones.
6. Identify the best point in the implementation plan to design and generate the synthetic source documents.
7. Explain any design choices where there are reasonable alternatives, including trade-offs.
8. Call out anything that appears unnecessarily complex for the stated scope.
9. Keep the plan aligned with the principle:

> **Small demo. Realistic architecture. Clear extension points.**

Prioritise pragmatic decisions over unnecessary abstractions.