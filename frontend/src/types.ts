export type Determination = "insufficient_evidence" | "not_determined";

export type Citation = {
  chunk_id: string;
  document_id: string;
  document_title: string;
  section_path: string;
  content: string;
};

export type EvidenceItem = {
  statement: string;
  citation_ids: string[];
};

export type InvestigationReport = {
  summary: string;
  determination: Determination;
  supporting_evidence: EvidenceItem[];
  contradicting_evidence: EvidenceItem[];
  policy_and_guidelines: EvidenceItem[];
  missing_information: string[];
  recommended_steps: string[];
  citations: Citation[];
};

export type HistoryTurn = {
  role: "user" | "assistant";
  content: string;
};

export type AskResponse = {
  answer: string;
  citations: Citation[];
};

export type SectionInfo = {
  ordinal: number;
  heading: string;
  section_path: string;
};

export type ChunkRef = {
  id: string;
  section_heading: string;
  section_path: string;
  ordinal: number;
};

export type ChunkDetail = ChunkRef & {
  content: string;
};

export type DocumentSummary = {
  id: string;
  title: string;
  source_path: string;
  sections: SectionInfo[];
  chunks: ChunkRef[];
};

export type DocumentDetail = {
  id: string;
  title: string;
  source_path: string;
  markdown: string;
  sections: SectionInfo[];
  chunks: ChunkDetail[];
  database_available: boolean;
};

export type DocumentListResponse = {
  documents: DocumentSummary[];
  database_available: boolean;
};

export type ErrorDetail = {
  error?: string;
  message?: string;
  missing?: string[];
  command?: string;
  status?: string;
  database?: string;
};
