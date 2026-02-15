# ClaimLens AI - Design Document

## 1. Architecture Overview

ClaimLens AI is built entirely on AWS-native services, leveraging managed infrastructure to eliminate operational overhead while ensuring HIPAA compliance, scalability, and cost efficiency.

### Design Principles

1. **AWS-Only Architecture**: All components use AWS-managed services—no third-party SaaS or self-hosted infrastructure
2. **Serverless-First**: Prefer Lambda, API Gateway, and managed services over EC2/containers where possible
3. **Security by Default**: VPC isolation, encryption at rest/transit, IAM least privilege, CloudTrail audit logging
4. **Event-Driven**: Asynchronous processing using EventBridge, SQS, and Step Functions
5. **Multi-Tenant Isolation**: Logical data separation using DynamoDB partition keys and S3 prefixes
6. **Observability**: CloudWatch metrics, logs, and X-Ray tracing for all components

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        Client Layer                              │
│  (Hospitals, Insurers, TPAs via Web Dashboard or API)           │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   API Gateway + CloudFront                       │
│              (Authentication via Cognito)                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ▼               ▼               ▼
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  Document   │  │   Claim     │  │  Analytics  │
│  Processing │  │  Reasoning  │  │  & Reporting│
│   Pipeline  │  │   Engine    │  │   Service   │
└─────────────┘  └─────────────┘  └─────────────┘
         │               │               │
         ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│  S3 | DynamoDB | RDS PostgreSQL | OpenSearch | ElastiCache     │
└─────────────────────────────────────────────────────────────────┘
         │               │               │
         ▼               ▼               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   AI/ML Layer                                    │
