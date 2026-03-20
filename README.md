# AI KYC Onboarding POC

A production-ready proof-of-concept for AI-powered bank client onboarding and KYC document processing. Built for cross-border banking scenarios with support for multiple jurisdictions.

## What This POC Proves

1. **Document Extraction**: OCR + LLM pipeline extracts structured fields from PDFs, DOCX, and images
2. **Policy Compliance**: YAML-driven rules engine validates against country-specific requirements
3. **Gap Detection**: Identifies missing documents and fields with severity scoring
4. **Outreach Automation**: AI-generated emails explaining requirements and requesting missing items

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   React + Vite  │────▶│   FastAPI        │────▶│   SQLite        │
│   Frontend      │     │   Backend        │     │   (Transactional)
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   Extraction     │
                        │   • pdfplumber   │
                        │   • pytesseract  │
                        │   • python-docx  │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   LLM (optional) │
                        │   • OpenAI API   │
                        │   • Structured   │
                        │     JSON output  │
                        └──────────────────┘
                               │
                               ▼
                        ┌──────────────────┐
                        │   Rules Engine   │
                        │   • YAML packs   │
                        │   • IN/SG ready  │
                        └──────────────────┘
```

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── settings.py          # Configuration
│   │   ├── storage.py           # SQLite models (SQLModel)
│   │   ├── paths.py             # Path utilities
│   │   ├── utils.py             # Helper functions
│   │   ├── routers/
│   │   │   └── cases.py         # API endpoints
│   │   ├── workflows/
│   │   │   ├── process_case.py  # Main processing pipeline
│   │   │   ├── extract_and_map.py
│   │   │   └── outreach.py      # Email generation
│   │   ├── extraction/
│   │   │   └── pipeline.py      # PDF/DOCX/OCR extraction
│   │   ├── rules/
│   │   │   ├── schema.py        # Pydantic rule models
│   │   │   ├── loader.py        # YAML rule loading
│   │   │   └── engine.py        # Rule evaluation
│   │   └── llm/
│   │       ├── client.py        # OpenAI client wrapper
│   │       ├── prompts.py       # Production-ready prompts
│   │       ├── schemas.py       # LLM output schemas
│   │       └── extract.py       # Classification + extraction
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Main app with routing
│   │   ├── pages/
│   │   │   ├── CreateCase.tsx   # Case creation form
│   │   │   ├── UploadDocuments.tsx
│   │   │   └── CaseResults.tsx  # Results dashboard
│   │   ├── components/          # Reusable components
│   │   ├── hooks/
│   │   │   └── useApi.ts        # API integration
│   │   └── types/
│   │       └── index.ts         # TypeScript types
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── rules/
│   └── countries/
│       ├── IN/
│       │   └── rules.yml        # India requirements
│       └── SG/
│           └── rules.yml        # Singapore requirements
├── policy/
│   ├── IN/
│   │   └── kyc_requirements.md  # Policy snippets for RAG
│   └── SG/
│       └── kyc_requirements.md
├── synthetic_data/
│   └── generator.py             # Synthetic doc generator
└── data/                        # Created at runtime
    ├── app.db                  # SQLite database
    ├── uploads/                # Uploaded documents
    └── chroma/                 # ChromaDB vector store
```

## Prerequisites

### Python Backend
- Python 3.11+ (you have 3.14.3 ✓)
- Tesseract OCR (for image/PDF OCR)

### Node Frontend
- Node.js 18+ (not installed in current environment)

### Install Tesseract OCR (Windows)
```powershell
# Using chocolatey (run as Administrator)
choco install tesseract

# Or download from:
# https://github.com/UB-Mannheim/tesseract/wiki
```

## Setup Instructions

### 1. Python Virtual Environment

```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

### 2. Environment Configuration

```powershell
# Copy example environment file
copy .env.example .env

# Edit .env and add your OpenAI API key (optional but recommended)
# OPENAI_API_KEY=sk-...
```

### 3. Generate Synthetic Documents (Optional)

```powershell
# Generate test documents for India and Singapore
cd ..
python synthetic_data/generator.py --country both --sets 2 --output synthetic_data/out

# Or generate with intentional gaps for testing
python synthetic_data/generator.py --country IN --sets 1 --missing ubo_dob registered_address
```

Generated files will be in `synthetic_data/out/IN/` and `synthetic_data/out/SG/`.

### 4. Start Backend Server

```powershell
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

The API will be available at `http://127.0.0.1:8000`

- Interactive docs: http://127.0.0.1:8000/docs
- Health check: http://127.0.0.1:8000/healthz

### 5. Start Frontend (requires Node.js)

```powershell
# In a new terminal
cd frontend
npm install
npm run dev
```

