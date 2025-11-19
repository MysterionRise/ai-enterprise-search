"""Application configuration using Pydantic Settings"""


from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    APP_NAME: str = "Enterprise Search"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # API
    API_V1_PREFIX: str = "/api/v1"

    # Security
    JWT_SECRET_KEY: str = Field(default="change-me-in-production")
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # OpenSearch
    OPENSEARCH_HOST: str = "localhost"
    OPENSEARCH_PORT: int = 9200
    OPENSEARCH_USE_SSL: bool = False
    OPENSEARCH_VERIFY_CERTS: bool = False
    OPENSEARCH_USER: str | None = None
    OPENSEARCH_PASSWORD: str | None = None
    OPENSEARCH_TIMEOUT: int = 30

    # Index names
    DOCUMENTS_INDEX: str = "enterprise-docs"
    CHUNKS_INDEX: str = "enterprise-chunks"

    # PostgreSQL
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "enterprise_search"
    POSTGRES_USER: str = "searchuser"
    POSTGRES_PASSWORD: str = "searchpass123"

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def redis_url(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # Celery
    CELERY_BROKER_URL: str | None = None
    CELERY_RESULT_BACKEND: str | None = None

    @property
    def celery_broker(self) -> str:
        return self.CELERY_BROKER_URL or self.redis_url

    @property
    def celery_backend(self) -> str:
        return self.CELERY_RESULT_BACKEND or self.redis_url

    # Tika Server
    TIKA_SERVER_URL: str = "http://localhost:9998"

    # Embedding Model
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DIMENSION: int = 1024
    EMBEDDING_BATCH_SIZE: int = 32
    EMBEDDING_DEVICE: str = "cpu"  # or "cuda" if GPU available

    # Search Configuration
    DEFAULT_SEARCH_SIZE: int = 10
    MAX_SEARCH_SIZE: int = 100
    HYBRID_SEARCH_BM25_WEIGHT: float = 0.5
    HYBRID_SEARCH_VECTOR_WEIGHT: float = 0.5
    RRF_K: int = 60  # Reciprocal Rank Fusion constant

    # Chunking
    CHUNK_SIZE: int = 512  # tokens
    CHUNK_OVERLAP: int = 128  # tokens

    # Language Detection
    SUPPORTED_LANGUAGES: list[str] = ["en", "fr", "de", "es", "it", "pt", "nl"]

    # PII Detection
    ENABLE_PII_DETECTION: bool = True
    PII_ENTITIES: list[str] = [
        "PERSON",
        "EMAIL_ADDRESS",
        "PHONE_NUMBER",
        "CREDIT_CARD",
        "SSN",
        "PASSPORT",
        "IBAN_CODE",
    ]

    # File Upload
    MAX_UPLOAD_SIZE: int = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS: list[str] = [
        ".pdf",
        ".docx",
        ".doc",
        ".pptx",
        ".ppt",
        ".xlsx",
        ".xls",
        ".txt",
        ".md",
        ".html",
        ".htm",
        ".rtf",
    ]

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
