# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

TalentMatch is an AI-powered talent management and HR analytics platform built with Streamlit. The system provides intelligent resume parsing, candidate matching, and recommendation capabilities using vector similarity search and large language models.

## Development Environment

### Prerequisites
- Python 3.12
- uv package manager
- Milvus vector database (or Zilliz Cloud)
- Access to LLM APIs (DeepSeek/SiliconCloud)

### Environment Setup
```bash
# Install dependencies
uv sync

# Copy environment configuration
cp .env.example .env
# Edit .env with your API keys and database configuration
```

### Running the Application
```bash
# Start the Streamlit application
uv run streamlit run frontend/app.py
```

## Architecture

### Core Structure
- **Frontend**: Streamlit-based multi-page web application (`frontend/`)
- **Backend**: Modular Python services for resume processing (`backend/`)
- **Utils**: Shared utilities for LLM integration and vector operations (`utils/`)
- **Data**: Configuration, datasets, and temporary storage (`data/`)

### Key Components

#### Resume Management (`backend/resume_management/`)
- **Extractor**: PDF and text resume parsing with structured data extraction
- **Recommendation**: AI-powered candidate matching using vector similarity
- **Storage**: Hybrid storage with SQL and vector database operations

#### Frontend Pages (`frontend/page/`)
- `resume_parsing.py`: Resume upload and data extraction interface
- `resume_recommendation.py`: Candidate search and matching interface  
- `resume_upload.py`: Batch processing capabilities

#### Utilities (`utils/`)
- `llm_tools.py`: LLM provider abstraction (DeepSeek/SiliconCloud)
- `vector_db_utils.py`: Milvus vector database operations
- `env_loader.py`: Environment configuration management

### Database Architecture
- **Milvus/Zilliz Cloud**: Vector embeddings for similarity search and recommendations
- **SQLite**: LangChain cache storage (`data/llm_cache/langchain.db`)
- **MySQL**: Structured data storage (configured via environment)

## Configuration

### Environment Variables
Key variables in `.env`:
- `LLM_PROVIDER`: AI provider (DEEPSEEK/SILICONCLOUD)
- `LLM_MODEL`: Model name (e.g., Qwen/Qwen2-72B-Instruct)
- `VECTOR_DB_HOST/PORT`: Self-hosted Milvus connection (or use `VECTOR_DB_URI/TOKEN` for Zilliz Cloud)
- `EMBEDDING_API_*`: Text embedding service configuration

### LLM Cache
The system uses SQLite caching for LLM responses. Cache location: `data/llm_cache/langchain.db`

## Data Processing

### Resume Processing Pipeline
1. **Extraction**: PDF/text parsing using resume_extraction_core.py
2. **Vectorization**: Text embedding for similarity search
3. **Storage**: Dual storage in SQL and vector database
4. **Recommendation**: Vector similarity matching with AI-generated reasoning

### Data Import
```bash
# Import resume data
uv run python scripts/import_resume_data.py
```

## System Features
The application focuses on three core talent management functions:
- Resume upload and batch processing
- Intelligent resume parsing and data extraction  
- AI-powered candidate matching and recommendations

## Development Notes

- The application uses Chinese UI elements and supports bilingual content
- Async processing capabilities for handling concurrent operations
- Modular LLM provider system supporting multiple AI services
- Vector similarity search for intelligent candidate matching
- Structured data extraction from unstructured resume content