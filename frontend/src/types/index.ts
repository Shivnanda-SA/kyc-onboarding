export interface Case {
  id: string;
  jurisdiction: string;
  entity_type: string;
  products_json: string;
  risk_tier: string;
  client_name: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Document {
  id: string;
  case_id: string;
  filename: string;
  stored_path: string;
  content_type: string | null;
  size_bytes: number;
  detected_doc_type: string | null;
  detected_doc_confidence: number | null;
  detected_doc_rationale: string | null;
  created_at: string;
}

export interface CaseDetail {
  case: Case;
  documents: Document[];
}

export interface ExtractedField {
  id: string;
  case_id: string;
  document_id: string;
  doc_type: string;
  field_name: string;
  value: string | null;
  evidence: string | null;
  confidence: number | null;
  created_at: string;
}

export interface ChecklistItem {
  id: string;
  case_id: string;
  doc_type: string;
  required: boolean;
  satisfied: boolean;
  satisfied_by_document_id: string | null;
  created_at: string;
}

export interface GapItem {
  id: string;
  case_id: string;
  kind: 'missing_doc' | 'missing_field' | 'inconsistency';
  item_key: string;
  severity: 'low' | 'medium' | 'high';
  message: string;
  created_at: string;
}

export interface OutreachEmail {
  subject: string;
  body: string;
}

export interface CaseCreateRequest {
  jurisdiction: string;
  entity_type: string;
  products: string[];
  risk_tier: string;
  client_name?: string;
}
