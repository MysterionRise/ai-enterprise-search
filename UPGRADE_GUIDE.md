# Upgrade Guide: OpenSearch 3.0 and Dependencies Update

**Date**: 2025-11-18
**Version**: Major upgrade from 2.x to 3.x stack

---

## 🚀 What's New

### OpenSearch 3.0.0 (from 2.11.1)
- **9.5x performance improvement** over OpenSearch 1.3
- **Apache Lucene 10** with sparse indexing for better query performance
- **25% faster range queries** through optimization
- **75% reduction in p90 latency** for high-cardinality queries
- **2.5x faster k-NN queries** with concurrent segment search (enabled by default)
- **GPU acceleration** support (NVIDIA cuVS) for vector search
  - 9.3x faster index builds
  - 3.75x cost reduction
- **gRPC support** for faster data transport
- **Pull-based ingestion** for Kafka and Kinesis
- **Improved security framework** (replaces Java Security Manager)
- **OpenSearch Workspaces** for multi-tenant dashboards
- **Model Context Protocol (MCP)** native support

### Python Dependencies
All dependencies updated to end of 2024/early 2025 versions:

| Package | Old Version | New Version | Key Changes |
|---------|-------------|-------------|-------------|
| **fastapi** | 0.104.1 | 0.115.5 | Performance improvements, bug fixes |
| **opensearch-py** | 2.4.2 | 3.0.0 | OpenSearch 3.0 compatibility |
| **sentence-transformers** | 2.2.2 | 3.3.1 | Better model support, performance |
| **torch** | 2.1.2 | 2.5.1 | Latest PyTorch with optimizations |
| **transformers** | 4.35.2 | 4.47.1 | Latest Hugging Face models |
| **celery** | 5.3.4 | 5.4.0 | Stability improvements |
| **pandas** | 2.1.4 | 2.2.3 | Performance and bug fixes |
| **numpy** | 1.26.2 | 2.1.3 | NumPy 2.0+ (breaking changes!) |
| **prefect** | 2.14.11 | 3.1.9 | Prefect 3.0 (major upgrade) |

### Infrastructure
- **Apache Tika**: 2.9.1 → 3.0.0 (major version)
- **Prometheus**: 2.48.0 → 3.0.1 (major version)
- **Grafana**: 10.2.2 → 11.3.0 (major version)

---

## ⚠️ Breaking Changes

### OpenSearch 3.0
1. **Lucene 10 Index Format**: Old indices may need reindexing
2. **Security Framework**: New Java agent replaces Security Manager
3. **API Changes**: Some API endpoints may have changed
4. **Concurrent Segment Search**: Now enabled by default for k-NN (may affect query behavior)

### NumPy 2.0+
- API changes in array handling
- May require code updates if using advanced NumPy features
- Most libraries now compatible, but test thoroughly

### Prefect 3.0
- Major API changes if using workflow orchestration
- New UI and features
- Migration guide: https://docs.prefect.io/3.0/

### Prometheus 3.0
- Configuration file format changes
- May need to update `prometheus.yml` if using custom configs

### Grafana 11.x
- New features and UI improvements
- Dashboard compatibility mostly preserved

---

## 📋 Migration Steps

### Step 1: Backup Current Data
```bash
# Stop services
docker-compose down

# Backup OpenSearch data (if you have important data)
cp -r ./volumes/opensearch-data ./backup/opensearch-data-$(date +%Y%m%d)

# Backup PostgreSQL
docker-compose up -d postgres
docker-compose exec postgres pg_dump -U searchuser enterprise_search > backup/postgres-$(date +%Y%m%d).sql
docker-compose down
```

### Step 2: Clean Up Old Containers and Volumes (Optional)
```bash
# CAUTION: This will delete all data!
docker-compose down -v

# Remove old images
docker rmi opensearchproject/opensearch:2.11.1
docker rmi opensearchproject/opensearch-dashboards:2.11.1
docker rmi apache/tika:2.9.1.0
docker rmi prom/prometheus:v2.48.0
docker rmi grafana/grafana:10.2.2
```