│  SageMaker Endpoints | Bedrock | Textract | Comprehend Medical │
└─────────────────────────────────────────────────────────────────┘
```

## 2. AWS Service Architecture Map

### 2.1 API & Application Layer

**Amazon API Gateway**
- RESTful API endpoints for claim submission, status queries, policy management
- Request throttling: 1,000 requests/second per client
- API key management for third-party integrations
- Request/response validation using JSON schemas
- CORS configuration for web dashboard

**AWS Lambda**
- API handlers for business logic (Node.js 20.x runtime)
- Timeout: 30 seconds for API calls, 15 minutes for async processing
- Memory: 512MB-3GB based on function complexity
- Provisioned concurrency for latency-sensitive endpoints

**Amazon Cognito**
- User pools for hospital/insurer user authentication
- Identity pools for temporary AWS credentials
- SAML 2.0 federation for enterprise SSO
- MFA enforcement for administrative users
- Custom attributes for tenant_id and role-based access

**Amazon CloudFront**
- CDN for React-based dashboard (S3 origin)
- Edge caching with 24-hour TTL for static assets
- Origin Access Identity for secure S3 access
- Custom domain with ACM SSL certificates

### 2.2 Document Processing Pipeline

**Amazon S3**
- Bucket structure: `claimlens-documents-{env}/{tenant_id}/{claim_id}/`
- Versioning enabled for audit trail
- Lifecycle policies: Transition to S3 Glacier after 90 days
- Event notifications trigger Lambda on document upload
- Server-side encryption with KMS customer-managed keys

**Amazon Textract**
- Asynchronous document analysis API for OCR
- Extracts text, tables, and forms from PDFs
- Confidence scores for extracted data validation
- Supports multi-page documents up to 3,000 pages

**AWS Step Functions**
- Orchestrates document processing workflow:
  1. Document upload → S3
  2. Textract OCR → Extract text
  3. Comprehend Medical → Entity extraction
  4. Lambda → Structure data
  5. DynamoDB → Store metadata
- Error handling with exponential backoff retry
- Execution history retained for 90 days

**Amazon EventBridge**
- Event bus for document lifecycle events
- Rules trigger downstream processing (e.g., "document.uploaded" → Step Functions)
- Cross-account event routing for multi-region deployments


### 2.3 AI/ML Intelligence Layer

**Amazon SageMaker**
- **Medical Entity Recognition Model**: Custom NER model hosted on ml.g4dn.xlarge instances
  - Auto-scaling: 1-10 instances based on InvocationsPerInstance metric
  - Model artifacts stored in S3 with versioning
  - A/B testing using production variants (90/10 traffic split)
  
- **Approval Prediction Model**: XGBoost classifier on ml.m5.large instances
  - Features: Entity counts, policy match scores, historical rejection patterns
  - Real-time inference with <200ms latency
  - Model retraining pipeline using SageMaker Pipelines (weekly schedule)

- **SageMaker Endpoints**: 
  - Data capture enabled for model monitoring
  - CloudWatch alarms on ModelLatency and Invocation4XXErrors
  - VPC deployment in private subnets

**Amazon Bedrock**
- **Foundation Model**: Anthropic Claude 3 Sonnet for claim reasoning
- **Use Cases**:
  - Generate natural language explanations for approval/rejection predictions
  - Summarize policy clauses relevant to claim
  - Suggest document corrections for rejected claims
- **Guardrails**: Content filtering to prevent PHI leakage in responses
- **Invocation logging**: All prompts and responses logged to S3 for audit

**Amazon Comprehend Medical**
- Detect medical entities: Medications, Procedures, Diagnoses, Anatomy
- Extract ICD-10 and CPT codes from discharge summaries
- PHI detection for redaction in non-production environments
- Batch processing for historical claim analysis

**Amazon OpenSearch Service**
- **Vector Search**: k-NN plugin for semantic policy clause retrieval
- **Index Structure**:
  - `policy-clauses`: 768-dimensional embeddings (from Bedrock Titan Embeddings)
  - `claims-metadata`: Structured claim data for analytics queries
- **Cluster Configuration**: 3 data nodes (r6g.large.search) across 3 AZs
- **Security**: Fine-grained access control, encryption at rest, VPC deployment

### 2.4 Data Storage Layer

**Amazon DynamoDB**
- **Tables**:
  - `Claims`: Partition key: `tenant_id`, Sort key: `claim_id`
  - `PolicyClauses`: Partition key: `policy_id`, Sort key: `clause_id`
  - `ReasoningTraces`: Partition key: `claim_id`, Sort key: `timestamp`
  - `Users`: Partition key: `tenant_id`, Sort key: `user_id`
- **Capacity**: On-demand billing mode for unpredictable workloads
- **Global Secondary Indexes**: 
  - `ClaimsByStatus`: Query claims by processing status
  - `ClaimsBySubmissionDate`: Time-range queries for analytics
- **Point-in-time recovery**: Enabled for disaster recovery
- **DynamoDB Streams**: Trigger Lambda for real-time notifications

**Amazon RDS PostgreSQL**
- **Use Case**: Relational data requiring complex joins (audit logs, reporting)
- **Instance**: db.r6g.xlarge (4 vCPU, 32GB RAM) Multi-AZ deployment
- **Read Replicas**: 2 replicas for analytics queries (Athena federation)
- **Backup**: Automated daily snapshots, 30-day retention
- **Encryption**: Transparent Data Encryption (TDE) with KMS
- **Schema**:
  - `audit_logs`: User actions, API calls, data access events
  - `claim_history`: Immutable record of claim state changes
  - `policy_versions`: Track policy document updates over time

**Amazon ElastiCache (Redis)**
- **Use Case**: Session management, API response caching, rate limiting
- **Cluster**: 3-node cluster (cache.r6g.large) with automatic failover
- **TTL Strategy**:
  - User sessions: 24 hours
  - Policy clause cache: 1 hour
  - API responses: 5 minutes
- **Encryption**: In-transit and at-rest encryption enabled

### 2.5 Security & Governance Layer

**AWS IAM**
- **Service Roles**: Lambda execution roles with least privilege policies
- **User Roles**: Hospital admin, billing manager, claim reviewer, auditor
- **Cross-Account Access**: Assume role for multi-account deployments
- **Permission Boundaries**: Prevent privilege escalation

**AWS KMS**
- **Customer-Managed Keys**: Separate keys for S3, RDS, DynamoDB, SageMaker
- **Key Rotation**: Automatic annual rotation enabled
- **Key Policies**: Restrict key usage to specific services and roles
- **CloudTrail Integration**: Log all key usage for audit

**AWS Secrets Manager**
- **Stored Secrets**: Database credentials, API keys, third-party service tokens
- **Rotation**: Automatic rotation for RDS credentials (30-day cycle)
- **VPC Endpoints**: Private access from Lambda without internet gateway

**Amazon VPC**
- **CIDR**: 10.0.0.0/16
- **Subnets**:
  - Public: 10.0.1.0/24, 10.0.2.0/24 (NAT Gateway, ALB)
  - Private: 10.0.10.0/24, 10.0.11.0/24 (Lambda, SageMaker, RDS)
  - Isolated: 10.0.20.0/24, 10.0.21.0/24 (Database tier)
- **Security Groups**: Least privilege ingress/egress rules
- **VPC Endpoints**: S3, DynamoDB, SageMaker, Secrets Manager (no internet routing)

**AWS CloudTrail**
- **Management Events**: All API calls logged to S3
- **Data Events**: S3 object-level logging for PHI access tracking
- **Log Integrity**: Log file validation enabled
- **Retention**: 7 years in S3 Glacier Deep Archive

**AWS Config**
- **Rules**: Enforce encryption, MFA, public access blocks, approved AMIs
- **Compliance Dashboard**: Real-time view of non-compliant resources
- **Remediation**: Automatic SSM automation for common violations

**Amazon GuardDuty**
- **Threat Detection**: Analyze VPC flow logs, CloudTrail, DNS logs
- **Findings**: Automated SNS notifications for high-severity threats
- **Integration**: EventBridge rules trigger Lambda for incident response

### 2.6 Monitoring & Observability Layer

**Amazon CloudWatch**
- **Metrics**: Custom metrics for claim processing latency, model accuracy, API errors
- **Dashboards**: Real-time operational dashboards for SRE team
- **Alarms**: 
  - SageMaker endpoint latency >500ms
  - Lambda error rate >1%
  - DynamoDB throttling events
  - RDS CPU >80%
- **Logs**: Centralized log aggregation from Lambda, API Gateway, Step Functions
- **Log Insights**: Query logs for error pattern analysis

**AWS X-Ray**
- **Distributed Tracing**: End-to-end request tracing across Lambda, API Gateway, DynamoDB
- **Service Map**: Visualize dependencies and latency bottlenecks
- **Annotations**: Tag traces with tenant_id, claim_id for filtering

**Amazon SNS**
- **Alerting**: CloudWatch alarms publish to SNS topics
- **Subscriptions**: Email, SMS, Lambda for on-call notifications
- **Topics**: `critical-alerts`, `operational-warnings`, `security-events`

**AWS Systems Manager (SSM)**
- **Parameter Store**: Application configuration (feature flags, model endpoints)
- **Session Manager**: Secure shell access to EC2 (if needed for debugging)
- **Patch Manager**: Automated OS patching for any EC2 instances

## 3. Detailed Design Flows

### 3.1 Claim Submission Flow

**Actors**: Hospital billing manager, ClaimLens API

**Preconditions**: User authenticated via Cognito, claim documents prepared

**Flow**:

1. **User uploads claim documents** (discharge summary, billing codes, patient info)
   - Frontend: React app hosted on S3, served via CloudFront
   - Action: POST /api/claims with multipart/form-data
   
2. **API Gateway receives request**
   - Validates JWT token from Cognito
   - Checks rate limit (100 requests/minute per user) using Lambda authorizer + ElastiCache
   - Routes to Lambda function: `SubmitClaimHandler`

3. **Lambda: SubmitClaimHandler**
   - Generates unique `claim_id` (UUID)
   - Uploads documents to S3: `s3://claimlens-docs/{tenant_id}/{claim_id}/`
   - Writes claim metadata to DynamoDB `Claims` table (status: "UPLOADED")
   - Publishes event to EventBridge: `claim.submitted`
   - Returns claim_id to user (HTTP 202 Accepted)

