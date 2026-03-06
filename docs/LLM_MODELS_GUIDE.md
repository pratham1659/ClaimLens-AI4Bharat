# ClaimLens LLM & Models Configuration Guide

This guide explains how to configure different LLM (Large Language Model) and embedding model options for ClaimLens across different environments.

---

## Table of Contents

1. [Quick Overview](#quick-overview)
2. [LLM Modes](#llm-modes)
3. [Local Development with Ollama](#local-development-with-ollama)
4. [Local Development with Mock LLM](#local-development-with-mock-llm)
5. [Production with AWS Bedrock](#production-with-aws-bedrock)
6. [Embedding Models](#embedding-models)
7. [Switching Models](#switching-models)
8. [Model Comparison](#model-comparison)

---

## Quick Overview

ClaimLens supports **three LLM modes**:

| Mode | Use Case | Cost | Quality | Setup |
|------|----------|------|---------|-------|
| **Mock** | UI Testing | Free | Simulated | Instant |
| **Ollama** | Local Development | Free | Good | ~5 min |
| **Bedrock** | Production | Pay per token | Excellent | AWS Setup |

---

## LLM Modes

### Environment Variables for LLM Selection

```bash
# .env file

# LLM Mode Selection
USE_MOCK_LLM=true|false        # Use mock responses (for UI testing)
BEDROCK_ENABLED=true|false     # Use AWS Bedrock (production)
OLLAMA_ENABLED=true|false      # Use local Ollama (development)

# Ollama Configuration
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b

# AWS Bedrock Configuration
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Embedding Mode
EMBEDDING_MODE=mock|local|bedrock|ollama
```

---

## Local Development with Ollama

**Ollama** is the recommended option for local development with real AI capabilities. It runs open-source LLMs locally on your machine.

### Step 1: Enable Ollama in Docker Compose

Add the Ollama service to your `docker-compose.yml` by uncommenting or adding:

```yaml
services:
  # ... other services ...

  ollama:
    image: ollama/ollama:latest
    container_name: claimlens-ollama
    profiles: ["local", "ollama"]
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    networks:
      - claimlens-network
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]
    # For Apple Silicon (M1/M2/M3), remove the deploy section above

volumes:
  ollama_data:
    name: claimlens-ollama-data
```

### Step 2: Configure Environment

Update your `.env` file:

```bash
# Disable mock, enable Ollama
USE_MOCK_LLM=false
BEDROCK_ENABLED=false
OLLAMA_ENABLED=true
OLLAMA_HOST=http://ollama:11434

# Choose your model (see recommendations below)
OLLAMA_MODEL=llama3.2:3b

# Use local embeddings
EMBEDDING_MODE=local
EMBEDDING_MODEL_SIZE=base
```

### Step 3: Start Services and Pull Model

```bash
# Start services with Ollama
./docker-manage.sh start local

# Pull your chosen model (run once)
docker exec -it claimlens-ollama ollama pull llama3.2:3b

# Verify model is available
docker exec -it claimlens-ollama ollama list
```

### Recommended Ollama Models

| Model | Size | RAM Required | Speed | Quality | Best For |
|-------|------|--------------|-------|---------|----------|
| `llama3.2:1b` | 1.3GB | 4GB | ⚡⚡⚡ | ★★☆ | Quick testing |
| `llama3.2:3b` | 2.0GB | 6GB | ⚡⚡ | ★★★ | **Recommended** |
| `llama3.1:8b` | 4.7GB | 10GB | ⚡ | ★★★★ | Better quality |
| `mistral:7b` | 4.1GB | 10GB | ⚡ | ★★★★ | Alternative |
| `mixtral:8x7b` | 26GB | 48GB | 🐢 | ★★★★★ | Best quality |
| `phi3:mini` | 2.3GB | 6GB | ⚡⚡ | ★★★ | Efficient |
| `gemma2:2b` | 1.6GB | 4GB | ⚡⚡⚡ | ★★★ | Google's model |

### Hardware Requirements for Ollama

| Hardware | Recommended Model | Notes |
|----------|-------------------|-------|
| **8GB RAM** | `llama3.2:1b`, `phi3:mini` | Basic usage |
| **16GB RAM** | `llama3.2:3b`, `mistral:7b` | Good balance |
| **32GB RAM** | `llama3.1:8b`, `codellama:13b` | Better quality |
| **NVIDIA GPU** | Any model | 2-10x faster |
| **Apple Silicon** | Any model | Native acceleration |

### Switching Ollama Models

```bash
# Pull a different model
docker exec -it claimlens-ollama ollama pull mistral:7b

# Update .env
OLLAMA_MODEL=mistral:7b

# Restart backend to use new model
docker restart claimlens-backend
```

---

## Local Development with Mock LLM

**Mock LLM** is perfect for:
- UI/UX development
- Testing frontend components
- CI/CD pipelines
- When you don't need real AI responses

### Configuration

```bash
# .env
USE_MOCK_LLM=true
BEDROCK_ENABLED=false
OLLAMA_ENABLED=false
EMBEDDING_MODE=mock
SKIP_MODEL_LOADING=true
```

### What Mock LLM Returns

The Mock LLM returns realistic, contextual responses:

- **Claim Analysis**: Returns sample approval scores, compliance risks, clause references
- **Medical Extraction**: Returns sample patient info, diagnoses, procedures
- **Policy Questions**: Returns relevant policy information

This allows full application testing without any AI infrastructure.

---

## Production with AWS Bedrock

**AWS Bedrock** provides access to Claude models for production use.

### Available Models

| Model | Model ID | Cost/1K tokens | Speed | Quality |
|-------|----------|----------------|-------|---------|
| **Claude 3.5 Sonnet** | `anthropic.claude-3-5-sonnet-20241022-v2:0` | $0.003 | Fast | ★★★★★ |
| **Claude 3 Haiku** | `anthropic.claude-3-haiku-20240307-v1:0` | $0.00025 | ⚡⚡⚡ | ★★★★ |
| **Claude 3 Sonnet** | `anthropic.claude-3-sonnet-20240229-v1:0` | $0.003 | ⚡⚡ | ★★★★★ |
| **Claude 3 Opus** | `anthropic.claude-3-opus-20240229-v1:0` | $0.015 | ⚡ | ★★★★★★ |

### Configuration

```bash
# .env
USE_MOCK_LLM=false
BEDROCK_ENABLED=true
OLLAMA_ENABLED=false

# AWS Credentials
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key

# Model Selection
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0

# Embedding Model
EMBEDDING_MODE=bedrock
BEDROCK_EMBEDDING_MODEL_ID=amazon.titan-embed-text-v1
```

### Cost Estimation

| Usage Level | Claims/Month | Est. Cost |
|-------------|--------------|-----------|
| Light | 100 | ~$1-5 |
| Medium | 1,000 | ~$10-30 |
| Heavy | 10,000 | ~$100-300 |

---

## Embedding Models

Embeddings are used for semantic search in the RAG (Retrieval Augmented Generation) system.

### Embedding Mode Options

| Mode | Model | Where it Runs | Best For |
|------|-------|---------------|----------|
| `mock` | None | N/A | UI testing |
| `local` | BGE (HuggingFace) | Your machine | Local dev |
| `bedrock` | Amazon Titan | AWS | Production |
| `ollama` | nomic-embed-text | Ollama container | Local dev |

### Local Embedding Models (BGE)

```bash
# .env
EMBEDDING_MODE=local
EMBEDDING_MODEL_SIZE=base  # Options: small, base, large

# Optional: Pre-download models
LOCAL_MODEL_PATH=/app/models
```

| Size | Model | Dimensions | RAM | Quality |
|------|-------|------------|-----|---------|
| `small` | bge-small-en-v1.5 | 384 | 500MB | ★★★ |
| `base` | bge-base-en-v1.5 | 768 | 1GB | ★★★★ |
| `large` | bge-large-en-v1.5 | 1024 | 2GB | ★★★★★ |

### Ollama Embeddings

```bash
# .env
EMBEDDING_MODE=ollama
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Pull the embedding model
docker exec -it claimlens-ollama ollama pull nomic-embed-text
```

---

## Switching Models

### Quick Switch Commands

```bash
# Switch to Mock (for UI testing)
sed -i 's/USE_MOCK_LLM=.*/USE_MOCK_LLM=true/' .env
sed -i 's/EMBEDDING_MODE=.*/EMBEDDING_MODE=mock/' .env
docker restart claimlens-backend

# Switch to Ollama (local AI)
sed -i 's/USE_MOCK_LLM=.*/USE_MOCK_LLM=false/' .env
sed -i 's/OLLAMA_ENABLED=.*/OLLAMA_ENABLED=true/' .env
sed -i 's/BEDROCK_ENABLED=.*/BEDROCK_ENABLED=false/' .env
sed -i 's/EMBEDDING_MODE=.*/EMBEDDING_MODE=local/' .env
docker restart claimlens-backend

# Switch to Bedrock (production)
sed -i 's/USE_MOCK_LLM=.*/USE_MOCK_LLM=false/' .env
sed -i 's/OLLAMA_ENABLED=.*/OLLAMA_ENABLED=false/' .env
sed -i 's/BEDROCK_ENABLED=.*/BEDROCK_ENABLED=true/' .env
sed -i 's/EMBEDDING_MODE=.*/EMBEDDING_MODE=bedrock/' .env
docker restart claimlens-backend
```

### Environment Presets

Create preset files for quick switching:

**`.env.mock`** (UI Testing)
```bash
USE_MOCK_LLM=true
BEDROCK_ENABLED=false
OLLAMA_ENABLED=false
EMBEDDING_MODE=mock
SKIP_MODEL_LOADING=true
```

**`.env.ollama`** (Local AI)
```bash
USE_MOCK_LLM=false
BEDROCK_ENABLED=false
OLLAMA_ENABLED=true
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama3.2:3b
EMBEDDING_MODE=local
EMBEDDING_MODEL_SIZE=base
```

**`.env.bedrock`** (Production)
```bash
USE_MOCK_LLM=false
BEDROCK_ENABLED=true
OLLAMA_ENABLED=false
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
EMBEDDING_MODE=bedrock
```

Switch presets:
```bash
# Use Ollama preset
cp .env.ollama .env
docker restart claimlens-backend
```

---

## Model Comparison

### LLM Comparison for Insurance Claims

| Feature | Mock | Ollama (llama3.2:3b) | Bedrock (Claude Haiku) |
|---------|------|----------------------|------------------------|
| **Setup Time** | Instant | 5 min | 30 min |
| **Cost** | Free | Free | ~$0.25/1K tokens |
| **Response Quality** | Simulated | Good | Excellent |
| **Speed** | Instant | 2-5 sec | 1-2 sec |
| **Offline** | ✅ | ✅ | ❌ |
| **Insurance Domain** | ❌ | ★★★ | ★★★★★ |
| **JSON Parsing** | ✅ | ★★★ | ★★★★★ |

### Decision Guide

```
┌─────────────────────────────────────────────────────────────────┐
│                    WHICH MODEL SHOULD I USE?                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Are you testing UI/frontend only?                               │
│  └─ YES → Use MOCK LLM                                          │
│                                                                  │
│  Do you need real AI responses locally?                          │
│  └─ YES → Use OLLAMA                                            │
│      └─ 8GB RAM: llama3.2:1b or phi3:mini                       │
│      └─ 16GB RAM: llama3.2:3b (recommended)                     │
│      └─ 32GB+ RAM: llama3.1:8b or mistral:7b                    │
│                                                                  │
│  Is this for production/customers?                               │
│  └─ YES → Use AWS BEDROCK                                       │
│      └─ Cost-effective: Claude 3 Haiku                          │
│      └─ Best quality: Claude 3.5 Sonnet                         │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## Troubleshooting

### Ollama Issues

**Model too slow:**
```bash
# Use a smaller model
docker exec -it claimlens-ollama ollama pull llama3.2:1b
# Update .env: OLLAMA_MODEL=llama3.2:1b
```

**Out of memory:**
```bash
# Check memory usage
docker stats claimlens-ollama

# Use a smaller model or increase Docker memory
```

**Model not found:**
```bash
# List available models
docker exec -it claimlens-ollama ollama list

# Pull the model again
docker exec -it claimlens-ollama ollama pull llama3.2:3b
```

### Embedding Issues

**Slow embedding:**
```bash
# Use smaller model
EMBEDDING_MODEL_SIZE=small
```

**CUDA not available:**
```bash
# Fall back to CPU (automatic)
# Or install NVIDIA Container Toolkit
```

### Bedrock Issues

**Access denied:**
- Request model access in AWS Bedrock console
- Verify IAM permissions include `bedrock:InvokeModel`

**Timeout:**
- Check AWS region matches your configuration
- Verify network connectivity to AWS

---

## Summary

| Environment | Recommended Setup |
|-------------|-------------------|
| **UI Testing** | Mock LLM + Mock Embeddings |
| **Local Development** | Ollama (llama3.2:3b) + Local BGE Embeddings |
| **Staging** | Ollama or Bedrock Haiku |
| **Production** | Bedrock (Claude 3.5 Sonnet) + Titan Embeddings |

Start with the recommended setup for your environment, then adjust based on your hardware and quality requirements.