### Step 3: Pull New Images
```bash
# Pull all updated images
docker-compose pull
```

### Step 4: Update Python Dependencies
```bash
# If running locally (outside Docker)
pip install -r requirements.txt

# If using Docker, rebuild images
docker-compose build api worker
```

### Step 5: Start Services
```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f opensearch
```

### Step 6: Initialize Indices (If Starting Fresh)
```bash
# Wait for OpenSearch to be healthy
docker-compose exec api python scripts/init_indices.py

# Load mock data (optional)
docker-compose exec api python scripts/generate_mock_data.py
docker-compose exec api python scripts/load_mock_data.py
```

### Step 7: Reindex Existing Data (If Upgrading with Data)
```bash
# OpenSearch 3.0 may require reindexing from old format
# Use OpenSearch Reindex API

# Example: Reindex old index to new format
curl -X POST "localhost:9200/_reindex" -H 'Content-Type: application/json' -d'
{
  "source": {
    "index": "enterprise-chunks-old"
  },
  "dest": {
    "index": "enterprise-chunks"
  }
}'
```

### Step 8: Verify All Services
```bash
# Check OpenSearch
curl http://localhost:9200/_cluster/health?pretty

# Check API health
curl http://localhost:8000/api/v1/health

# Check RAG health
curl http://localhost:8000/api/v1/rag/health

# Open dashboards
open http://localhost:5601  # OpenSearch Dashboards
open http://localhost:3000  # Grafana
open http://localhost:8000  # Search UI
```

---

## 🧪 Testing Checklist

After upgrade, test the following:

### Basic Functionality
- [ ] Can log in with demo users
- [ ] Search returns results
- [ ] Document upload works
- [ ] ACL filtering works (login as different users)

### Advanced Features
- [ ] RAG answers generate correctly
- [ ] Streaming RAG works
- [ ] Recommendations load (trending, popular)
- [ ] Personalized search works

### Performance
- [ ] Search latency improved (should be faster)
- [ ] k-NN queries faster
- [ ] No error logs

### Monitoring
- [ ] Prometheus metrics collecting
- [ ] Grafana dashboards load
- [ ] Flower (Celery) works

---

## 🐛 Troubleshooting

### OpenSearch Won't Start
```bash
# Check logs
docker-compose logs opensearch

# Common issues:
# 1. Memory limit too low (increase in docker-compose.yml)
# 2. Port conflict (check if 9200 is in use)
# 3. Disk space full

# Solution: Increase memory
# Edit docker-compose.yml:
# OPENSEARCH_JAVA_OPTS: "-Xms2g -Xmx2g"
```

### Index Compatibility Issues
```bash
# If you see "index format too old" errors
# You need to reindex from a snapshot or recreate indices

# Recreate indices (DELETES DATA!)
docker-compose exec api python scripts/init_indices.py --force
```

### Dependency Conflicts
```bash
# If pip install fails with conflicts
# Try installing in a fresh environment

python -m venv venv-new
source venv-new/bin/activate
pip install -r requirements.txt
```

### NumPy 2.0 Compatibility Issues
```bash
# NumPy 2.1.3 is used for best performance with latest libraries
# Some older libraries don't support NumPy 2.x yet

# RESOLVED: unstructured library removed (requires numpy<2)
# Alternative document parsing using:
# - Apache Tika (handles most formats)
# - pypdf (PDF parsing)
# - python-docx (Word documents)
# - python-pptx (PowerPoint)

# If you need unstructured for specific use cases:
# Option 1: Use in separate environment with numpy 1.x
# Option 2: Wait for unstructured to support numpy 2.x
# Option 3: Use docker container with old numpy

# If presidio (PII detection) causes issues, comment it out in requirements.txt
# PII detection is optional for core functionality
```

