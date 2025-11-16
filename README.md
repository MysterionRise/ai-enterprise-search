# AI Enterprise Search Platform

A secure, multilingual, context-aware enterprise search platform with RAG capabilities. Built with open-source technologies and designed for on-premise or cloud deployment.

## 🎯 Features

- **Hybrid Search**: BM25 + k-NN vector search with Reciprocal Rank Fusion (RRF)
- **Semantic Search**: Dense vector embeddings using BAAI bge-m3 (multilingual)
- **Security**: Role-based access control (RBAC) with JWT authentication and ACL filtering
- **Personalization**: Context-aware results based on user's country, department, and groups
- **Multilingual**: Support for English, French, German, Spanish, Italian, Portuguese, Dutch
- **Document Processing**: Parse PDF, DOCX, PPTX, HTML with OCR support for scanned documents
- **Enterprise Sources**: Connectors for ServiceNow, SharePoint, Confluence, and more
- **Observability**: Prometheus metrics, Grafana dashboards, structured logging

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                         FastAPI                             │
│  ┌──────────┐  ┌──────────┐  ┌────────┐  ┌──────────────┐ │
│  │  Auth    │  │  Search  │  │ Ingest │  │   Health     │ │
│  └──────────┘  └──────────┘  └────────┘  └──────────────┘ │
└────────────────────┬────────────────────────────────────────┘
                     │
    ┌────────────────┼────────────────────┐
    │                │                    │
┌───▼────┐   ┌──────▼───────┐   ┌───────▼─────┐
│OpenSearch│   │  PostgreSQL │   │    Redis    │
│ (Search) │   │  (Metadata) │   │   (Cache)   │
└──────────┘   └─────────────┘   └─────────────┘
                                         │
                                 ┌───────▼───────┐
                                 │  Celery       │
                                 │  Workers      │
                                 └───────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.10+ (for local development)
- 8GB+ RAM recommended

### 1. Clone the Repository

```bash
git clone <repository-url>
cd ai-enterprise-search
```

### 2. Set Up Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env if needed (defaults work for local development)
```

### 3. Start Services

```bash
# Start all services (OpenSearch, PostgreSQL, Redis, Tika, API, Workers)
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### 4. Initialize Database and Indices

```bash
# Wait for services to be healthy (check docker-compose ps)

# Initialize OpenSearch indices
docker-compose exec api python scripts/init_indices.py

# Generate mock enterprise data
docker-compose exec api python scripts/generate_mock_data.py

# Load mock data into search index
docker-compose exec api python scripts/load_mock_data.py
```

### 5. Access the Application

- **Search UI**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **OpenSearch Dashboards**: http://localhost:5601
- **Grafana**: http://localhost:3000 (admin/admin)
- **Flower (Celery Monitoring)**: http://localhost:5555

### 6. Test the Search

**Default Demo Users** (password: `password123`):
- `john.doe` - HR department, UK (sees UK-specific content)
- `jane.smith` - Engineering, US (sees US engineering docs)
- `admin` - IT, US, Admin group (full access)

1. Go to http://localhost:8000
2. Login with a demo user
3. Try searches like:
   - "how to request time off"
   - "remote work policy"
   - "kubernetes setup"
   - "expense reimbursement"

Results are **personalized** based on your user's country and department!

## 📚 API Usage

### Authentication

```bash
# Login
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "john.doe", "password": "password123"}'

# Response:
# {"access_token": "eyJ...", "token_type": "bearer", "expires_in": 86400}
```

### Search

```bash
# Search with authentication
curl -X POST http://localhost:8000/api/v1/search/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "query": "remote work policy",
    "size": 10,
    "use_hybrid": true,
    "boost_personalization": true
  }'
```

### Ingest Documents

```bash
# Ingest a document
curl -X POST http://localhost:8000/api/v1/ingest/document \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <your-token>" \
  -d '{
    "source": "confluence",
    "source_id": "PAGE-12345",
    "title": "New Policy Document",
    "content": "Policy content here...",
    "acl_allow": ["all-employees"],
    "country_tags": ["UK"],
    "department": "HR"
  }'
```

### Upload Files

```bash
# Upload PDF/DOCX/etc
curl -X POST http://localhost:8000/api/v1/ingest/upload \
  -H "Authorization: Bearer <your-token>" \
  -F "file=@document.pdf" \
  -F "source=sharepoint" \
  -F "acl_allow=all-employees" \
  -F "country_tags=UK,US"
```

## 🔧 Development

### Local Development (without Docker)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start services (OpenSearch, PostgreSQL, Redis)
docker-compose up -d opensearch postgres redis tika

# Run API server
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Run Celery worker (in another terminal)
celery -A src.workers.tasks worker --loglevel=info
```

### Code Quality

```bash
# Format code
black src/ tests/

# Lint
ruff check src/ tests/

