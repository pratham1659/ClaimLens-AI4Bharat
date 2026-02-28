# README.md

# ClaimLens AI

**AI-Powered Medical Insurance Claim Compliance Platform**

ClaimLens AI is a production-grade SaaS application that pre-validates healthcare claims before submission using advanced AI and natural language processing.


claimlens-ai/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── core/         # Configuration & security
│   │   ├── models/       # Database models
│   │   ├── schemas/      # Pydantic schemas
│   │   ├── services/     # Business logic
│   │   ├── ingestion/    # Document processing
│   │   ├── rag/          # Retrieval system
│   │   ├── llm/          # AI orchestration
│   │   └── auth/         # Authentication
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/   # React components
│   │   ├── pages/        # Page components
│   │   ├── services/     # API services
│   │   ├── hooks/        # Custom hooks
│   │   ├── context/      # React context
│   │   └── utils/        # Utilities
│   ├── Dockerfile
│   └── package.json
├── aws/
│   └── cloudformation/
├── docker-compose.yml
└── README.md


## Features

- 📄 **Document Ingestion**: Upload discharge summaries, insurance policies, and billing data
- 🔍 **Medical Entity Extraction**: Automatic extraction of diagnoses, procedures, and medications
- 🧠 **AI-Powered Analysis**: Claude AI analyzes claims against policy clauses
- 📊 **Compliance Scoring**: Get approval likelihood scores with detailed explanations
- 🔎 **Semantic Search**: Search across policy documents using natural language
- 📈 **Risk Assessment**: Identify compliance risks with actionable recommendations

## Tech Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **Database**: PostgreSQL with pgvector
- **AI/ML**: AWS Bedrock (Claude, Titan Embeddings)
- **Storage**: Amazon S3
- **Authentication**: JWT with role-based access control

### Frontend
- **Framework**: React 18 with Vite
- **Styling**: Tailwind CSS
- **State Management**: React Context + Custom Hooks
- **Charts**: Recharts

### Infrastructure
- **Container**: Docker
- **Orchestration**: AWS ECS Fargate
- **Database**: Aurora PostgreSQL
- **CDN**: CloudFront
- **CI/CD**: GitHub Actions

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 20+
- Python 3.11+
- AWS Account (for Bedrock access)

### Local Development

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/claimlens-ai.git
   cd claimlens-ai
