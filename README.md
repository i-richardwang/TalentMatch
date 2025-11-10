# TalentMatch

**🤖 AI-Powered Talent Recommendation System**

A streamlined AI application focused on intelligent candidate matching and recommendation using vector similarity search and large language models.

> 💡 **Note**: This project is built with vibe coding - prioritizing rapid experimentation and learning over production-ready code. Feel free to explore and learn from it!

[中文版本 Chinese Version](README_CN.md)

## ✨ Features

- **AI Candidate Matching**: Smart recommendations based on vector similarity search
- **Intelligent Query Processing**: Natural language job requirement analysis
- **Multi-dimensional Scoring**: Comprehensive candidate evaluation across skills, experience, and education
- **Data Import Tools**: Easy import of existing resume datasets

## 🚦 Quick Start

### Prerequisites

- Python 3.12+
- uv package manager
- MySQL database
- Milvus vector database (or Zilliz Cloud)

### Installation Steps

1. **Clone the project**
   ```bash
   git clone https://github.com/i-richardwang/TalentMatch.git
   cd TalentMatch
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env file to configure API keys and database connections
   ```

4. **Initialize database**
   ```bash
   uv run python scripts/init_project.py
   ```

5. **Import sample data (optional)**
   ```bash
   uv run python scripts/import_resume_data.py
   ```

6. **Start the application**
   ```bash
   uv run streamlit run frontend/app.py
   ```

The application will start at `http://localhost:8501`.

## 🏗️ Project Structure

```
TalentMatch/
├── frontend/           # Streamlit interface
│   └── page/          # Recommendation page
├── backend/           # Core business logic
│   └── resume_management/
│       ├── recommendation/ # AI recommendation system
│       └── storage/       # Data storage
├── utils/             # Utility modules
│   ├── ai/           # LLM and embedding clients
│   ├── database/     # Database connections
│   └── data/         # Data models
├── scripts/          # Data import and initialization
└── data/             # Configuration and datasets
```

## ⚙️ Configuration

Main configuration options (set in `.env` file):

- **LLM_PROVIDER**: AI service provider (DEEPSEEK/SILICONCLOUD)
- **LLM_MODEL**: Language model to use
- **MYSQL_***: MySQL database connection information
- **VECTOR_DB_***: Vector database configuration
  - Self-hosted Milvus: `VECTOR_DB_HOST`, `VECTOR_DB_PORT`
  - Zilliz Cloud: `VECTOR_DB_URI`, `VECTOR_DB_TOKEN`
- **EMBEDDING_***: Text embedding service configuration

## 🔧 Tech Stack

- **Frontend**: Streamlit
- **Backend**: Python 3.12, Pydantic, AsyncIO
- **AI/ML**: LangChain, Large Language Models, Vector Embeddings
- **Database**: MySQL, Milvus Vector DB

## 📝 Usage

1. **Data Import**: Import existing resume datasets using the provided scripts
2. **Intelligent Query**: Enter job requirements in natural language
3. **AI Analysis**: System analyzes requirements and generates search strategies
4. **Candidate Matching**: Get ranked candidate recommendations with detailed reasoning
5. **Multi-dimensional Scoring**: View comprehensive evaluation across different criteria

## 📄 License

MIT License - See [LICENSE](LICENSE) file for details

## 🤝 Contributing

Issues and Pull Requests are welcome!

---

This is a streamlined demo project showcasing AI-powered talent recommendation capabilities.