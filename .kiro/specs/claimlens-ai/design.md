# ClaimLens AI: Design Document (Hackathon MVP)

## Overview

### System Purpose

ClaimLens AI is an AI-powered medical insurance claim reasoning engine for the Indian healthcare ecosystem. This MVP demonstrates the core innovation: using RAG (Retrieval-Augmented Generation) and clause-aware LLM reasoning to automatically analyze medical claims against insurance policy documents, providing explainable approval predictions.

### MVP Scope

This hackathon MVP focuses on demonstrating:

1. **Document Upload**: Upload discharge summaries and policy documents
2. **RAG Pipeline**: Semantic policy retrieval using vector embeddings
3. **Clause-Aware Reasoning**: LLM-based claim analysis with policy citations
4. **Explainable Predictions**: Human-readable approval/denial reasoning with confidence scores
5. **Simple Web Interface**: Demo dashboard for uploading documents and viewing results

This MVP demonstrates the core clause-aware RAG reasoning engine that will power future capabilities including multi-lingual policy understanding, Ayushman Bharat PMJAY package validation, and large-scale TPA integrations in production deployments.

### What's NOT in MVP (Future Scope)

- Multi-region deployment and disaster recovery
- Full multi-tenant SaaS with organization isolation
- Production-grade authentication (Cognito, SSO)
- Real-time webhooks and TPA integrations
- Advanced fraud detection ML models
- Comprehensive audit logging and compliance automation
- Auto-scaling and load balancing
- Kubernetes/EKS orchestration

### Design Principles

1. **Semantic Understanding**: Use embeddings and LLM reasoning, not keyword matching
2. **Explainability First**: Every decision cites specific policy clauses
3. **Minimal Viable Architecture**: Prove the AI innovation with simplest infrastructure
4. **Demo-Ready**: Focus on working end-to-end flow for judges


## Architecture

### MVP System Architecture

Simplified architecture focusing on core RAG pipeline demonstration:

```
┌─────────────────────────────────────────────────────────┐
│                   Web Interface                          │
│            (Simple React/Streamlit UI)                   │
└────────────────────────┬────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────┐
│                FastAPI Backend                           │
│         (Single ECS container or local)                  │
└────────────────────────┬────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼──────┐  ┌──────▼──────┐  ┌─────▼──────┐
│  S3 Storage  │  │  OpenSearch │  │   Bedrock  │
│  (Documents) │  │  (Vectors)  │  │  (Claude)  │
└──────────────┘  └─────────────┘  └────────────┘
                         │
                  ┌──────▼──────┐
                  │  SageMaker  │
                  │ (Embeddings)│
                  └─────────────┘
                         │
                  ┌──────▼──────┐
                  │   SQLite    │
                  │ (Metadata)  │
                  └─────────────┘
```

### Core Data Flow

**1. Policy Upload Flow**:
```
User uploads policy PDF → S3 storage
→ Extract text (PyPDF2)
→ Chunk into semantic units (200-400 tokens)
→ Generate embeddings (SageMaker BGE-Large)
→ Index in OpenSearch k-NN
→ Store metadata in SQLite
```

**2. Claim Analysis Flow**:
```
User uploads discharge summary → Extract clinical data
→ Generate query embedding
→ OpenSearch retrieves top-K policy chunks
→ Construct prompt with retrieved context
→ Bedrock Claude generates reasoning
→ Parse response → Return approval prediction + citations
```

### AWS Services (Minimal Set)

| Service | Purpose | MVP Justification |
|---------|---------|-------------------|
| **S3** | Document storage | Simple, durable file storage |
| **SageMaker** | Embedding model hosting | BGE-Large for semantic search |
| **OpenSearch** | Vector database | k-NN search for RAG retrieval |
| **Bedrock** | LLM reasoning | Claude 3.5 Sonnet for analysis |
| **ECS/Fargate** | Backend hosting | Containerized FastAPI app |
| **SQLite** | Metadata storage | Lightweight, no RDS needed for MVP |

### Deployment Options

**Option 1: Fully AWS-Hosted** (Recommended for demo)
- ECS Fargate for FastAPI backend
- OpenSearch managed service
- SageMaker endpoint for embeddings
- S3 for document storage

**Option 2: Hybrid Local** (For development)
- Local FastAPI server
- Local OpenSearch (Docker)
- AWS Bedrock API calls
- AWS SageMaker endpoint
- Local SQLite database


