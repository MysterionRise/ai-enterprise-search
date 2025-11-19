"""Database connection utilities"""

import logging
from collections.abc import Generator
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import RealDictCursor

from src.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseConnection:
    """PostgreSQL database connection manager"""

    def __init__(self):
        self.connection_params = {
            "host": settings.POSTGRES_HOST,
            "port": settings.POSTGRES_PORT,
            "database": settings.POSTGRES_DB,
            "user": settings.POSTGRES_USER,
            "password": settings.POSTGRES_PASSWORD,
        }
        self._connection: psycopg2.extensions.connection | None = None

    def connect(self):
        """Establish database connection"""
        try:
            self._connection = psycopg2.connect(**self.connection_params)
            logger.info("Database connection established")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise

    def close(self):
        """Close database connection"""
        if self._connection:
            self._connection.close()
            logger.info("Database connection closed")

    @contextmanager
    def get_cursor(self, dict_cursor: bool = True) -> Generator:
        """
        Context manager for database cursor

        Args:
            dict_cursor: If True, returns rows as dictionaries

        Yields:
            Database cursor
        """
        if not self._connection or self._connection.closed:
            self.connect()

        cursor_factory = RealDictCursor if dict_cursor else None
        cursor = self._connection.cursor(cursor_factory=cursor_factory)

        try:
            yield cursor
            self._connection.commit()
        except Exception as e:
            self._connection.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            cursor.close()


# Global database instance
db = DatabaseConnection()


@contextmanager
def get_db() -> Generator:
    """
    FastAPI dependency for database access

    Yields:
        Database cursor
    """
    with db.get_cursor() as cursor:
        yield cursor


def execute_query(query: str, params: tuple = None, fetch: bool = True):
    """
    Execute a database query

    Args:
        query: SQL query string
        params: Query parameters
        fetch: If True, fetch and return results

    Returns:
        Query results if fetch=True, None otherwise
    """
    with db.get_cursor() as cursor:
        cursor.execute(query, params)
        if fetch:
            return cursor.fetchall()
        return None


def get_user_by_username(username: str):
    """Get user record by username"""
    query = "SELECT * FROM users WHERE username = %s"
    with db.get_cursor() as cursor:
        cursor.execute(query, (username,))
        return cursor.fetchone()


def get_user_by_email(email: str):
    """Get user record by email"""
    query = "SELECT * FROM users WHERE email = %s"
    with db.get_cursor() as cursor:
        cursor.execute(query, (email,))
        return cursor.fetchone()


def create_user(
    username: str,
    email: str,
    hashed_password: str,
    full_name: str | None = None,
    groups: list[str] = None,
    department: str | None = None,
    country: str | None = None,
):
    """Create a new user"""
    if groups is None:
        groups = ["all-employees"]

    query = """
        INSERT INTO users (username, email, hashed_password, full_name, groups, department, country)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, username, email, full_name, groups, department, country, created_at
    """
    with db.get_cursor() as cursor:
        cursor.execute(
            query, (username, email, hashed_password, full_name, groups, department, country)
        )
        return cursor.fetchone()


def log_search_query(
    query_text: str,
    username: str,
    user_groups: list[str],
    filters: dict = None,
    results_count: int = 0,
):
    """Log a search query for analytics"""
    query = """
        INSERT INTO search_queries (query_text, username, user_groups, filters, results_count)
        VALUES (%s, %s, %s, %s, %s)
    """
    import json

    with db.get_cursor() as cursor:
        cursor.execute(
            query, (query_text, username, user_groups, json.dumps(filters or {}), results_count)
        )