The frontend will be available at `http://localhost:5173`

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/cases` | Create new case |
| GET | `/api/cases/{case_id}` | Get case details |
| POST | `/api/cases/{case_id}/documents` | Upload documents |
| POST | `/api/cases/{case_id}/process` | Start processing |
| GET | `/api/cases/{case_id}/checklist` | Get required docs checklist |
| GET | `/api/cases/{case_id}/gaps` | Get identified gaps |
| GET | `/api/cases/{case_id}/fields` | Get extracted fields |
| POST | `/api/cases/{case_id}/outreach-email` | Generate outreach email |
| GET | `/healthz` | Health check |

## Using the System

### Workflow

1. **Create Case**: Select jurisdiction (IN/SG), entity type, products, and risk tier
2. **Upload Documents**: Drag-and-drop or select PDFs, DOCX, images
3. **Process**: System extracts text, classifies documents, extracts fields
4. **Review Results**:
   - Checklist shows required vs. uploaded documents
   - Gaps tab lists missing docs and fields
   - Fields tab shows extracted data with confidence scores
   - Email tab generates AI outreach

### Document Types Supported

**India (IN):**
- Certificate of Incorporation
- UBO Declaration
- Proof of Address (Utility Bill)
- Directors List

**Singapore (SG):**
- Certificate of Incorporation (ACRA)
- UBO Declaration
- Proof of Address (Utility Bill)
- Board Resolution

## Production-Ready Prompts

The system uses structured prompts with strict JSON output schemas:

### Prompt A: Document Classification
```
System: You are a banking KYC document classifier. Return JSON only.
Output: { "doc_type": string, "confidence": number, "rationale": string }
```

### Prompt B: Field Extraction
```
System: Extract only fields in the schema. Use null for missing. 
Return JSON only.
Output: { "fields": { "<field>": { "value": string|null, 
  "evidence": string|null, "confidence": number|null } } }
```

### Prompt C: Gap Explanation
```
System: Explain missing requirements using policy_excerpts only.
Output: { "items": [{ "item": string, "why": string, 
  "citations": ["source_id"] }] }
```

### Prompt D: Outreach Email
```
System: Draft professional email. No invented facts. JSON only.
Output: { "subject": string, "body": string }
```

## LLM Configuration

The system works **without** an LLM (uses heuristics), but quality improves significantly with one:

```env
# .env file
OPENAI_API_KEY=sk-...                    # Required for LLM features
OPENAI_BASE_URL=https://api.openai.com/v1  # Optional: for proxies
OPENAI_MODEL=gpt-4o-mini                  # or gpt-5.2, gpt-4.1, etc.
```

### JSON Schema Enforcement

All LLM calls:
1. Use `temperature=0.1` for consistency
2. Request JSON-only output
3. Validate against Pydantic schemas
4. Retry up to 3 times on validation failures
5. Fall back to heuristic extraction on final failure

## Extending to New Countries

Adding a new country is data-only, no code changes:

1. **Create rule pack** `rules/countries/XX/rules.yml`:
```yaml
country: XX
version: "1"
doc_types:
  certificate_of_incorporation:
    title: Certificate of Incorporation
    fields:
      company_name: { required: true }
      registration_number: { required: true }
requirements:
  - entity_type: company
    products_any: ["payments", "trade"]
    risk_tiers_any: ["low", "medium", "high"]
    required_docs:
      - certificate_of_incorporation
```

2. **Add policy snippets** `policy/XX/kyc_requirements.md`:
```markdown
# XX KYC Requirements
## Certificate of Incorporation
Explanation of why this doc is required...
```

3. **Generate synthetic docs** (optional):
Extend `synthetic_data/generator.py` with company profile generator for XX.

## Key Features for Production Selection

1. **Deterministic Baseline**: Works without LLM (heuristic fallback)
2. **Structured Logging**: All actions audited in `audit_events` table
3. **Schema Validation**: All LLM outputs validated with retries
4. **Country Agnostic**: Add countries via YAML, no code changes
5. **Async Processing**: Background task model (easily migrates to Celery/RQ)
6. **File Safety**: Strict file type/size validation, safe filename handling

## Data Model

### Core Entities

**Case**: A client onboarding case with jurisdiction, entity type, products, risk tier

**Document**: Uploaded file with detected type, storage path, metadata

**ExtractionRun**: Processing job tracking with status

**ExtractedField**: Field-level extraction with provenance (evidence text)

**ChecklistItem**: Required document tracking with satisfaction status

**GapItem**: Missing docs/fields with severity (high/medium/low)

**AuditEvent**: Immutable audit trail of all actions

## Troubleshooting

### Tesseract not found
```powershell
# Add to PATH or set in .env
TESSDATA_PREFIX=C:\Program Files\Tesseract-OCR
```

### PDF extraction fails
- Ensure `pdfplumber` is installed
- For scanned PDFs, Tesseract OCR will be used automatically

### LLM responses not structured
- Check `OPENAI_API_KEY` is set
- The system falls back to heuristics if LLM is unavailable

### CORS errors in frontend
- Ensure backend is running on `127.0.0.1:8000`
- Frontend proxy is configured in `vite.config.ts`

## Next Steps for Production

1. **Authentication**: Add JWT/OAuth2 for user auth
2. **Cloud Storage**: Replace local uploads with S3/Azure Blob
3. **Database**: Migrate SQLite to PostgreSQL
4. **Queue**: Add Redis + Celery for background jobs
5. **Monitoring**: Add structured logging (JSON), metrics, alerts
6. **Security**: Add virus scanning, PII detection, encryption at rest
7. **Testing**: Add unit tests, integration tests, load tests

## License

MIT - For demonstration and educational purposes.

## Contact

This is a POC built for demonstration. For production deployment guidance, consult with your architecture and security teams.
