"""
Database connection management module

This module provides unified database connection management, including MySQL connection 
pooling and Milvus connection management. Supports connection reuse, error handling, 
and resource cleanup.
"""

import os
from contextlib import contextmanager
from typing import Optional, Dict, Any, Generator
import mysql.connector
from mysql.connector import pooling, Error as MySQLError
from pymilvus import connections, Collection, utility, MilvusClient
from pymilvus.exceptions import MilvusException
from ..core.logging import get_project_logger
from ..core.exceptions import DatabaseError, VectorDBError, ConfigurationError

# Configure logging
logger = get_project_logger(__name__)

# Global connection pool variables
_mysql_pool: Optional[pooling.MySQLConnectionPool] = None
_milvus_connected = False
_milvus_client: Optional[MilvusClient] = None


class DatabaseConfig:
    """Database configuration management class"""
    
    @staticmethod
    def get_mysql_config() -> Dict[str, Any]:
        """Get MySQL database configuration"""
        return {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "database": os.getenv("MYSQL_DATABASE", "talentmatch"),
            "charset": "utf8mb4",
            "autocommit": True,
        }
    
    @staticmethod
    def get_milvus_config() -> Dict[str, Any]:
        """
        Get Milvus/Zilliz database configuration
        
        Supports two modes:
        1. Self-hosted Milvus: uses VECTOR_DB_HOST + VECTOR_DB_PORT
        2. Zilliz Cloud: uses VECTOR_DB_URI + VECTOR_DB_TOKEN
        
        Returns:
            Dict[str, Any]: Database configuration dictionary
        """
        # Check if Zilliz Cloud is configured
        vector_db_uri = os.getenv("VECTOR_DB_URI")
        vector_db_token = os.getenv("VECTOR_DB_TOKEN")
        
        if vector_db_uri and vector_db_token:
            # Zilliz Cloud mode (only uri and token needed)
            return {
                "mode": "cloud",
                "uri": vector_db_uri,
                "token": vector_db_token,
            }
        else:
            # Self-hosted Milvus mode
            return {
                "mode": "standalone",
                "host": os.getenv("VECTOR_DB_HOST", "localhost"),
                "port": os.getenv("VECTOR_DB_PORT", "19530"),
                "db_name": os.getenv("VECTOR_DB_DATABASE_RESUME", "resume"),
            }
    


class MySQLConnectionManager:
    """MySQL connection manager"""
    
    @staticmethod
    def init_connection_pool(pool_size: int = 10) -> None:
        """Initialize MySQL connection pool"""
        global _mysql_pool
        
        if _mysql_pool is not None:
            logger.info("MySQL connection pool already exists")
            return
        
        try:
            config = DatabaseConfig.get_mysql_config()
            _mysql_pool = pooling.MySQLConnectionPool(
                pool_name="mysql_pool",
                pool_size=pool_size,
                pool_reset_session=True,
                **config
            )
            logger.info(f"MySQL connection pool initialized successfully with size: {pool_size}")
        except MySQLError as e:
            logger.error(f"Failed to initialize MySQL connection pool: {e}")
            raise DatabaseError(f"Failed to initialize MySQL connection pool: {e}", error_code="MYSQL_POOL_INIT_ERROR")
    
    @staticmethod
    @contextmanager
    def get_connection() -> Generator[mysql.connector.MySQLConnection, None, None]:
        """Context manager for getting MySQL connections"""
        global _mysql_pool
        
        if _mysql_pool is None:
            MySQLConnectionManager.init_connection_pool()
        
        connection = None
        try:
            connection = _mysql_pool.get_connection()
            logger.debug("Successfully obtained MySQL connection")
            yield connection
        except MySQLError as e:
            logger.error(f"Failed to get MySQL connection: {e}")
            if connection:
                connection.rollback()
            raise DatabaseError(f"Failed to get MySQL connection: {e}", error_code="MYSQL_CONNECTION_ERROR")
        finally:
            if connection and connection.is_connected():
                connection.close()
                logger.debug("MySQL connection closed")
    
    @staticmethod
    def execute_query(query: str, params: Optional[tuple] = None, fetch: bool = True) -> Optional[list]:
        """Execute SQL query"""
        with MySQLConnectionManager.get_connection() as conn:
            cursor = conn.cursor(dictionary=True)
            try:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                else:
                    conn.commit()
                    return None
            except MySQLError as e:
                logger.error(f"Failed to execute SQL query: {e}")
                conn.rollback()
                raise DatabaseError(f"Failed to execute SQL query: {e}", error_code="SQL_EXECUTION_ERROR")
            finally:
                cursor.close()
    