## Components and Interfaces

### 1. Document Processing Module

**Responsibility**: Extract text from PDFs and prepare for analysis

**Components**:
- **PDF Text Extractor**: Uses PyPDF2 for digital PDFs
- **Policy Chunker**: Splits policy documents at clause boundaries
- **Clinical Data Parser**: Extracts diagnoses, procedures, dates from discharge summaries

**API**:

```python
# Upload Document
POST /api/documents/upload
Request:
{
  "document_type": "policy" | "discharge_summary",
  "file": <binary>
}
Response:
{
  "document_id": "doc_123",
  "status": "processing"
}

# Get Document Status
GET /api/documents/{document_id}
Response:
{
  "document_id": "doc_123",
  "status": "completed",
  "extracted_data": {
    "text": "...",
    "entities": {...}
  }
}
```

### 2. RAG Pipeline Module

**Responsibility**: Semantic retrieval and LLM reasoning

**Components**:
- **Embedding Generator**: Calls SageMaker endpoint for BGE-Large embeddings
- **Vector Search**: Queries OpenSearch k-NN index
- **Prompt Constructor**: Builds structured prompts with retrieved context
- **LLM Caller**: Invokes Bedrock Claude API
- **Response Parser**: Extracts approval prediction and clause citations

**API**:

```python
# Analyze Claim
POST /api/claims/analyze
Request:
{
  "discharge_summary_id": "doc_123",
  "policy_id": "pol_456",
  "clinical_data": {
    "diagnoses": ["K80.0 - Calculous cholecystitis"],
    "procedures": ["Laparoscopic cholecystectomy"],
    "admission_date": "2024-01-10",
    "discharge_date": "2024-01-13"
  }
}
Response:
{
  "claim_id": "claim_789",
  "approval_prediction": "likely_approved",
  "confidence": 0.88,
  "reasoning": "Laparoscopic cholecystectomy is covered under Section 7.2.1...",
  "supporting_clauses": [
    {
      "clause_id": "7.2.1",
      "text": "Laparoscopic procedures covered for acute conditions",
      "relevance_score": 0.94
    }
  ],
  "recommendations": [
    "Attach pre-operative ultrasound report",
    "Add secondary diagnosis code K80.12"
  ]
}
```

### 3. Policy Management Module

**Responsibility**: Index and version policy documents

**Components**:
- **Policy Uploader**: Stores PDFs in S3
- **Policy Indexer**: Chunks and embeds policy text
- **Version Tracker**: Maintains policy effective dates

**API**:

```python
# Upload Policy
POST /api/policies/upload
Request:
{
  "insurer": "Star Health",
  "policy_name": "Corporate Policy 2024",
  "effective_date": "2024-01-01",
  "file": <binary>
}
Response:
{
  "policy_id": "pol_456",
  "indexing_status": "in_progress"
}

# List Policies
GET /api/policies
Response:
{
  "policies": [
    {
      "policy_id": "pol_456",
      "insurer": "Star Health",
      "policy_name": "Corporate Policy 2024",
      "chunks_indexed": 342,
      "status": "active"
    }
  ]
}
```


## Data Models

### 1. Document Metadata (SQLite)

```sql
CREATE TABLE documents (
  document_id TEXT PRIMARY KEY,
  document_type TEXT NOT NULL, -- 'policy', 'discharge_summary'
  file_name TEXT NOT NULL,
  s3_key TEXT NOT NULL,
  upload_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
  processing_status TEXT, -- 'pending', 'processing', 'completed', 'failed'
  extracted_text TEXT,
  metadata JSON -- Flexible field for document-specific data
);
```

### 2. Policy Metadata (SQLite)

```sql
CREATE TABLE policies (
  policy_id TEXT PRIMARY KEY,
  insurer TEXT NOT NULL,
  policy_name TEXT NOT NULL,
  effective_date DATE NOT NULL,
  s3_key TEXT NOT NULL,
  total_chunks INTEGER,
  indexed_at DATETIME,
  status TEXT -- 'pending', 'indexing', 'active', 'failed'
);
```

### 3. Policy Chunks (OpenSearch)

