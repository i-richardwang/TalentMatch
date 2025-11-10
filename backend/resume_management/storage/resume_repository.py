"""
Resume data storage repository module

This module provides a unified interface for resume data storage, integrating 
operations for MySQL and vector databases. It implements the Repository pattern 
to separate data access logic from business logic.
"""

from typing import Dict, Optional, Any, List
from .mysql_base import ResumeTableManager
from utils.core.logging import get_project_logger
from utils.core.exceptions import DatabaseError, StorageError

logger = get_project_logger(__name__)


class ResumeRepository:
    """
    Resume data storage repository class
    
    Provides a unified data access interface that supports:
    - Storage and retrieval of complete resume data
    - Management of upload records
    - Hash value management and deduplication
    """
    
    @staticmethod
    def init_all_tables():
        """Initialize all necessary database tables"""
        return ResumeTableManager.init_all_tables()
    
    # Complete resume data operations
    @staticmethod
    def store_full_resume(resume_data: Dict[str, Any]) -> bool:
        """
        Store complete resume data
        
        Args:
            resume_data: Resume data dictionary
            
        Returns:
            bool: Whether storage was successful
        """
        try:
            data = {
                "resume_id": resume_data.get("id"),
                "personal_info": ResumeTableManager.prepare_json_field(resume_data.get("personal_info", {})),
                "education": ResumeTableManager.prepare_json_field(resume_data.get("education", [])),
                "work_experiences": ResumeTableManager.prepare_json_field(resume_data.get("work_experiences", [])),
                "project_experiences": ResumeTableManager.prepare_json_field(resume_data.get("project_experiences", [])),
                "characteristics": resume_data.get("characteristics", ""),
                "experience_summary": resume_data.get("experience_summary", ""),
                "skills_overview": resume_data.get("skills_overview", ""),
                "resume_format": resume_data.get("resume_format", ""),
                "file_or_url": resume_data.get("file_or_url", "")
            }
            
            ResumeTableManager.insert_or_update("full_resume", data, "resume_id")
            logger.info(f"Resume data stored successfully: {resume_data.get('id')}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to store resume data: {e}")
            raise StorageError(f"Failed to store resume data: {e}", error_code="RESUME_STORE_ERROR")
    
    @staticmethod
    def batch_store_full_resumes(resume_data_list: List[Dict[str, Any]]) -> int:
        """
        Batch store multiple complete resume data
        
        Args:
            resume_data_list: List of resume data dictionaries
            
        Returns:
            int: Number of successfully stored resumes
        """
        try:
            data_list = []
            for resume_data in resume_data_list:
                data = {
                    "resume_id": resume_data.get("id"),
                    "personal_info": ResumeTableManager.prepare_json_field(resume_data.get("personal_info", {})),
                    "education": ResumeTableManager.prepare_json_field(resume_data.get("education", [])),
                    "work_experiences": ResumeTableManager.prepare_json_field(resume_data.get("work_experiences", [])),
                    "project_experiences": ResumeTableManager.prepare_json_field(resume_data.get("project_experiences", [])),
                    "characteristics": resume_data.get("characteristics", ""),
                    "experience_summary": resume_data.get("experience_summary", ""),
                    "skills_overview": resume_data.get("skills_overview", ""),
                    "resume_format": resume_data.get("resume_format", ""),
                    "file_or_url": resume_data.get("file_or_url", "")
                }
                data_list.append(data)
            
            success_count = ResumeTableManager.batch_insert_or_update("full_resume", data_list, "resume_id")
            logger.info(f"Batch stored {success_count} resume records successfully")
            return success_count
            
        except Exception as e:
            logger.error(f"Failed to batch store resume data: {e}")
            raise StorageError(f"Failed to batch store resume data: {e}", error_code="RESUME_BATCH_STORE_ERROR")
    
    @staticmethod
    def get_full_resume(resume_id: str) -> Optional[Dict[str, Any]]:
        """
        Get complete resume data
        
        Args:
            resume_id: Resume ID
            
        Returns:
            Optional[Dict[str, Any]]: Resume data, or None if not found
        """
        try:
            conditions = {"resume_id": resume_id}
            result = ResumeTableManager.select_by_condition("full_resume", conditions)
            
            if not result:
                return None
            
            resume = result[0]
            return {
                "resume_id": resume["resume_id"],
                "personal_info": ResumeTableManager.parse_json_field(resume["personal_info"]),
                "education": ResumeTableManager.parse_json_field(resume["education"]),
                "work_experiences": ResumeTableManager.parse_json_field(resume["work_experiences"]),
                "project_experiences": ResumeTableManager.parse_json_field(resume["project_experiences"]),
                "characteristics": resume["characteristics"] or "",
                "experience_summary": resume["experience_summary"] or "",
                "skills_overview": resume["skills_overview"] or "",
                "resume_format": resume["resume_format"] or "",
                "file_or_url": resume["file_or_url"] or "",
                "created_at": resume.get("created_at"),
                "updated_at": resume.get("updated_at")
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch resume data: {e}")
            raise StorageError(f"Failed to fetch resume data: {e}", error_code="RESUME_FETCH_ERROR")