4. **EventBridge triggers Step Functions workflow**: `ProcessClaimWorkflow`

5. **Step Functions: ProcessClaimWorkflow**
   
   **Step 1: OCR Processing**
   - Lambda: `InvokeTextractAsync`
   - Calls Textract StartDocumentAnalysis API
   - Stores job_id in DynamoDB
   - Wait for Textract completion (SNS callback)
   
   **Step 2: Text Extraction**
   - Lambda: `ExtractTextFromTextract`
   - Calls Textract GetDocumentAnalysis API
   - Extracts text blocks, tables, key-value pairs
   - Stores raw text in S3: `{claim_id}/extracted_text.json`
   
   **Step 3: Medical Entity Recognition**
   - Lambda: `ExtractMedicalEntities`
   - Calls Comprehend Medical DetectEntitiesV2 API
   - Extracts: Medications, Procedures, Diagnoses, Anatomy
   - Stores entities in DynamoDB: `Claims` table (entities field)
   
   **Step 4: Policy Clause Retrieval**
   - Lambda: `RetrievePolicyClauses`
   - Generates embedding for claim text using Bedrock Titan Embeddings
   - Queries OpenSearch k-NN index for top-10 similar policy clauses
   - Stores matched clauses in DynamoDB: `ReasoningTraces` table
   
   **Step 5: Approval Prediction**
   - Lambda: `PredictApproval`
   - Invokes SageMaker Endpoint: `approval-prediction-model`
   - Input features: Entity counts, policy match scores, claim amount
   - Returns approval probability (0.0-1.0)
   - Stores prediction in DynamoDB: `Claims` table (approval_score field)
   
   **Step 6: Reasoning Generation**
   - Lambda: `GenerateReasoning`
   - Calls Bedrock Claude 3 Sonnet with prompt:
     ```
     Claim: {extracted_text}
     Matched Policy Clauses: {top_clauses}
     Approval Score: {score}
     
     Explain why this claim would be approved/rejected. Reference specific policy clauses.
     ```
   - Stores reasoning in DynamoDB: `ReasoningTraces` table
   - Updates claim status to "PROCESSED"
   
   **Step 7: Notification**
   - Lambda: `NotifyUser`
   - Publishes SNS message to user's notification topic
   - Sends email via SES with claim result summary

6. **User queries claim status**
   - GET /api/claims/{claim_id}
   - Lambda: `GetClaimHandler`
   - Queries DynamoDB `Claims` table
   - Returns claim metadata, approval score, reasoning