```json
{
  "chunk_id": "pol_456_chunk_042",
  "policy_id": "pol_456",
  "clause_id": "7.2.1",
  "text": "Laparoscopic procedures are covered for acute conditions...",
  "embedding": [0.023, -0.145, ...],  // 768-dimensional vector
  "metadata": {
    "section": "Surgical Procedures",
    "page_number": 42
  }
}
```

**OpenSearch Index Configuration**:
```json
{
  "settings": {
    "index.knn": true
  },
  "mappings": {
    "properties": {
      "chunk_id": {"type": "keyword"},
      "policy_id": {"type": "keyword"},
      "text": {"type": "text"},
      "embedding": {
        "type": "knn_vector",
        "dimension": 768,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimilarity"
        }
      }
    }
  }
}
```

### 4. Claim Analysis Results (SQLite)

```sql
CREATE TABLE claims (
  claim_id TEXT PRIMARY KEY,
  discharge_summary_id TEXT,
  policy_id TEXT,
  clinical_data JSON,
  approval_prediction TEXT, -- 'likely_approved', 'likely_denied', 'uncertain'
  confidence REAL,
  reasoning TEXT,
  supporting_clauses JSON,
  recommendations JSON,
  analyzed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```


## Correctness Properties

### What are Correctness Properties?

A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.

### Core MVP Properties

**Property 1: RAG Round-Trip Consistency**

*For any* policy chunk text, if we:
1. Generate an embedding for the text
2. Index it in OpenSearch
3. Query with the same text
4. Retrieve top-K results

Then the original chunk should appear in the top-K results with similarity score > 0.95.

**Rationale**: Validates that embeddings preserve semantic meaning and vector search works correctly.

---

**Property 2: Embedding Dimensionality Consistency**

*For any* text input to the embedding model, the output vector should always have exactly 768 dimensions (for BGE-Large model).

**Rationale**: Ensures embedding model deployment is correct and compatible with OpenSearch configuration.

---

**Property 3: Claim Analysis Includes Citations**

*For any* claim analysis that returns "likely_approved" or "likely_denied", the response must contain at least one policy clause citation with clause_id and relevance_score.

**Rationale**: Core explainability requirement - every decision must reference specific policy sections.

---

**Property 4: Policy Chunk Retrieval Relevance**

*For any* claim query, all retrieved policy chunks should have cosine similarity > 0.6 to the query embedding.

**Rationale**: Ensures RAG retrieval returns semantically relevant policy sections, not random chunks.

---

**Property 5: Document Upload Idempotency**

*For any* document with the same content hash, uploading multiple times should return the same document_id and store only one copy in S3.

**Rationale**: Prevents duplicate storage and ensures consistent references.

---

**Property 6: ICD-10 Code Format Validation**

*For any* diagnosis code in clinical data, it should match ICD-10 format: letter + 2-3 digits + optional decimal + 1-2 digits (e.g., "K80.0", "E11.9").

**Rationale**: Basic data validation to prevent malformed medical codes.

---

**Property 7: Confidence Score Range**

*For any* claim analysis, the confidence score should be in the range [0.0, 1.0].

**Rationale**: Validates output parsing and ensures UI can display confidence as percentage.

---

**Property 8: S3 Document Retrieval**

*For any* document_id stored in the database, the corresponding S3 object should exist and be retrievable.

**Rationale**: Ensures data consistency between metadata database and object storage.


## Error Handling

### Error Response Format

All API errors return consistent JSON structure:

```json
{
  "error": {
    "code": "INVALID_FILE_FORMAT",
    "message": "Only PDF files are supported",
    "details": {
      "received_format": "image/jpeg",
      "supported_formats": ["application/pdf"]
    }
  }
}
```

### Common Error Scenarios

| Error | HTTP Code | Handling |
|-------|-----------|----------|
| Invalid file format | 400 | Validate MIME type before upload |
| File too large (>50MB) | 413 | Check file size client-side |
| Document not found | 404 | Return clear error message |
| OpenSearch unavailable | 503 | Retry with exponential backoff (3 attempts) |
| Bedrock rate limit | 429 | Wait and retry after 60 seconds |
| SageMaker timeout | 504 | Increase timeout to 60s, retry once |
| Invalid ICD-10 code | 422 | Validate format with regex |

### Retry Strategy

**Exponential Backoff** for transient errors:
```
Retry 1: Wait 1 second
Retry 2: Wait 2 seconds
Retry 3: Wait 4 seconds
Max retries: 3
```