class MilvusConnectionManager:
    """Milvus connection manager, supports both self-hosted Milvus and Zilliz Cloud"""
    
    @staticmethod
    def connect() -> None:
        """
        Connect to Milvus/Zilliz database
        
        Auto-detects configuration mode:
        - If VECTOR_DB_URI and VECTOR_DB_TOKEN are configured, uses Zilliz Cloud mode (MilvusClient)
        - Otherwise uses self-hosted Milvus mode (host + port)
        """
        global _milvus_connected, _milvus_client
        
        if _milvus_connected:
            logger.debug("Milvus/Zilliz already connected")
            return
        
        try:
            config = DatabaseConfig.get_milvus_config()
            mode = config.get("mode", "standalone")
            
            if mode == "cloud":
                # Zilliz Cloud mode - use MilvusClient (recommended approach)
                # Note: When using token authentication, do NOT specify db_name parameter
                logger.info(f"Attempting to connect to Zilliz Cloud...")
                logger.info(f"URI: {config['uri']}")
                logger.info(f"Token: {'*' * 20}... (hidden)")
                
                # Create MilvusClient for modern API
                _milvus_client = MilvusClient(
                    uri=config["uri"],
                    token=config["token"]
                )
                logger.info(f"Successfully connected to Zilliz Cloud using MilvusClient")
                
                # Also establish connections.connect() for Collection API compatibility
                # This is needed because some legacy code still uses Collection class
                connections.connect(
                    alias="default",
                    uri=config["uri"],
                    token=config["token"]
                )
                logger.info(f"Also established connections.connect() for Collection API")
            else:
                # Self-hosted Milvus mode
                connections.connect(
                    alias="default",
                    host=config["host"],
                    port=config["port"],
                    db_name=config["db_name"],
                )
                logger.info(f"Successfully connected to Milvus (address: {config['host']}:{config['port']}, database: {config['db_name']})")
            
            _milvus_connected = True
            
        except MilvusException as e:
            logger.error(f"Failed to connect to vector database: {e}")
            raise VectorDBError(f"Failed to connect to vector database: {e}", error_code="MILVUS_CONNECTION_ERROR")
        except Exception as e:
            logger.error(f"Failed to connect to vector database: {e}")
            raise VectorDBError(f"Failed to connect to vector database: {e}", error_code="MILVUS_CONNECTION_ERROR")
    
    @staticmethod
    def disconnect() -> None:
        """Disconnect from Milvus"""
        global _milvus_connected, _milvus_client
        
        try:
            if _milvus_client:
                _milvus_client.close()
                _milvus_client = None
            connections.disconnect("default")
            _milvus_connected = False
            logger.info("Milvus connection disconnected")
        except MilvusException as e:
            logger.error(f"Failed to disconnect from Milvus: {e}")
            raise VectorDBError(f"Failed to disconnect from Milvus: {e}", error_code="MILVUS_DISCONNECT_ERROR")
    
    @staticmethod
    def get_client() -> Optional[MilvusClient]:
        """Get MilvusClient instance (for Zilliz Cloud)"""
        return _milvus_client
    
    @staticmethod
    def get_collection(collection_name: str) -> Collection:
        """Get Milvus collection object"""
        MilvusConnectionManager.connect()
        
        if not utility.has_collection(collection_name):
            raise VectorDBError(f"Collection {collection_name} does not exist", error_code="COLLECTION_NOT_EXISTS")
        
        collection = Collection(collection_name)
        collection.load()
        return collection


# Initialize all connections
def init_all_connections(mysql_pool_size: int = 10) -> None:
    """Initialize all database connections"""
    try:
        MySQLConnectionManager.init_connection_pool(mysql_pool_size)
        MilvusConnectionManager.connect()
        logger.info("All database connections initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database connections: {e}")
        raise ConfigurationError(f"Failed to initialize database connections: {e}", error_code="DB_INIT_ERROR")


# Cleanup resources
def cleanup_connections() -> None:
    """Clean up all database connections"""
    try:
        global _mysql_pool, _milvus_client
        MilvusConnectionManager.disconnect()
        if _mysql_pool:
            _mysql_pool = None
            logger.info("MySQL connection pool closed")
        if _milvus_client:
            _milvus_client = None
        logger.info("Database connection cleanup completed")
    except Exception as e:
        logger.error(f"Failed to cleanup database connections: {e}")
        # Don't throw exceptions for cleanup failures, just log them