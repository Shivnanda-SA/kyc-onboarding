import { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { 
  FileText, CheckCircle, AlertCircle, Mail, RefreshCw, 
  FileCheck, AlertTriangle, Building2, Globe, Shield 
} from 'lucide-react';
import { getCase, getChecklist, getGaps, getFields, draftEmail, sendEmail } from '../hooks/useApi';
import type { Case, Document, ChecklistItem, GapItem, ExtractedField, OutreachEmail } from '../types';

type Tab = 'overview' | 'checklist' | 'gaps' | 'fields' | 'email';

export default function CaseResults() {
  const { caseId } = useParams<{ caseId: string }>();
  const [activeTab, setActiveTab] = useState<Tab>('overview');
  
  const [caseData, setCaseData] = useState<{ case: Case; documents: Document[] } | null>(null);
  const [checklist, setChecklist] = useState<ChecklistItem[]>([]);
  const [gaps, setGaps] = useState<GapItem[]>([]);
  const [fields, setFields] = useState<ExtractedField[]>([]);
  const [email, setEmail] = useState<OutreachEmail | null>(null);
  const [emailLoading, setEmailLoading] = useState(false);
  const [emailError, setEmailError] = useState<string | null>(null);
  const [emailTo, setEmailTo] = useState('');
  const [emailCc, setEmailCc] = useState('');
  const [emailSending, setEmailSending] = useState(false);
  const [emailSendMessage, setEmailSendMessage] = useState<string | null>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadData = async () => {
    if (!caseId) return;
    
    setLoading(true);
    setError(null);
    try {
      const [caseResult, checklistResult, gapsResult, fieldsResult] = await Promise.all([
        getCase(caseId),
        getChecklist(caseId),
        getGaps(caseId),
        getFields(caseId),
      ]);
      
      if (caseResult) {
        setCaseData(caseResult);
      } else {
        setError('Failed to load case data');
      }
      if (checklistResult) setChecklist(checklistResult.items);
      if (gapsResult) setGaps(gapsResult.items);
      if (fieldsResult) setFields(fieldsResult.items);
    } catch (err) {
      setError('An error occurred while loading case data');
    } finally {
      setLoading(false);
    }
  };

  const generateEmail = async () => {
    if (!caseId) return;
    setEmailLoading(true);
    setEmailError(null);
    setEmailSendMessage(null);
    try {
      const result = await draftEmail(caseId);
      if (result) {
        setEmail(result);
        setActiveTab('email');
      } else {
        setEmailError('Failed to generate email. Please try again.');
      }
    } catch (err) {
      setEmailError('An error occurred while generating the email.');
    } finally {
      setEmailLoading(false);
    }
  };

  const handleSendEmail = async () => {
    if (!caseId || !email) return;
    const toList = emailTo.split(',').map(s => s.trim()).filter(Boolean);
    const ccList = emailCc.split(',').map(s => s.trim()).filter(Boolean);
    if (toList.length === 0) {
      setEmailSendMessage('Please enter at least one recipient in "To".');
      return;
    }
    setEmailSending(true);
    setEmailSendMessage(null);
    const res = await sendEmail(caseId, {
      to: toList,
      cc: ccList,
      subject: email.subject,
      body: email.body,
    });
    if (res) {
      setEmailSendMessage('Email recorded as sent (POC).');
    } else {
      setEmailSendMessage('Failed to send email. Please try again.');
    }
    setEmailSending(false);
  };

  useEffect(() => {
    loadData();
  }, [caseId]);

  // Auto-generate email when user opens the Outreach Email tab.
  useEffect(() => {
    if (!caseId) return;
    if (activeTab !== 'email') return;
    if (email || emailLoading) return;
    void generateEmail();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, caseId]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="w-8 h-8 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin" />
      </div>
    );
  }

  if (error || !caseData) {
    return (
      <div className="max-w-3xl mx-auto p-8">
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
          {error || 'Failed to load case data'}
        </div>
      </div>
    );
  }

  const { case: c, documents } = caseData;
  const satisfiedCount = checklist.filter(i => i.satisfied).length;
  const totalRequired = checklist.filter(i => i.required).length;

  const tabs = [
    { id: 'overview' as Tab, label: 'Overview', icon: Building2 },
    { id: 'checklist' as Tab, label: 'Checklist', icon: FileCheck },
    { id: 'gaps' as Tab, label: `Gaps (${gaps.length})`, icon: AlertTriangle },
    { id: 'fields' as Tab, label: 'Extracted Fields', icon: FileText },
    { id: 'email' as Tab, label: 'Outreach Email', icon: Mail },
  ];

  return (
    <div className="max-w-6xl mx-auto">
      {/* Header */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6 mb-6">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3 mb-2">
              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                c.status === 'complete' ? 'bg-green-100 text-green-700' :
                c.status === 'processing' ? 'bg-yellow-100 text-yellow-700' :
                c.status === 'failed' ? 'bg-red-100 text-red-700' :
                'bg-gray-100 text-gray-700'
              }`}>
                {c.status}
              </span>
              <span className="text-sm text-gray-500">Case ID: {c.id}</span>
            </div>
            <h1 className="text-2xl font-semibold text-gray-900">
              {c.client_name || 'Untitled Case'}
            </h1>
            <div className="flex items-center gap-4 mt-3 text-sm text-gray-600">
              <span className="flex items-center gap-1">
                <Globe className="w-4 h-4" />
                {c.jurisdiction}
              </span>
              <span className="flex items-center gap-1">
                <Building2 className="w-4 h-4" />
                {c.entity_type}
              </span>
              <span className="flex items-center gap-1">
                <Shield className="w-4 h-4" />
                {c.risk_tier} risk
              </span>
            </div>
          </div>
          
          <button
            onClick={loadData}
            className="flex items-center gap-2 px-4 py-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Refresh
          </button>
        </div>

        {/* Progress */}
        <div className="mt-6 pt-6 border-t border-gray-200">
          <div className="flex items-center justify-between text-sm mb-2">
            <span className="text-gray-600">Document Completion</span>
            <span className="font-medium text-gray-900">
              {satisfiedCount} / {totalRequired} required documents
            </span>
          </div>
          <div className="w-full bg-gray-200 rounded-full h-2">
            <div
              className="bg-primary-600 h-2 rounded-full transition-all"
              style={{ width: `${totalRequired > 0 ? (satisfiedCount / totalRequired) * 100 : 0}%` }}
            />
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="flex border-b border-gray-200 overflow-x-auto">
          {tabs.map(tab => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`flex items-center gap-2 px-6 py-4 text-sm font-medium border-b-2 transition-colors whitespace-nowrap ${
                activeTab === tab.id
                  ? 'border-primary-600 text-primary-600'
                  : 'border-transparent text-gray-600 hover:text-gray-900'
              }`}
            >
              <tab.icon className="w-4 h-4" />
              {tab.label}
            </button>
          ))}
        </div>

        <div className="p-6">
          {/* Overview Tab */}
          {activeTab === 'overview' && (
            <div className="space-y-6">
              {/* Documents */}
              <div>
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Uploaded Documents</h3>
                {documents.length === 0 ? (
                  <p className="text-gray-500">No documents uploaded yet.</p>
                ) : (
                  <div className="grid gap-3">
                    {documents.map(doc => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between p-4 bg-gray-50 rounded-lg"
                      >
                        <div className="flex items-center gap-3">
                          <FileText className="w-5 h-5 text-gray-400" />
                          <div>
                            <p className="font-medium text-gray-900">{doc.filename}</p>
                            <p className="text-sm text-gray-500">
                              {doc.detected_doc_type || 'Type pending'} • {new Date(doc.created_at).toLocaleDateString()}
                            </p>
                          </div>
                        </div>
                        {doc.detected_doc_type && doc.detected_doc_type !== 'unknown' ? (
                          <CheckCircle className="w-5 h-5 text-green-500" />
                        ) : (
                          <AlertCircle className="w-5 h-5 text-yellow-500" />
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Quick Stats */}
              <div className="grid grid-cols-3 gap-4">
                <div className="p-4 bg-green-50 rounded-lg">
                  <p className="text-2xl font-bold text-green-700">{satisfiedCount}</p>
                  <p className="text-sm text-green-600">Documents Complete</p>
                </div>
                <div className="p-4 bg-red-50 rounded-lg">
                  <p className="text-2xl font-bold text-red-700">{gaps.length}</p>
                  <p className="text-sm text-red-600">Gaps Identified</p>
                </div>
                <div className="p-4 bg-blue-50 rounded-lg">
                  <p className="text-2xl font-bold text-blue-700">{fields.length}</p>
                  <p className="text-sm text-blue-600">Fields Extracted</p>
                </div>
              </div>

              {/* Action */}
              {gaps.length > 0 && (
                <div className="flex flex-col gap-3">
                  <div className="flex gap-3">
                    <button
                      onClick={generateEmail}
                      disabled={emailLoading}
                      className="flex items-center gap-2 bg-primary-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {emailLoading ? (
                        <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                      ) : (
                        <Mail className="w-4 h-4" />
                      )}
                      {emailLoading ? 'Generating...' : 'Draft Outreach Email'}
                    </button>
                    <button
                      onClick={() => setActiveTab('gaps')}
                      className="flex items-center gap-2 bg-white border border-gray-300 text-gray-700 py-2 px-4 rounded-lg font-medium hover:bg-gray-50 transition-colors"
                    >
                      <AlertTriangle className="w-4 h-4" />
                      View Gaps
                    </button>
                  </div>
                  {emailError && (
                    <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                      {emailError}
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Checklist Tab */}
          {activeTab === 'checklist' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Document Status</h3>

              <div className="mb-6">
                <h4 className="text-sm font-medium text-gray-700 mb-3">Uploaded Documents ({documents.length})</h4>
                {documents.length === 0 ? (
                  <p className="text-gray-500 text-sm">No documents uploaded yet.</p>
                ) : (
                  <div className="space-y-2">
                    {documents.map(doc => (
                      <div
                        key={doc.id}
                        className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border border-gray-200"
                      >
                        <div className="flex items-center gap-3">
                          <FileText className="w-5 h-5 text-gray-400" />
                          <div>
                            <p className="font-medium text-gray-900">{doc.filename}</p>
                            <p className="text-sm text-gray-500">
                              {doc.detected_doc_type ? doc.detected_doc_type.replace(/_/g, ' ') : 'Type pending'} •{' '}
                              {(doc.size_bytes / 1024).toFixed(1)} KB
                            </p>
                            {doc.detected_doc_rationale && (
                              <p className="text-xs text-gray-500 mt-1">
                                Why: {doc.detected_doc_rationale}
                              </p>
                            )}
                          </div>
                        </div>
                        {doc.detected_doc_type && doc.detected_doc_type !== 'unknown' ? (
                          <span className="px-2 py-1 bg-green-100 text-green-700 text-xs rounded-full">
                            Detected{doc.detected_doc_confidence != null ? ` ${(doc.detected_doc_confidence * 100).toFixed(0)}%` : ''}
                          </span>
                        ) : (
                          <span className="px-2 py-1 bg-yellow-100 text-yellow-700 text-xs rounded-full">Pending</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {checklist.length === 0 && documents.length > 0 && (
                <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
                  <p className="text-yellow-800 font-medium">No checklist generated yet</p>
                  <p className="text-yellow-700 text-sm mt-1">
                    This usually means the rules did not match the selected entity type/products. Try “Process” again
                    after restarting the backend, or create a new case with a supported entity type.
                  </p>
                </div>
              )}

              {checklist.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-3">Requirements Checklist ({checklist.length})</h4>
                  <div className="space-y-3">
                    {checklist.map(item => (
                      <div
                        key={item.id}
                        className={`flex items-center justify-between p-4 rounded-lg border ${
                          item.satisfied ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                        }`}
                      >
                        <div className="flex items-center gap-3">
                          {item.satisfied ? (
                            <CheckCircle className="w-5 h-5 text-green-600" />
                          ) : (
                            <AlertCircle className="w-5 h-5 text-red-600" />
                          )}
                          <div>
                            <p className={`font-medium ${item.satisfied ? 'text-green-900' : 'text-red-900'}`}>
                              {item.doc_type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}
                            </p>
                            <p className={`text-sm ${item.satisfied ? 'text-green-700' : 'text-red-700'}`}>
                              {item.satisfied ? '✓ Satisfied' : '✗ Missing'}
                            </p>
                          </div>
                        </div>
                        {item.satisfied ? (
                          <span className="text-sm text-green-700 font-medium">Uploaded</span>
                        ) : (
                          <span className="text-sm text-red-700 font-medium">Required</span>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Gaps Tab */}
          {activeTab === 'gaps' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Identified Gaps</h3>
              {gaps.length === 0 ? (
                <div className="p-8 text-center">
                  <CheckCircle className="w-12 h-12 text-green-500 mx-auto mb-4" />
                  <p className="text-gray-900 font-medium">No gaps found</p>
                  <p className="text-gray-500 text-sm mt-1">All required documents and fields are present.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {gaps.map(gap => (
                    <div
                      key={gap.id}
                      className={`p-4 rounded-lg border ${
                        gap.severity === 'high'
                          ? 'bg-red-50 border-red-200'
                          : gap.severity === 'medium'
                          ? 'bg-yellow-50 border-yellow-200'
                          : 'bg-blue-50 border-blue-200'
                      }`}
                    >
                      <div className="flex items-start gap-3">
                        <AlertTriangle className={`w-5 h-5 flex-shrink-0 ${
                          gap.severity === 'high' ? 'text-red-600' :
                          gap.severity === 'medium' ? 'text-yellow-600' : 'text-blue-600'
                        }`} />
                        <div>
                          <p className={`font-medium ${
                            gap.severity === 'high' ? 'text-red-900' :
                            gap.severity === 'medium' ? 'text-yellow-900' : 'text-blue-900'
                          }`}>
                            {gap.message}
                          </p>
                          <p className="text-sm mt-1 text-gray-600">
                            Type: {gap.kind.replace('_', ' ')} • Severity: {gap.severity}
                          </p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Fields Tab */}
          {activeTab === 'fields' && (
            <div>
              <h3 className="text-lg font-semibold text-gray-900 mb-4">Extracted Fields</h3>
              {fields.length === 0 ? (
                <p className="text-gray-500">No fields extracted yet.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="w-full">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="text-left p-3 text-sm font-medium text-gray-700">Field</th>
                        <th className="text-left p-3 text-sm font-medium text-gray-700">Document Type</th>
                        <th className="text-left p-3 text-sm font-medium text-gray-700">Value</th>
                        <th className="text-left p-3 text-sm font-medium text-gray-700">Confidence</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {fields.map(field => (
                        <tr key={field.id} className="hover:bg-gray-50">
                          <td className="p-3 text-sm font-medium text-gray-900">
                            {field.field_name}
                          </td>
                          <td className="p-3 text-sm text-gray-600">
                            {field.doc_type.replace(/_/g, ' ')}
                          </td>
                          <td className="p-3 text-sm text-gray-900">
                            {field.value || <span className="text-gray-400 italic">Not found</span>}
                          </td>
                          <td className="p-3 text-sm">
                            {field.confidence ? (
                              <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                                field.confidence >= 0.8 ? 'bg-green-100 text-green-700' :
                                field.confidence >= 0.6 ? 'bg-yellow-100 text-yellow-700' :
                                'bg-red-100 text-red-700'
                              }`}>
                                {Math.round(field.confidence * 100)}%
                              </span>
                            ) : (
                              <span className="text-gray-400">-</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          )}

          {/* Email Tab */}
          {activeTab === 'email' && (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-gray-900">Outreach Email Draft</h3>
                <button
                  onClick={generateEmail}
                  disabled={emailLoading}
                  className="flex items-center gap-2 px-3 py-1.5 text-sm bg-primary-100 text-primary-700 rounded-lg hover:bg-primary-200 transition-colors disabled:opacity-50"
                >
                  {emailLoading ? (
                    <div className="w-4 h-4 border-2 border-primary-700/30 border-t-primary-700 rounded-full animate-spin" />
                  ) : (
                    <RefreshCw className="w-4 h-4" />
                  )}
                  {emailLoading ? 'Generating...' : 'Regenerate'}
                </button>
              </div>
              
              {emailError && (
                <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {emailError}
                </div>
              )}
              {emailSendMessage && (
                <div className="mb-4 p-3 bg-blue-50 border border-blue-200 rounded-lg text-blue-800 text-sm">
                  {emailSendMessage}
                </div>
              )}
              
              {email ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <label className="text-sm font-medium text-gray-700 block mb-2">
                        To
                      </label>
                      <input
                        type="text"
                        value={emailTo}
                        onChange={e => setEmailTo(e.target.value)}
                        placeholder="client@example.com, rm@example.com"
                        className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                    <div className="p-4 bg-gray-50 rounded-lg">
                      <label className="text-sm font-medium text-gray-700 block mb-2">
                        Cc
                      </label>
                      <input
                        type="text"
                        value={emailCc}
                        onChange={e => setEmailCc(e.target.value)}
                        placeholder="optional1@example.com, optional2@example.com"
                        className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                      />
                    </div>
                  </div>

                  <div className="p-4 bg-gray-50 rounded-lg">
                    <label className="text-sm font-medium text-gray-700 block mb-2">
                      Subject
                    </label>
                    <input
                      type="text"
                      value={email.subject}
                      onChange={e => setEmail(prev => prev ? { ...prev, subject: e.target.value } : null)}
                      className="w-full p-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500"
                    />
                  </div>
                  
                  <div className="p-4 bg-gray-50 rounded-lg">
                    <label className="text-sm font-medium text-gray-700 block mb-2">
                      Body
                    </label>
                    <textarea
                      value={email.body}
                      onChange={e => setEmail(prev => prev ? { ...prev, body: e.target.value } : null)}
                      rows={12}
                      className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 font-mono text-sm"
                    />
                  </div>
                  
                  <div className="flex justify-end">
                    <button
                      onClick={handleSendEmail}
                      disabled={emailSending}
                      className="min-w-[140px] bg-primary-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-primary-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                      {emailSending ? 'Sending…' : 'Send Email'}
                    </button>
                  </div>
                </div>
              ) : (
                <div className="text-center p-8">
                  {emailLoading ? (
                    <>
                      <div className="w-12 h-12 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin mx-auto mb-4" />
                      <p className="text-gray-900 font-medium">Generating email...</p>
                      <p className="text-gray-500 text-sm mt-1">
                        Creating professional outreach based on identified gaps.
                      </p>
                    </>
                  ) : (
                    <>
                      <Mail className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-900 font-medium">No email generated yet</p>
                      <p className="text-gray-500 text-sm mt-1 mb-4">
                        Generate an outreach email based on the identified gaps.
                      </p>
                      <button
                        onClick={generateEmail}
                        className="inline-flex items-center gap-2 bg-primary-600 text-white py-2 px-4 rounded-lg font-medium hover:bg-primary-700 transition-colors"
                      >
                        <Mail className="w-4 h-4" />
                        Generate Email
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