**Postconditions**: Claim processed, user notified, audit trail in CloudTrail

**Error Handling**:
- Textract failure: Retry 3 times with exponential backoff, then mark claim as "OCR_FAILED"
- SageMaker timeout: Fall back to rule-based prediction, flag for manual review
- Bedrock rate limit: Queue request in SQS, process with delay


### 3.2 Policy Document Ingestion Flow

**Actors**: Insurance admin, ClaimLens admin API

**Preconditions**: Insurance policy document (PDF) available

**Flow**:

1. **Admin uploads policy document**
   - POST /api/admin/policies with PDF file
   - API Gateway → Lambda: `IngestPolicyHandler`

2. **Lambda: IngestPolicyHandler**
   - Generates `policy_id` (UUID)
   - Uploads PDF to S3: `s3://claimlens-policies/{tenant_id}/{policy_id}.pdf`
   - Writes policy metadata to DynamoDB `Policies` table
   - Triggers Step Functions: `PolicyIngestionWorkflow`

3. **Step Functions: PolicyIngestionWorkflow**
   
   **Step 1: OCR Policy Document**
   - Lambda: `ExtractPolicyText`
   - Calls Textract for text extraction
   - Stores extracted text in S3
   
   **Step 2: Clause Segmentation**
   - Lambda: `SegmentPolicyClauses`
   - Uses Bedrock Claude to identify clause boundaries:
     ```
     Extract individual policy clauses from this document.
     Each clause should be a self-contained rule or condition.
     Return as JSON array: [{clause_id, text, category}]
     ```
   - Stores clauses in DynamoDB `PolicyClauses` table
   
   **Step 3: Generate Embeddings**
   - Lambda: `GenerateClauseEmbeddings`
   - For each clause, call Bedrock Titan Embeddings
   - Generates 768-dimensional vector
   - Indexes in OpenSearch with k-NN configuration
   
   **Step 4: Validate Policy**
   - Lambda: `ValidatePolicy`
   - Checks for required sections (coverage limits, exclusions, etc.)
   - Marks policy as "ACTIVE" or "INCOMPLETE"

4. **Admin reviews policy clauses**
   - GET /api/admin/policies/{policy_id}/clauses
   - Lambda queries DynamoDB and returns clause list
   - Admin can edit/approve clauses via PUT endpoint

**Postconditions**: Policy indexed, searchable via semantic retrieval

### 3.3 Real-Time Claim Status Query Flow

**Actors**: Hospital user, ClaimLens dashboard

**Preconditions**: User authenticated, claim_id known

**Flow**:

1. **User requests claim status**
   - Frontend: React app calls GET /api/claims/{claim_id}
   - CloudFront serves cached response if available (5-minute TTL)
   - If cache miss, routes to API Gateway

2. **API Gateway**
   - Validates Cognito JWT token
   - Extracts tenant_id from token claims
   - Routes to Lambda: `GetClaimHandler`

3. **Lambda: GetClaimHandler**
   - Checks ElastiCache for cached claim data (key: `claim:{claim_id}`)
   - If cache hit, return immediately
   - If cache miss:
     - Query DynamoDB `Claims` table (partition key: tenant_id, sort key: claim_id)
     - Query DynamoDB `ReasoningTraces` table for latest reasoning
     - Combine data and cache in ElastiCache (TTL: 5 minutes)
   - Return JSON response with claim details

4. **Frontend renders claim dashboard**
   - Displays approval score with confidence interval
   - Shows matched policy clauses with highlighting
   - Renders reasoning explanation from Bedrock
   - Provides download link for original documents (S3 presigned URL)

**Performance Optimization**:
- ElastiCache hit rate target: >80%
- DynamoDB read capacity: On-demand (auto-scales)
- API Gateway response time: <100ms (p95)

### 3.4 Batch Claim Processing Flow

**Actors**: TPA admin, ClaimLens batch API

**Preconditions**: CSV file with 1,000+ claims

**Flow**:

1. **Admin uploads batch file**
   - POST /api/batch/claims with CSV file
   - API Gateway → Lambda: `InitiateBatchProcessing`

2. **Lambda: InitiateBatchProcessing**
   - Uploads CSV to S3: `s3://claimlens-batch/{batch_id}/input.csv`
   - Writes batch metadata to DynamoDB `Batches` table
   - Publishes message to SQS queue: `ClaimProcessingQueue`
   - Returns batch_id to user

3. **SQS Queue: ClaimProcessingQueue**
   - FIFO queue for ordered processing
   - Message retention: 14 days
   - Dead-letter queue for failed messages

4. **Lambda: BatchClaimProcessor** (triggered by SQS)
   - Batch size: 10 messages per invocation
   - Concurrency: 100 (processes 1,000 claims in parallel)
   - For each claim:
     - Invoke Step Functions: `ProcessClaimWorkflow` (same as 3.1)
     - Update batch progress in DynamoDB
   - If processing fails, message returns to queue (max 3 retries)