# Type check
mypy src/

# Run tests
pytest tests/ -v --cov=src
```

## 📦 Project Structure

```
ai-enterprise-search/
├── src/
│   ├── api/              # FastAPI application
│   │   ├── main.py       # App entry point
│   │   └── routes/       # API endpoints
│   ├── core/             # Core utilities
│   │   ├── config.py     # Configuration
│   │   ├── security.py   # Authentication
│   │   └── database.py   # Database utilities
│   ├── models/           # Pydantic models
│   │   ├── auth.py       # User/auth models
│   │   ├── documents.py  # Document models
│   │   └── search.py     # Search models
│   ├── services/         # Business logic
│   │   ├── opensearch_service.py  # Search engine
│   │   ├── embedding_service.py   # Text embeddings
│   │   ├── search_service.py      # Hybrid search
│   │   └── ingest_service.py      # Document ingestion
│   ├── utils/            # Utilities
│   │   ├── text_processing.py  # Text utils
│   │   └── document_parser.py  # Document parsing
│   ├── workers/          # Celery workers
│   └── connectors/       # Data source connectors
├── tests/                # Unit and integration tests
├── scripts/              # Utility scripts
│   ├── init_indices.py   # Initialize OpenSearch
│   ├── generate_mock_data.py
│   └── load_mock_data.py
├── config/               # Configuration files
│   ├── postgres/         # Database init scripts
│   ├── prometheus/       # Prometheus config
│   └── grafana/          # Grafana dashboards
├── ui/                   # Web UI
│   └── templates/
│       └── index.html    # Search interface
├── docker/               # Dockerfiles
├── docker-compose.yml    # Local development stack
├── requirements.txt      # Python dependencies
└── README.md
```

## 🔐 Security Features

### Access Control
- **JWT Authentication**: Secure token-based authentication
- **ACL Filtering**: Document-level access control lists
- **Security Trimming**: Query-time filtering based on user groups
- **Group-based Authorization**: Role and department-based access

### Data Protection
- **PII Detection**: Presidio-based PII detection (optional)
- **Encryption**: TLS for data in transit
- **Secrets Management**: Environment-based configuration
- **Audit Logging**: Search query logging for compliance

## 🌍 Multilingual Support

The platform supports multilingual content:

- **Language Detection**: Automatic language detection using langdetect
- **Multilingual Embeddings**: BAAI bge-m3 supports 100+ languages
- **Language Filtering**: Filter results by language
- **Cross-lingual Search**: Find documents in any language

Supported languages: English, French, German, Spanish, Italian, Portuguese, Dutch, and more.

## 📊 Observability

### Metrics (Prometheus)
- Request latency (p50, p95, p99)
- Search query counts
- Index operations
- Error rates

### Logs
- Structured JSON logging
- Request/response logging
- Error tracking
- Search analytics

### Dashboards (Grafana)
- API performance
- Search metrics
- System health
- User activity

## 🔮 Future Enhancements (Phase 2)

- **RAG Integration**: LLM-powered answers with Qwen/Llama
- **Advanced Connectors**: Full ServiceNow, SharePoint, Confluence integration
- **Learning to Rank**: ML-based result ranking
- **Real-time Indexing**: Streaming updates via Kafka
- **Advanced Analytics**: Click-through rate, dwell time analysis
- **Multi-tenancy**: Tenant isolation and management
- **Advanced OCR**: Form recognition, table extraction
- **Voice Search**: Speech-to-text integration

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

## 🆘 Troubleshooting

### Services won't start
```bash
# Check Docker resources (need 8GB+ RAM)
docker stats

# Clean up and restart
docker-compose down -v
docker-compose up -d
```

### OpenSearch cluster health is yellow/red
```bash
# Check cluster status
curl http://localhost:9200/_cluster/health?pretty

# View logs
docker-compose logs opensearch
```

### Embedding model download is slow
```bash
# Pre-download model (will be cached)
docker-compose exec worker python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-m3')"
```

### Search returns no results
```bash
# Verify indices exist
curl http://localhost:9200/_cat/indices?v

# Check document count
curl http://localhost:9200/enterprise-chunks/_count

# Re-index mock data
docker-compose exec api python scripts/load_mock_data.py
```

## 📞 Support

For issues and questions:
- **GitHub Issues**: https://github.com/your-org/ai-enterprise-search/issues
- **Documentation**: See `/docs` endpoint
- **Community**: Join our Slack channel

## 🌟 Acknowledgments

Built with:
- [OpenSearch](https://opensearch.org/) - Search and analytics engine
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [sentence-transformers](https://www.sbert.net/) - State-of-the-art embeddings
- [Apache Tika](https://tika.apache.org/) - Document parsing
- [Celery](https://docs.celeryq.dev/) - Distributed task queue

---

**Made with ❤️ for Enterprise Search**
