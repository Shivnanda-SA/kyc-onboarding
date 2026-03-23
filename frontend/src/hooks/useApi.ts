import { useState, useCallback } from 'react';

// In production (Vercel), set VITE_API_BASE to your Render API URL, e.g.
// https://your-backend.onrender.com/api
const API_BASE = (import.meta.env.VITE_API_BASE || '/api').replace(/\/+$/, '');

interface ApiState<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
}

export function useApi<T>() {
  const [state, setState] = useState<ApiState<T>>({
    data: null,
    loading: false,
    error: null,
  });

  const request = useCallback(async <R = T>(
    endpoint: string,
    options?: RequestInit
  ): Promise<R | null> => {
    setState(prev => ({ ...prev, loading: true, error: null }));

    try {
      const response = await fetch(`${API_BASE}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
        },
        ...options,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || `HTTP ${response.status}`);
      }

      const data = await response.json();
      setState({ data, loading: false, error: null });
      return data;
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error';
      setState(prev => ({ ...prev, loading: false, error: errorMessage }));
      return null;
    }
  }, []);

  return { ...state, request };
}

export async function createCase(data: {
  jurisdiction: string;
  entity_type: string;
  products: string[];
  risk_tier: string;
  client_name?: string;
}): Promise<{ case_id: string } | null> {
  const response = await fetch(`${API_BASE}/cases`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });

  if (!response.ok) return null;
  return response.json();
}

export async function getCase(caseId: string): Promise<{
  case: Case;
  documents: Document[];
} | null> {
  const response = await fetch(`${API_BASE}/cases/${caseId}`);
  if (!response.ok) return null;
  return response.json();
}

export async function uploadDocuments(
  caseId: string,
  files: File[]
): Promise<{ uploaded: { document_id: string; filename: string }[] } | null> {
  const formData = new FormData();
  files.forEach(file => formData.append('files', file));

  const response = await fetch(`${API_BASE}/cases/${caseId}/documents`, {
    method: 'POST',
    body: formData,
  });

  if (!response.ok) return null;
  return response.json();
}

export async function processCase(caseId: string): Promise<{ run_id: string } | null> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/process`, {
    method: 'POST',
  });

  if (!response.ok) return null;
  return response.json();
}

export async function getChecklist(caseId: string): Promise<{ items: ChecklistItem[] } | null> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/checklist`);
  if (!response.ok) return null;
  return response.json();
}

export async function getGaps(caseId: string): Promise<{ items: GapItem[] } | null> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/gaps`);
  if (!response.ok) return null;
  return response.json();
}

export async function getFields(caseId: string): Promise<{ items: ExtractedField[] } | null> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/fields`);
  if (!response.ok) return null;
  return response.json();
}

export async function draftEmail(caseId: string): Promise<OutreachEmail | null> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/outreach-email`, {
    method: 'POST',
  });

  if (!response.ok) return null;
  return response.json();
}

export async function sendEmail(caseId: string, data: {
  to: string[];
  cc: string[];
  subject: string;
  body: string;
}): Promise<{ status: string } | null> {
  const response = await fetch(`${API_BASE}/cases/${caseId}/send-email`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!response.ok) return null;
  return response.json();
}

// Type imports for the hook
import type { Case, Document, ExtractedField, ChecklistItem, GapItem, OutreachEmail } from '../types';