5. **Lambda: BatchCompletionHandler** (triggered by DynamoDB Stream)
   - Monitors `Batches` table for completion
   - When all claims processed:
     - Generates summary report (approval rate, common rejection reasons)
     - Stores report in S3: `{batch_id}/report.json`
     - Sends SNS notification to admin
     - Publishes EventBridge event: `batch.completed`

6. **Admin downloads batch results**
   - GET /api/batch/{batch_id}/results
   - Lambda generates S3 presigned URL for report download
   - Report includes: claim_id, approval_score, reasoning, status

**Scalability**:
- SQS supports unlimited throughput
- Lambda concurrency: 1,000 (can process 10,000 claims/minute)
- SageMaker auto-scales to 50 instances under load

### 3.5 Analytics & Reporting Flow

**Actors**: Insurance analyst, ClaimLens analytics dashboard

**Preconditions**: Historical claim data in DynamoDB and RDS

**Flow**:

1. **Analyst requests trend report**
   - Frontend: GET /api/analytics/trends?start_date=2026-01-01&end_date=2026-02-15
   - API Gateway → Lambda: `GenerateTrendsReport`

2. **Lambda: GenerateTrendsReport**
   - Queries RDS PostgreSQL using read replica:
     ```sql
     SELECT 
       DATE_TRUNC('day', submission_date) as date,
       AVG(approval_score) as avg_score,
       COUNT(*) as total_claims,
       SUM(CASE WHEN approval_score > 0.8 THEN 1 ELSE 0 END) as approved_count
     FROM claim_history
     WHERE tenant_id = ? AND submission_date BETWEEN ? AND ?
     GROUP BY DATE_TRUNC('day', submission_date)
     ORDER BY date;
     ```
   - Caches result in ElastiCache (TTL: 1 hour)
   - Returns JSON with time-series data

3. **Frontend renders charts**
   - Uses Chart.js to visualize approval trends
   - Shows rejection reason breakdown (from DynamoDB aggregation)
   - Displays policy clause hit frequency (from OpenSearch aggregation)

4. **Analyst exports data for deeper analysis**
   - GET /api/analytics/export?format=csv
   - Lambda: `ExportAnalyticsData`
   - Queries Athena for large-scale data export:
     ```sql
     SELECT * FROM claimlens_data_lake.claims
     WHERE year = 2026 AND month = 2
     ```
   - Athena queries S3 data lake (partitioned by year/month)
   - Results stored in S3, presigned URL returned

5. **QuickSight Dashboard** (optional for enterprise users)
   - QuickSight connects to Athena as data source
   - Pre-built dashboards:
     - Claim approval rate by hospital
     - Top rejection reasons by policy type
     - Model performance metrics (accuracy, precision, recall)
   - Embedded in ClaimLens dashboard via QuickSight SDK

**Data Pipeline**:
- DynamoDB Streams → Lambda → S3 (Parquet format)
- AWS Glue Crawler: Discovers schema, updates Athena tables
- Glue ETL Job: Nightly aggregation for reporting tables

### 3.6 Model Retraining Flow

**Actors**: ML engineer, SageMaker Pipelines

**Preconditions**: New labeled claim data available

**Flow**:

1. **Scheduled trigger** (weekly via EventBridge)
   - EventBridge rule: `cron(0 2 ? * SUN *)`
   - Triggers Lambda: `InitiateModelRetraining`

2. **Lambda: InitiateModelRetraining**
   - Starts SageMaker Pipeline execution: `ApprovalModelRetrainingPipeline`

3. **SageMaker Pipeline Steps**:
   
   **Step 1: Data Preparation**
   - Processing Job: Extract claims from DynamoDB (last 90 days)
   - Filter: Only claims with ground truth labels (actual approval/rejection)
   - Transform: Feature engineering (entity counts, policy match scores)
   - Output: Training dataset in S3 (CSV format)
   
   **Step 2: Model Training**
   - Training Job: XGBoost algorithm on ml.m5.xlarge
   - Hyperparameters: max_depth=5, eta=0.1, objective=binary:logistic
   - Training data: 80% of dataset
   - Validation data: 20% of dataset
   - Output: Model artifacts in S3
   
   **Step 3: Model Evaluation**
   - Processing Job: Calculate metrics (accuracy, precision, recall, AUC)
   - Condition: If accuracy > 0.85, proceed to deployment
   - If accuracy < 0.85, send SNS alert to ML team, halt pipeline
   
   **Step 4: Model Registration**
   - Register model in SageMaker Model Registry
   - Tag with version, training date, metrics
   - Approval status: "PendingManualApproval"
   
   **Step 5: A/B Testing Deployment**
   - Create new SageMaker Endpoint variant: `variant-new`
   - Traffic split: 90% to current model, 10% to new model
   - Monitor for 48 hours
   
   **Step 6: Full Deployment** (manual approval required)
   - ML engineer reviews A/B test results in CloudWatch
   - If new model performs better, update traffic to 100%
   - Delete old endpoint variant