**Services with Retry**:
- OpenSearch queries
- Bedrock API calls
- SageMaker endpoint calls
- S3 uploads

**No Retry** for:
- Validation errors (400, 422)
- Not found errors (404)
- File format errors (415)

### Graceful Degradation

If OpenSearch is unavailable:
- Return error message asking user to try again
- Log error for debugging

If Bedrock is unavailable:
- Return "Service temporarily unavailable" message
- Suggest retry after 1 minute


## Testing Strategy

### Testing Approach

**Unit Tests** (50%): Validate specific functions and edge cases
**Property Tests** (30%): Verify universal properties with randomized inputs
**Integration Tests** (15%): Test component interactions
**Manual Testing** (5%): End-to-end demo flow

### Property-Based Testing

**Framework**: Hypothesis (Python)

**Configuration**:
- Minimum 100 iterations per property test
- Each test references design document property
- Tag format: `# Feature: claimlens-ai, Property {number}`

**Example Property Tests**:

```python
from hypothesis import given, strategies as st

# Property 1: RAG Round-Trip Consistency
@given(policy_text=st.text(min_size=100, max_size=500))
def test_rag_round_trip(policy_text):
    """
    Feature: claimlens-ai, Property 1: RAG Round-Trip Consistency
    """
    # Index the chunk
    chunk_id = index_policy_chunk(policy_text)
    
    # Search with same text
    results = vector_search(policy_text, top_k=5)
    
    # Original chunk should be in results
    assert any(r.chunk_id == chunk_id for r in results)
    
    # With high similarity
    original = next(r for r in results if r.chunk_id == chunk_id)
    assert original.similarity > 0.95


# Property 2: Embedding Dimensionality
@given(text=st.text(min_size=10, max_size=1000))
def test_embedding_dimensionality(text):
    """
    Feature: claimlens-ai, Property 2: Embedding Dimensionality Consistency
    """
    embedding = generate_embedding(text)
    assert len(embedding) == 768


# Property 3: Claim Analysis Citations
@given(
    diagnoses=st.lists(st.sampled_from(['K80.0', 'E11.9']), min_size=1),
    procedures=st.lists(st.sampled_from(['47562', '99213']), min_size=1)
)
def test_claim_analysis_citations(diagnoses, procedures):
    """
    Feature: claimlens-ai, Property 3: Claim Analysis Includes Citations
    """
    result = analyze_claim({
        'diagnoses': diagnoses,
        'procedures': procedures,
        'policy_id': 'test_policy'
    })
    
    if result.approval_prediction in ['likely_approved', 'likely_denied']:
        assert len(result.supporting_clauses) > 0
        assert all(hasattr(c, 'clause_id') for c in result.supporting_clauses)
```

### Unit Testing

**Coverage Target**: 80%+ for core modules

**Key Test Areas**:
- PDF text extraction
- Policy chunking logic
- ICD-10 code validation
- Embedding generation
- Prompt construction
- Response parsing

**Example Unit Tests**:

```python
def test_icd10_validation():
    """Validate ICD-10 code format"""
    assert validate_icd10('K80.0') == True
    assert validate_icd10('E11.9') == True
    assert validate_icd10('XYZ') == False
    assert validate_icd10('123') == False

def test_policy_chunking():
    """Validate policy chunking preserves clause boundaries"""
    policy_text = "Section 7.2.1: Coverage... Section 7.2.2: Exclusions..."
    chunks = chunk_policy(policy_text)
    
    assert len(chunks) == 2
    assert 'Section 7.2.1' in chunks[0]
    assert 'Section 7.2.2' in chunks[1]

def test_confidence_score_range():
    """Confidence scores should be between 0 and 1"""
    result = analyze_claim(sample_claim_data)
    assert 0.0 <= result.confidence <= 1.0
```

### Integration Testing

**Test Scenarios**:

1. **End-to-End Policy Indexing**:
   - Upload PDF → Extract text → Chunk → Embed → Index in OpenSearch
   - Verify chunks are searchable

2. **End-to-End Claim Analysis**:
   - Upload discharge summary → Extract clinical data
   - Query policy → Retrieve chunks → LLM reasoning
   - Verify response format

3. **S3 Integration**:
   - Upload document → Verify S3 object exists
   - Retrieve document → Verify content matches