### Prometheus Config Issues
```bash
# If Prometheus won't start with new version
# Check config compatibility

docker-compose exec prometheus promtool check config /etc/prometheus/prometheus.yml
```

### Performance Not Improved
```bash
# Verify k-NN concurrent search is enabled
curl "localhost:9200/_cluster/settings?pretty"

# Should see: "search.concurrent_segment_search.enabled": "true"

# If not enabled (should be default):
curl -X PUT "localhost:9200/_cluster/settings" -H 'Content-Type: application/json' -d'
{
  "persistent": {
    "search.concurrent_segment_search.enabled": "true"
  }
}'
```

---

## 🎯 GPU Acceleration (Optional)

To enable GPU acceleration for vector search:

### Prerequisites
- NVIDIA GPU with CUDA support
- nvidia-docker installed

### Enable GPU in docker-compose.yml
```yaml
opensearch:
  image: opensearchproject/opensearch:3.0.0
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
```

### Configure k-NN to Use GPU
```bash
# Enable GPU for k-NN indices
curl -X PUT "localhost:9200/enterprise-chunks/_settings" -H 'Content-Type: application/json' -d'
{
  "index": {
    "knn": {
      "algo_param": {
        "engine": "faiss",
        "gpu_cache_size_mb": 1024
      }
    }
  }
}'
```

---

## 📊 Performance Benchmarks

Expected improvements after upgrade:

| Metric | Before (2.11.1) | After (3.0.0) | Improvement |
|--------|----------------|---------------|-------------|
| Search latency (p50) | 50ms | 35ms | 30% faster |
| Search latency (p95) | 150ms | 80ms | 47% faster |
| k-NN queries | 200ms | 80ms | 60% faster |
| Range queries | 100ms | 75ms | 25% faster |
| High-cardinality agg | 400ms | 100ms | 75% faster |

*Actual results may vary based on data size and hardware*

---

## 🔄 Rollback Plan

If upgrade causes issues:

### Quick Rollback
```bash
# Stop services
docker-compose down

# Restore old configuration
git checkout HEAD~1 docker-compose.yml requirements.txt

# Restore data (if backed up)
rm -rf ./volumes/opensearch-data
cp -r ./backup/opensearch-data-YYYYMMDD ./volumes/opensearch-data

# Start old version
docker-compose up -d
```

### Long-term Support
- OpenSearch 2.x is still supported
- Consider staying on 2.x if stability is critical
- Plan migration during maintenance window

---

## 📚 Additional Resources

- [OpenSearch 3.0 Release Notes](https://github.com/opensearch-project/opensearch-build/blob/main/release-notes/opensearch-release-notes-3.0.0.md)
- [Lucene 10 Changes](https://lucene.apache.org/core/10_0_0/changes/Changes.html)
- [FastAPI 0.115 Changelog](https://fastapi.tiangolo.com/release-notes/)
- [NumPy 2.0 Migration Guide](https://numpy.org/devdocs/numpy_2_0_migration_guide.html)
- [Prefect 3.0 Migration](https://docs.prefect.io/3.0/guides/migration-guide/)

---

## ✅ Post-Upgrade Validation

Run this validation script:

```bash
#!/bin/bash

echo "🔍 Validating upgrade..."

# Check OpenSearch version
echo -n "OpenSearch version: "
curl -s localhost:9200 | jq -r '.version.number'

# Check API health
echo -n "API health: "
curl -s localhost:8000/api/v1/health | jq -r '.status'

# Check RAG health
echo -n "RAG health: "
curl -s localhost:8000/api/v1/rag/health | jq -r '.status'

# Check document count
echo -n "Document count: "
curl -s localhost:9200/enterprise-chunks/_count | jq -r '.count'

# Check concurrent search enabled
echo -n "Concurrent search: "
curl -s "localhost:9200/_cluster/settings?include_defaults=true" | jq -r '.defaults.search.concurrent_segment_search.enabled'

echo "✅ Validation complete!"
```

---

**Questions or issues?** Open an issue on GitHub or contact the development team.
