# **Technical Roadmap – ClaimLens AI (AI for Bharat Prototype)**

**Prototype Objective**

ClaimLens AI is a clause-aware compliance reasoning engine that pre-validates medical insurance claims before submission. The system ingests discharge summaries, billing data, and policy PDFs; performs structured medical extraction; deterministically splits policy documents into hierarchical clauses; retrieves relevant clauses using a hybrid semantic \+ lexical retrieval pipeline; and generates explainable approval likelihood with risk analysis and corrective suggestions.

The prototype will be fully deployed and testable on AWS.

## **AWS Architecture & Resource Utilization**

**Amazon EC2 (Primary Compute Layer)**  
 Will host:

* FastAPI backend

* Document ingestion & OCR pipeline

* Deterministic clause-splitting engine

* Hybrid retrieval engine (Vector \+ BM25 \+ reranking)

* LLM orchestration layer

Instance type: t3.medium for balanced NLP workload execution.

**Amazon S3**  
 Secure storage for uploaded PDFs, structured claim outputs, and evaluation datasets.

**AWS Bedrock (Controlled Usage)**  
 Used for structured clause-aware reasoning:

* Approval likelihood score

* Compliance risk explanation

* Missing documentation insights

Fallback to locally hosted open-source LLM on EC2 if required for cost efficiency.

**AWS IAM & CloudWatch**  
 Role-based security and active monitoring to optimize credit utilization.

## **Credit Strategy ($100 Allocation)**

* EC2 compute for backend processing

* Controlled Bedrock API usage

* S3 storage

* Monitoring buffer

We will enforce instance shutdown when idle and track daily usage to remain within the allocation.

## **7-Day Execution Plan**

 **Day 1–2:** Infrastructure setup, ingestion pipeline, structured claim extraction.  
 **Day 3:** Hierarchical clause splitting with TOC filtering and metadata tagging.  
 **Day 4:** Hybrid retrieval system (dense \+ lexical \+ reranking).  
 **Day 5:** LLM-based compliance reasoning integration.  
 **Day 6:** Frontend integration and public AWS deployment.  
 **Day 7:** Testing, validation, optimization, and submission readiness.

This roadmap ensures efficient cloud utilization while delivering a functional, explainable, and production-oriented AI compliance prototype within the 7-day window.

Data Strategy

Data Sources  
	•	Publicly available insurance policy wording PDFs (e.g., ICICI Lombard, Niva Bupa).  
	•	Internally curated evaluation queries for benchmarking retrieval quality.

All documents are legal contracts processed at clause level for structured semantic retrieval.

Storage Architecture

1\. Raw Documents  
	•	Stored in Amazon S3 (versioned buckets).

2\. Vector Embeddings  
	•	Generated using Amazon Titan Embeddings (via Amazon Bedrock).  
	•	Stored in Amazon Aurora PostgreSQL using the pgvector extension for scalable vector similarity search.

Aurora enables:  
	•	Efficient vector similarity queries  
	•	Hybrid filtering using SQL \+ metadata  
	•	Scalable relational storage for clause-level metadata

Processing Pipeline  
	1\.	Policy PDFs uploaded to Amazon S3.  
	2\.	Text extraction and clause-aware hierarchical splitting.  
	3\.	Embeddings generated using Titan Embeddings (Bedrock).  
	4\.	Embeddings stored in Aurora (pgvector) along with structured metadata.  
	5\.	Hybrid retrieval using:  
	•	Vector similarity search  
	•	Keyword filtering  
	6\.	Retrieved clauses passed to reasoning layer.

LLM Reasoning Layer  
	•	Powered by Amazon Bedrock.  
	•	Model used: Claude Haiku.  
	•	Responsibilities:  
	•	Legal reasoning over retrieved clauses  
	•	Determining coverage conditions  
	•	Generating structured JSON outputs  
	•	Providing clause references for traceability

Deployment & Scalability  
	•	API Layer: Amazon API Gateway  
	•	Compute: AWS Lambda or Amazon ECS  
	•	Monitoring: Amazon CloudWatch  
	•	Security: IAM-based access control

The system is designed to be scalable, serverless-compatible, and production-ready on AWS infrastructure.

24-Hour Goal

Within the first 24 hours of receiving credits, we will deploy a production-ready AWS-native version of our hybrid RAG system.

First Technical Milestone

Deploy an end-to-end AWS pipeline:  
	1\.	Store policy PDFs in Amazon S3.  
	2\.	Generate embeddings using Amazon Titan Embeddings (Bedrock).  
	3\.	Store embeddings in Amazon Aurora PostgreSQL with pgvector.  
	4\.	Implement hybrid vector retrieval via Aurora.  
	5\.	Integrate Claude Haiku (Bedrock) for structured reasoning.  
	6\.	Expose the system via an API Gateway endpoint.

At the end of 24 hours, we will have:  
	•	A live API endpoint  
	•	Real policy documents indexed in Aurora  
	•	Titan-based embeddings stored and searchable  
	•	Claude Haiku producing structured JSON coverage decisions

Deliverable:  
A working cloud-hosted prototype answering real insurance queries with clause references.

Within the first 24 hours of receiving credits, we will deploy an AWS-native version of our hybrid RAG system. We will store policy PDFs in Amazon S3, generate embeddings using Amazon Titan (Bedrock), and store those embeddings in Amazon Aurora PostgreSQL with pgvector for scalable vector search. We will implement hybrid retrieval within Aurora and integrate Claude Haiku (Bedrock) to perform structured legal reasoning over retrieved clauses. The system will be exposed through an API Gateway endpoint.

By the end of 24 hours, we will have a live cloud-hosted API that indexes real policy documents, performs semantic retrieval, and generates structured JSON coverage decisions with clause references.  