4. **Model Monitoring** (continuous)
   - SageMaker Model Monitor: Detects data drift
   - CloudWatch alarms: Alert if prediction latency increases
   - Data Capture: Log all predictions for future retraining

**Automation**:
- Entire pipeline runs without manual intervention (except final approval)
- Cost: ~$50 per retraining run (spot instances for training)

## 4. Data Models

### 4.1 DynamoDB Tables

**Claims Table**
```json
{
  "tenant_id": "hospital-abc",           // Partition Key
  "claim_id": "claim-123e4567",          // Sort Key
  "status": "PROCESSED",                 // UPLOADED | PROCESSING | PROCESSED | FAILED
  "submission_date": "2026-02-15T10:30:00Z",
  "patient_id": "patient-789",
  "claim_amount": 15000.00,
  "approval_score": 0.87,
  "entities": {
    "medications": ["Aspirin", "Lisinopril"],
    "procedures": ["Cardiac Catheterization"],
    "diagnoses": ["Coronary Artery Disease"]
  },
  "matched_policy_clauses": ["clause-001", "clause-045"],
  "documents": {
    "discharge_summary": "s3://claimlens-docs/.../discharge.pdf",
    "billing_codes": "s3://claimlens-docs/.../billing.csv"
  },
  "created_at": "2026-02-15T10:30:00Z",
  "updated_at": "2026-02-15T10:35:00Z"
}
```

**PolicyClauses Table**
```json
{
  "policy_id": "policy-abc123",          // Partition Key
  "clause_id": "clause-001",             // Sort Key
  "text": "Cardiac procedures are covered up to $50,000 per year...",
  "category": "COVERAGE_LIMIT",
  "embedding_indexed": true,
  "created_at": "2026-01-01T00:00:00Z"
}
```

**ReasoningTraces Table**
```json
{
  "claim_id": "claim-123e4567",          // Partition Key
  "timestamp": "2026-02-15T10:35:00Z",   // Sort Key
  "reasoning_text": "This claim is likely to be approved because...",
  "matched_clauses": [
    {
      "clause_id": "clause-001",
      "relevance_score": 0.92,
      "text": "Cardiac procedures are covered..."
    }
  ],
  "model_version": "approval-model-v3",
  "bedrock_model": "anthropic.claude-3-sonnet"
}
```

### 4.2 RDS PostgreSQL Schema

**audit_logs Table**
```sql
CREATE TABLE audit_logs (
  id SERIAL PRIMARY KEY,
  tenant_id VARCHAR(50) NOT NULL,
  user_id VARCHAR(50) NOT NULL,
  action VARCHAR(100) NOT NULL,
  resource_type VARCHAR(50),
  resource_id VARCHAR(100),
  ip_address INET,
  user_agent TEXT,
  timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
  details JSONB
);

CREATE INDEX idx_audit_tenant_time ON audit_logs(tenant_id, timestamp DESC);
```

**claim_history Table**
```sql
CREATE TABLE claim_history (
  id SERIAL PRIMARY KEY,
  tenant_id VARCHAR(50) NOT NULL,
  claim_id VARCHAR(100) NOT NULL,
  status VARCHAR(50) NOT NULL,
  approval_score DECIMAL(5,4),
  submission_date TIMESTAMP NOT NULL,
  processing_duration_ms INTEGER,
  model_version VARCHAR(50),
  created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_claim_history_tenant_date ON claim_history(tenant_id, submission_date DESC);
```

### 4.3 OpenSearch Index Schema

**policy-clauses Index**
```json
{
  "mappings": {
    "properties": {
      "policy_id": { "type": "keyword" },
      "clause_id": { "type": "keyword" },
      "text": { "type": "text" },
      "category": { "type": "keyword" },
      "embedding": {
        "type": "knn_vector",
        "dimension": 768,
        "method": {
          "name": "hnsw",
          "space_type": "cosinesimil",
          "engine": "nmslib"
        }
      },
      "created_at": { "type": "date" }
    }
  }
}
```

**Query Example** (k-NN search):
```json
{
  "size": 10,
  "query": {
    "knn": {
      "embedding": {
        "vector": [0.123, 0.456, ...],
        "k": 10
      }
    }
  }
}
```

## 5. Security Implementation Details

### 5.1 Authentication Flow (Cognito)

1. User enters credentials in React app
2. App calls Cognito InitiateAuth API
3. Cognito returns JWT tokens (ID token, Access token, Refresh token)
4. App stores tokens in browser localStorage (encrypted)
5. All API requests include ID token in Authorization header
6. API Gateway validates token signature using Cognito public keys
7. Lambda extracts tenant_id and user_id from token claims