**Test Environment**:
- LocalStack for S3 mocking
- Docker OpenSearch for vector search
- Mocked Bedrock responses for deterministic testing

### Manual Testing Checklist

For demo preparation:

- [ ] Upload sample policy PDF (Star Health corporate policy)
- [ ] Verify policy indexing completes successfully
- [ ] Upload sample discharge summary
- [ ] Run claim analysis
- [ ] Verify approval prediction displays correctly
- [ ] Verify clause citations are shown
- [ ] Verify recommendations are actionable
- [ ] Test with different claim scenarios (approved, denied, uncertain)
- [ ] Verify error handling (invalid file format, missing policy)


## Future Scope

### Production Features (Post-Hackathon)

**1. Multi-Tenant SaaS Architecture**
- Organization-based data isolation
- Row-level security in database
- Cognito user pools per organization
- API key management

**2. Advanced Authentication & Authorization**
- SSO integration (SAML, OAuth)
- Role-based access control (RBAC)
- Fine-grained permissions
- API rate limiting per organization

**3. Enhanced Document Processing**
- OCR for scanned documents (Textract)
- Medical entity recognition (Comprehend Medical)
- Multi-language support (Hindi, Tamil, Telugu)
- Automated ICD-10 code extraction

**4. Production Infrastructure**
- Multi-region deployment (Mumbai, Hyderabad)
- Auto-scaling ECS clusters
- RDS PostgreSQL with Multi-AZ
- ElastiCache Redis for caching
- CloudFront CDN
- VPC network isolation

**5. Compliance & Audit**
- Comprehensive audit logging (CloudTrail)
- Immutable audit trail in RDS
- HIPAA/DISHA compliance automation
- Data retention policies (7 years)
- Encryption key rotation (KMS)

**6. Advanced AI Features**
- Reranking models for better retrieval
- Fine-tuned embedding models for medical domain
- Fraud detection ML models
- Cashless pre-authorization prediction
- Medical coding assistant

**7. Integration Ecosystem**
- Hospital EMR integrations (e-Sushrut, Practo Ray)
- TPA portal integrations (Medi Assist, Vidal Health)
- Real-time webhooks for claim status updates
- Batch processing APIs for high volume

**8. Analytics & Reporting**
- Denial rate analytics by hospital/insurer
- Revenue leakage reports
- Claim approval trends
- Policy coverage gap analysis
- QuickSight dashboards

**9. Monitoring & Observability**
- CloudWatch dashboards
- X-Ray distributed tracing
- PagerDuty alerting
- Error rate monitoring
- Performance metrics (P50, P95, P99 latency)

**10. DevOps & CI/CD**
- Automated testing pipeline
- Blue-green deployments
- Canary releases
- Infrastructure as Code (Terraform/CDK)
- Automated rollback on errors

### Scalability Roadmap

**Phase 1 (MVP)**: 1,000-5,000 claims/month
- Single ECS task
- Small OpenSearch cluster (1 node)
- SQLite database

**Phase 2 (Beta)**: 50,000-100,000 claims/month
- Auto-scaling ECS (2-5 tasks)
- OpenSearch cluster (3 nodes)
- RDS PostgreSQL
- ElastiCache Redis

**Phase 3 (Production)**: 1M+ claims/month
- Multi-region deployment
- ECS cluster with 10-50 tasks
- OpenSearch with dedicated master nodes
- Aurora PostgreSQL Global Database
- Advanced caching strategies

### Cost Optimization Strategies

**MVP Cost Estimate**: ₹50,000-₹80,000/month (~$600-$1,000)

**Production Optimizations**:
- Spot instances for batch processing (70% savings)
- S3 Intelligent-Tiering for document archival
- Reserved instances for baseline capacity
- Lambda for event-driven processing
- Caching frequently accessed policy chunks
- Batch embedding generation

### Technical Debt to Address

**MVP Shortcuts**:
- SQLite instead of RDS (not suitable for production)
- No authentication/authorization
- No rate limiting
- No comprehensive error logging
- No monitoring/alerting
- Hardcoded configuration values
- No automated testing in CI/CD

**Post-Hackathon Priorities**:
1. Migrate to RDS PostgreSQL
2. Implement authentication (Cognito)
3. Add comprehensive logging
4. Set up CloudWatch monitoring
5. Implement automated testing
6. Add API rate limiting
7. Externalize configuration