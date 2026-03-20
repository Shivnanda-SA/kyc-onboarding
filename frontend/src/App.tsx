import { Routes, Route, NavLink } from 'react-router-dom';
import { Building2, Plus, Home } from 'lucide-react';
import CreateCase from './pages/CreateCase';
import UploadDocuments from './pages/UploadDocuments';
import CaseResults from './pages/CaseResults';

function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary-600 rounded-lg">
                <Building2 className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-lg font-semibold text-gray-900">AI KYC Onboarding</h1>
              </div>
            </div>
            
            <nav className="flex items-center gap-4">
              <NavLink
                to="/"
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`
                }
              >
                <Home className="w-4 h-4" />
                Home
              </NavLink>
              <NavLink
                to="/cases/new"
                className={({ isActive }) =>
                  `flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:bg-gray-100'
                  }`
                }
              >
                <Plus className="w-4 h-4" />
                New Case
              </NavLink>
            </nav>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {children}
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-auto">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <p className="text-sm text-gray-500 text-center">
            AI KYC Onboarding POC • FastAPI + React + SQLite/Chroma
          </p>
        </div>
      </footer>
    </div>
  );
}

function HomePage() {
  return (
    <div className="text-center py-16">
      <div className="w-20 h-20 bg-primary-100 rounded-full flex items-center justify-center mx-auto mb-6">
        <Building2 className="w-10 h-10 text-primary-600" />
      </div>
      <h1 className="text-3xl font-bold text-gray-900 mb-4">
        AI KYC Onboarding System
      </h1>
      <p className="text-lg text-gray-600 mb-8 max-w-2xl mx-auto">
        Automate client onboarding with intelligent document processing, 
        policy compliance checking, and gap detection.
      </p>
      <div className="flex items-center justify-center gap-4">
        <a
          href="/cases/new"
          className="inline-flex items-center gap-2 bg-primary-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-primary-700 transition-colors"
        >
          <Plus className="w-5 h-5" />
          Create New Case
        </a>
      </div>
      
      <div className="mt-16 grid grid-cols-3 gap-6 max-w-4xl mx-auto">
        <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">📄</span>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Document Extraction</h3>
          <p className="text-sm text-gray-600">
            OCR + LLM-powered extraction from PDFs, images, and DOCX files
          </p>
        </div>
        <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">✓</span>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Policy Compliance</h3>
          <p className="text-sm text-gray-600">
            YAML-driven rules engine for country-specific KYC requirements
          </p>
        </div>
        <div className="p-6 bg-white rounded-xl shadow-sm border border-gray-200">
          <div className="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">✉️</span>
          </div>
          <h3 className="font-semibold text-gray-900 mb-2">Outreach Generation</h3>
          <p className="text-sm text-gray-600">
            AI-generated emails explaining missing requirements
          </p>
        </div>
      </div>
    </div>
  );
}

function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/cases/new" element={<CreateCase />} />
        <Route path="/cases/:caseId/upload" element={<UploadDocuments />} />
        <Route path="/cases/:caseId/results" element={<CaseResults />} />
      </Routes>
    </Layout>
  );
}

export default App;