### 5.2 Authorization Model (IAM + Cognito)

**Role Hierarchy**:
- `SuperAdmin`: Full access to all tenants (ClaimLens internal)
- `TenantAdmin`: Manage users, policies within tenant
- `BillingManager`: Submit claims, view results
- `Auditor`: Read-only access to claims and audit logs

**IAM Policy Example** (Lambda execution role):
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:Query"
      ],
      "Resource": "arn:aws:dynamodb:us-east-1:123456789012:table/Claims",
      "Condition": {
        "ForAllValues:StringEquals": {
          "dynamodb:LeadingKeys": ["${cognito-identity.amazonaws.com:sub}"]
        }
      }
    }
  ]
}
```

### 5.3 Data Encryption

**At Rest**:
- S3: SSE-KMS with customer-managed key `claimlens-s3-key`
- DynamoDB: Encryption enabled with AWS-managed key
- RDS: TDE with customer-managed key `claimlens-rds-key`
- EBS volumes: Encrypted with default AWS-managed key

**In Transit**:
- API Gateway: TLS 1.2+ enforced
- VPC Endpoints: Private connectivity to AWS services
- RDS: SSL/TLS connections required (rds.force_ssl=1)

### 5.4 Network Security

**VPC Configuration**:
- Internet Gateway: Only for public subnets (ALB, NAT Gateway)
- NAT Gateway: Allows private subnets to access internet (for AWS API calls)
- VPC Endpoints: S3, DynamoDB, SageMaker, Secrets Manager (no internet routing)

**Security Group Rules**:
- Lambda SG: Outbound to RDS (5432), OpenSearch (443), SageMaker (443)
- RDS SG: Inbound from Lambda SG only (5432)
- OpenSearch SG: Inbound from Lambda SG only (443)

## 6. Cost Optimization Strategies

### 6.1 Compute Costs
- **Lambda**: Pay-per-invocation, no idle costs
- **SageMaker**: Use Spot Instances for training (70% savings)
- **SageMaker Endpoints**: Auto-scale down to 1 instance during off-hours
- **RDS**: Reserved Instances for baseline capacity (40% savings)

### 6.2 Storage Costs
- **S3 Lifecycle Policies**: 
  - Standard → Intelligent-Tiering after 30 days
  - Intelligent-Tiering → Glacier after 90 days
  - Glacier → Deep Archive after 1 year
- **DynamoDB**: On-demand pricing (no over-provisioning)
- **RDS Snapshots**: Delete snapshots older than 30 days

### 6.3 Data Transfer Costs
- **CloudFront**: Cache static assets at edge (reduce S3 data transfer)
- **VPC Endpoints**: Eliminate NAT Gateway data transfer charges for AWS services
- **S3 Transfer Acceleration**: Only for large file uploads (>100MB)

**Estimated Monthly Cost** (1,000 claims/day):
- Lambda: $200
- SageMaker: $500 (2 endpoints, auto-scaling)
- RDS: $300 (db.r6g.xlarge reserved)
- DynamoDB: $150 (on-demand)
- S3: $100 (1TB storage)
- OpenSearch: $400 (3-node cluster)
- Data Transfer: $50
- **Total: ~$1,700/month**

## 7. Disaster Recovery & High Availability

### 7.1 RTO/RPO Targets
- **RTO** (Recovery Time Objective): 1 hour
- **RPO** (Recovery Point Objective): 5 minutes

### 7.2 Backup Strategy
- **DynamoDB**: Point-in-time recovery (35-day window)
- **RDS**: Automated daily snapshots, 30-day retention
- **S3**: Versioning enabled, cross-region replication to us-west-2

### 7.3 Multi-AZ Deployment
- **RDS**: Multi-AZ with automatic failover
- **OpenSearch**: 3 data nodes across 3 AZs
- **ElastiCache**: Multi-AZ with automatic failover
- **Lambda**: Automatically deployed across AZs

### 7.4 Disaster Recovery Procedure
1. Detect outage via CloudWatch alarms
2. Trigger Lambda: `InitiateDisasterRecovery`
3. Restore RDS from latest snapshot in secondary region
4. Update Route 53 DNS to point to secondary region API Gateway
5. Verify data integrity and resume operations
6. Estimated recovery time: 30-45 minutes

## 8. Compliance & Audit

### 8.1 HIPAA Compliance Checklist
- [x] AWS BAA signed
- [x] All data encrypted at rest (KMS)
- [x] All data encrypted in transit (TLS 1.2+)
- [x] Access controls via IAM and Cognito
- [x] Audit logging via CloudTrail
- [x] VPC isolation for sensitive workloads
- [x] MFA for administrative access
- [x] Automated backup and recovery

### 8.2 Audit Trail Requirements
- **CloudTrail**: All API calls logged with user identity
- **Application Logs**: All claim access logged to RDS audit_logs table
- **Data Access**: S3 object-level logging for PHI documents
- **Retention**: 7 years (HIPAA requirement)

### 8.3 Compliance Reporting
- **AWS Config**: Monthly compliance reports
- **AWS Artifact**: Download SOC 2, HIPAA attestations
- **Custom Reports**: Lambda generates quarterly audit reports from RDS

## 9. Testing Strategy

### 9.1 Unit Testing
- Lambda functions: Jest (Node.js), pytest (Python)
- Coverage target: >80%
- Mocking: AWS SDK calls mocked using aws-sdk-mock

### 9.2 Integration Testing
- Step Functions: Test workflows end-to-end in staging environment
- API Gateway: Postman collections for API testing
- SageMaker: Model validation on holdout test set

### 9.3 Load Testing
- Tool: AWS Distributed Load Testing solution
- Scenario: 10,000 concurrent claim submissions
- Target: <500ms API response time at p95

### 9.4 Security Testing
- AWS Inspector: Automated vulnerability scanning
- Penetration testing: Annual third-party audit
- OWASP Top 10: Addressed in API Gateway and Lambda code

## 10. Deployment Strategy

### 10.1 Infrastructure as Code
- **Tool**: AWS CDK (TypeScript)
- **Stacks**: 
  - `NetworkStack`: VPC, subnets, security groups
  - `DataStack`: DynamoDB, RDS, S3, OpenSearch
  - `ComputeStack`: Lambda, API Gateway, Step Functions
  - `MLStack`: SageMaker endpoints, Bedrock configuration
  - `MonitoringStack`: CloudWatch dashboards, alarms

### 10.2 CI/CD Pipeline
- **Source**: GitHub
- **Build**: AWS CodeBuild
- **Deploy**: AWS CodePipeline
- **Stages**:
  1. Source: GitHub webhook triggers pipeline
  2. Build: Run tests, build Lambda packages
  3. Deploy to Dev: CDK deploy to dev account
  4. Integration Tests: Run automated tests
  5. Deploy to Staging: CDK deploy to staging account
  6. Manual Approval: Product owner approves
  7. Deploy to Production: Blue-green deployment

### 10.3 Blue-Green Deployment
- API Gateway stages: `blue` (current), `green` (new)
- Route 53 weighted routing: 90% blue, 10% green
- Monitor for 1 hour, then switch to 100% green
- Rollback: Switch Route 53 back to blue (< 5 minutes)

## 11. Correctness Properties

### Property 1: Data Integrity
**Statement**: All uploaded documents must be retrievable and unmodified

**Validation**:
- S3 versioning ensures document immutability
- MD5 checksum validation on upload and download
- CloudTrail logs all S3 access for audit

**Test**: Upload document, retrieve, compare checksums

### Property 2: Approval Score Consistency
**Statement**: For identical claims, approval scores must be deterministic

**Validation**:
- SageMaker endpoint uses fixed model version
- No randomness in feature extraction
- Cache results in ElastiCache for consistency

**Test**: Submit same claim twice, verify scores match

### Property 3: Audit Completeness
**Statement**: All claim access must be logged

**Validation**:
- Lambda logs all DynamoDB queries to RDS audit_logs
- CloudTrail logs all API calls
- S3 object-level logging for document access

**Test**: Access claim, verify log entry exists in audit_logs table

### Property 4: Multi-Tenant Isolation
**Statement**: Users can only access claims within their tenant

**Validation**:
- DynamoDB queries filter by tenant_id from Cognito token
- IAM policies enforce tenant-level access
- Integration tests verify cross-tenant access fails

**Test**: Attempt to access claim from different tenant, verify 403 Forbidden

### Property 5: Encryption Enforcement
**Statement**: All PHI data must be encrypted at rest and in transit

**Validation**:
- AWS Config rules enforce encryption on S3, RDS, DynamoDB
- API Gateway requires TLS 1.2+
- Automated compliance checks in CI/CD pipeline

**Test**: Attempt to create unencrypted S3 bucket, verify Config blocks it

## 12. Future Enhancements

### Phase 2 Features
- Real-time claim status webhooks (EventBridge → API Gateway → Customer endpoint)
- Mobile app for claim tracking (AWS Amplify + React Native)
- Multi-language support (Amazon Translate)

### Phase 3 Features
- Prior authorization prediction
- Denial appeal letter generation (Bedrock)
- Fraud detection models (SageMaker Autopilot)

### Phase 4 Features
- Predictive claim cost modeling
- Provider network optimization
- Integration with EHR systems (HL7 FHIR)

---

**Document Version**: 1.0  
**Last Updated**: 2026-02-15  
**Author**: ClaimLens AI Architecture Team  
**AWS Services Used**: 25+ managed services, zero self-hosted infrastructure
