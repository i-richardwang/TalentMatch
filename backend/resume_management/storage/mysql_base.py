"""
MySQL operation base class module

Provides unified MySQL database operation interface to avoid code duplication.
Includes common CRUD operations, table management, and transaction handling functionality.
"""

import json
from typing import Dict, Optional, Any, List, Tuple
from datetime import datetime
from utils.database.connections import MySQLConnectionManager
from mysql.connector import Error as MySQLError
from utils.core.logging import get_project_logger
from utils.core.exceptions import DatabaseError, StorageError, ValidationError

logger = get_project_logger(__name__)


class MySQLBaseOperations:
    """MySQL base operations class - provides common database operation methods"""
    
    @staticmethod
    def ensure_table_exists(table_name: str, create_sql: str) -> bool:
        """
        Ensure table exists, create if it doesn't exist
        
        Args:
            table_name (str): Table name
            create_sql (str): SQL statement to create table
            
        Returns:
            bool: Whether operation was successful
        """
        try:
            MySQLConnectionManager.execute_query(create_sql, fetch=False)
            logger.info(f"Table {table_name} initialized successfully")
            return True
        except MySQLError as e:
            logger.error(f"Failed to create table {table_name}: {e}")
            raise DatabaseError(f"Failed to create table {table_name}: {e}", error_code="TABLE_CREATE_ERROR")
    
    @staticmethod
    def insert_or_update(table_name: str, data: Dict[str, Any], 
                        primary_key: str, update_fields: Optional[List[str]] = None) -> bool:
        """
        Generic method to insert or update records
        
        Args:
            table_name (str): Table name
            data (Dict[str, Any]): Data to insert
            primary_key (str): Primary key field name
            update_fields (Optional[List[str]]): List of fields to update, None means update all fields
            
        Returns:
            bool: Whether operation was successful
        """
        try:
            if not data:
                raise ValidationError("Insert data cannot be empty", error_code="EMPTY_DATA")
            
            # Build field list and placeholders
            fields = list(data.keys())
            placeholders = ", ".join(["%s"] * len(fields))
            field_list = ", ".join(fields)
            
            # Build ON DUPLICATE KEY UPDATE clause
            if update_fields is None:
                update_fields = [f for f in fields if f != primary_key]
            
            update_clause = ", ".join([f"{field} = VALUES({field})" for field in update_fields])
            
            sql = f"""
            INSERT INTO {table_name} ({field_list})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
            """
            
            values = tuple(data.values())
            MySQLConnectionManager.execute_query(sql, values, fetch=False)
            logger.debug(f"Table {table_name} record insert/update successful")
            return True
            
        except MySQLError as e:
            logger.error(f"Failed to insert/update table {table_name}: {e}")
            raise StorageError(f"Failed to insert/update table {table_name}: {e}", error_code="INSERT_UPDATE_ERROR")
    
    @staticmethod
    def batch_insert_or_update(table_name: str, data_list: List[Dict[str, Any]], 
                              primary_key: str, update_fields: Optional[List[str]] = None) -> int:
        """
        True batch insert or update multiple records using executemany
        
        Args:
            table_name (str): Table name
            data_list (List[Dict[str, Any]]): List of data to insert
            primary_key (str): Primary key field name
            update_fields (Optional[List[str]]): List of fields to update, None means update all fields
            
        Returns:
            int: Number of successfully inserted/updated records
        """
        try:
            if not data_list:
                return 0
            
            # Get fields from first record (assume all records have same structure)
            fields = list(data_list[0].keys())
            field_list = ", ".join(fields)
            placeholders = ", ".join(["%s"] * len(fields))
            
            # Build ON DUPLICATE KEY UPDATE clause
            if update_fields is None:
                update_fields = [f for f in fields if f != primary_key]
            
            update_clause = ", ".join([f"{field} = VALUES({field})" for field in update_fields])
            
            # Build batch INSERT SQL
            sql = f"""
            INSERT INTO {table_name} ({field_list})
            VALUES ({placeholders})
            ON DUPLICATE KEY UPDATE {update_clause}
            """
            
            # Prepare values list for executemany
            values_list = [
                tuple(data.get(field) for field in fields)
                for data in data_list
            ]
            
            # Execute TRUE batch insert using executemany
            with MySQLConnectionManager.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    # executemany: one SQL with multiple value sets
                    cursor.executemany(sql, values_list)
                    success_count = cursor.rowcount
                    conn.commit()
                    logger.info(f"Successfully batch inserted/updated {len(data_list)} records to table {table_name}")
                except MySQLError as e:
                    conn.rollback()
                    logger.error(f"Failed to batch insert/update table {table_name}: {e}")
                    raise StorageError(f"Failed to batch insert/update table {table_name}: {e}", error_code="BATCH_INSERT_ERROR")
                finally:
                    cursor.close()
            
            return len(data_list)
            
        except Exception as e:
            logger.error(f"Batch insert error: {e}")
            raise StorageError(f"Batch insert error: {e}", error_code="BATCH_INSERT_ERROR")
    
    @staticmethod
    def select_by_condition(table_name: str, conditions: Dict[str, Any], 
                          fields: Optional[List[str]] = None, 
                          limit: Optional[int] = None,
                          order_by: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Generic method to query records by condition
        
        Args:
            table_name (str): Table name
            conditions (Dict[str, Any]): Query conditions
            fields (Optional[List[str]]): List of fields to query, None means query all fields
            limit (Optional[int]): Limit number of returned records
            order_by (Optional[str]): Sort field
            
        Returns:
            List[Dict[str, Any]]: Query result list
        """
        try:
            # Build SELECT clause
            if fields:
                field_list = ", ".join(fields)
            else:
                field_list = "*"
            
            # Build WHERE clause
            where_conditions = []
            values = []
            for key, value in conditions.items():
                where_conditions.append(f"{key} = %s")
                values.append(value)
            
            where_clause = " AND ".join(where_conditions) if where_conditions else "1=1"
            
            # Build complete SQL
            sql = f"SELECT {field_list} FROM {table_name} WHERE {where_clause}"
            
            if order_by:
                sql += f" ORDER BY {order_by}"
            
            if limit:
                sql += f" LIMIT {limit}"
            
            result = MySQLConnectionManager.execute_query(sql, tuple(values))
            return result if result else []
            
        except MySQLError as e:
            logger.error(f"Failed to query table {table_name}: {e}")
            raise StorageError(f"Failed to query table {table_name}: {e}", error_code="SELECT_ERROR")
    


class JSONFieldMixin:
    """JSON field handling mixin class"""
    
    @staticmethod
    def prepare_json_field(value: Any) -> str:
        """Prepare JSON field data"""
        if value is None:
            return json.dumps({})
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False)
        return str(value)
    
    @staticmethod
    def parse_json_field(value: str) -> Any:
        """Parse JSON field data"""
        if not value:
            return {}
        try:
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            return {}


class ResumeTableManager(MySQLBaseOperations, JSONFieldMixin):
    """Resume table manager class - unified management of all resume-related tables"""
    
    # Table structure definitions
    FULL_RESUME_TABLE = """
    CREATE TABLE IF NOT EXISTS full_resume (
        resume_id VARCHAR(255) PRIMARY KEY,
        personal_info JSON,
        education JSON,
        work_experiences JSON,
        project_experiences JSON,
        characteristics TEXT,
        experience_summary TEXT,
        skills_overview TEXT,
        resume_format VARCHAR(50),
        file_or_url TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_resume_id (resume_id),
        INDEX idx_created_at (created_at)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    RESUME_HASH_TABLE = """
    CREATE TABLE IF NOT EXISTS resume_hash (
        id INT AUTO_INCREMENT PRIMARY KEY,
        resume_id VARCHAR(255) NOT NULL,
        file_hash VARCHAR(64) NOT NULL,
        resume_format VARCHAR(50) NOT NULL,
        file_name VARCHAR(255),
        file_url TEXT,
        raw_content LONGTEXT,
        upload_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        is_outdated BOOLEAN DEFAULT FALSE,
        latest_resume_id VARCHAR(255),
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY unique_hash (file_hash),
        INDEX idx_resume_id (resume_id),
        INDEX idx_file_hash (file_hash),
        INDEX idx_upload_date (upload_date),
        INDEX idx_is_outdated (is_outdated)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    RESUME_UPLOADS_TABLE = """
    CREATE TABLE IF NOT EXISTS resume_uploads (
        id INT AUTO_INCREMENT PRIMARY KEY,
        file_name VARCHAR(255) NOT NULL,
        file_path VARCHAR(500),
        upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50) DEFAULT 'pending',
        resume_id VARCHAR(255),
        error_message TEXT,
        INDEX idx_upload_time (upload_time),
        INDEX idx_status (status),
        INDEX idx_resume_id (resume_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """
    
    @classmethod
    def init_all_tables(cls) -> bool:
        """Initialize all resume-related tables"""
        try:
            cls.ensure_table_exists("full_resume", cls.FULL_RESUME_TABLE)
            cls.ensure_table_exists("resume_hash", cls.RESUME_HASH_TABLE)
            cls.ensure_table_exists("resume_uploads", cls.RESUME_UPLOADS_TABLE)
            logger.info("All resume tables initialized successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize resume tables: {e}")
            raise DatabaseError(f"Failed to initialize resume tables: {e}", error_code="RESUME_TABLES_INIT_ERROR")