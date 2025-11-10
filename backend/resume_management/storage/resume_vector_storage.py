"""
Resume vector storage module

This module handles vector storage operations for resume data, using Milvus vector 
database for storage and retrieval. Uses unified database connection management.
"""

import json
from typing import Dict, Any, List
from datetime import datetime
import pandas as pd

from utils.ai.embedding_client import get_embedding, get_embeddings_batch, get_embeddings_batch_async
import asyncio
from utils.core.logging import get_project_logger
from utils.core.exceptions import VectorDBError
from utils.database.vector_db import (
    create_milvus_collection,
    initialize_vector_store,
    update_milvus_records,
)
from utils.database.connections import MilvusConnectionManager

logger = get_project_logger(__name__)


# Load collection configuration
COLLECTIONS_CONFIG_PATH = "data/config/collections_config.json"
with open(COLLECTIONS_CONFIG_PATH, "r", encoding="utf-8") as f:
    COLLECTIONS_CONFIG = json.load(f)["collections"]


def prepare_data_for_milvus(
    data: Dict[str, Any], collection_name: str, resume_id: str
) -> tuple:
    """
    Prepare data for Milvus storage

    Args:
        data (Dict[str, Any]): Raw data
        collection_name (str): Collection name
        resume_id (str): Resume ID

    Returns:
        tuple: Processed data records and vectors
    """
    config = COLLECTIONS_CONFIG[collection_name]
    df = pd.DataFrame(data if isinstance(data, list) else [data])
    df["resume_id"] = resume_id

    # Process all fields to handle None values and special characters
    for column in df.columns:
            df[column] = df[column].apply(lambda x: process_field(x))

    # Get embeddings in batch (much faster with chunk_size=32)
    vectors = {}
    for field in config["embedding_fields"]:
        if field in df.columns:
            texts = df[field].tolist()
            vectors[field] = get_embeddings_batch(texts)

    records = df.to_dict("records")
    
    # Final check: ensure no None values in any field
    for record in records:
        for key, value in record.items():
            if value is None:
                record[key] = ""

    return records, vectors


def process_field(value: Any) -> str:
    """
    Process field value, convert lists and escape special characters

    Args:
        value (Any): Field value

    Returns:
        str: Processed field value
    """
    # Handle None values
    if value is None:
        return ""

    if isinstance(value, list):
        value = " ".join(map(str, value))
    if isinstance(value, str):
        value = value.replace("\\", "\\\\").replace('"', '\\"').replace("'", "\\'")
    return str(value)


def store_resume_in_milvus(resume_data: Dict[str, Any]):
    """
    Store parsed resume data into Milvus (single resume)

    Args:
        resume_data (Dict[str, Any]): Parsed resume data
    """
    # Ensure connection to Milvus
    MilvusConnectionManager.connect()

    try:
        resume_id = resume_data["id"]
        for collection_name in [
            "personal_infos",
            "educations",
            "work_experiences",
            "project_experiences",
            "skills",
        ]:
            config = COLLECTIONS_CONFIG[collection_name]

            # Initialize or create collection
            try:
                collection = initialize_vector_store(collection_name)
            except VectorDBError as e:
                # Collection doesn't exist, create it
                if "does not exist" in str(e):
                    logger.info(f"Collection {collection_name} does not exist, creating it...")
                    collection = create_milvus_collection(config, dim=1024)
                else:
                    raise

            # Prepare data
            data = None
            if collection_name == "personal_infos":
                data = resume_data["personal_info"]
            elif collection_name == "educations":
                data = resume_data["education"]
            elif collection_name == "work_experiences":
                data = resume_data["work_experiences"]
            elif collection_name == "project_experiences" and resume_data.get(
                "project_experiences"
            ):
                data = resume_data["project_experiences"]
            elif collection_name == "skills" and resume_data["personal_info"].get(
                "skills"
            ):
                data = [
                    {"skill": skill} for skill in resume_data["personal_info"]["skills"]
                ]

            if data:
                records, vectors = prepare_data_for_milvus(
                    data, collection_name, resume_id
                )
                update_milvus_records(
                    collection, records, vectors, config["embedding_fields"]
                )

    except Exception as e:
        raise VectorDBError(f"Error storing resume data: {str(e)}", error_code="VECTOR_STORE_ERROR")
    finally:
        MilvusConnectionManager.disconnect()


def prepare_batch_data_for_milvus(
    resume_batch: List[Dict[str, Any]], collection_name: str
) -> tuple:
    """
    Prepare batch data for Milvus storage (embeddings obtained one by one)
    
    Args:
        resume_batch: List of resume data
        collection_name: Collection name
        
    Returns:
        tuple: (all_records, all_vectors)
    """
    config = COLLECTIONS_CONFIG[collection_name]
    all_records = []
    all_vectors = {field: [] for field in config["embedding_fields"]}
    
    # Process each resume and accumulate data
    for resume_data in resume_batch:
        resume_id = resume_data["id"]
        
        # Extract data based on collection type
        data = None
        if collection_name == "personal_infos":
            data = resume_data["personal_info"]
        elif collection_name == "educations":
            data = resume_data["education"]
        elif collection_name == "work_experiences":
            data = resume_data["work_experiences"]
        elif collection_name == "project_experiences" and resume_data.get("project_experiences"):
            data = resume_data["project_experiences"]
        elif collection_name == "skills" and resume_data["personal_info"].get("skills"):
            data = [{"skill": skill} for skill in resume_data["personal_info"]["skills"]]
        
        if data:
            # Use existing prepare_data_for_milvus for single resume
            records, vectors = prepare_data_for_milvus(data, collection_name, resume_id)
            all_records.extend(records)
            
            # Accumulate vectors
            for field, vector_list in vectors.items():
                all_vectors[field].extend(vector_list)
    
    return all_records, all_vectors


async def prepare_batch_data_for_milvus_async(
    resume_batch: List[Dict[str, Any]], collection_name: str
) -> tuple:
    """
    Prepare batch data for Milvus storage using ASYNC embedding (10x faster!)
    
    Uses async concurrency to fetch embeddings much faster than sync version.
    
    Args:
        resume_batch: List of resume data
        collection_name: Collection name
        
    Returns:
        tuple: (all_records, all_vectors)
    """
    config = COLLECTIONS_CONFIG[collection_name]
    all_data = []
    
    # Step 1: Collect all data from all resumes
    for resume_data in resume_batch:
        resume_id = resume_data["id"]
        
        # Extract data based on collection type
        data = None
        if collection_name == "personal_infos":
            data = resume_data["personal_info"]
        elif collection_name == "educations":
            data = resume_data["education"]
        elif collection_name == "work_experiences":
            data = resume_data["work_experiences"]
        elif collection_name == "project_experiences" and resume_data.get("project_experiences"):
            data = resume_data["project_experiences"]
        elif collection_name == "skills" and resume_data["personal_info"].get("skills"):
            data = [{"skill": skill} for skill in resume_data["personal_info"]["skills"]]
        
        if data:
            # Convert to list if not already
            data_list = data if isinstance(data, list) else [data]
            for item in data_list:
                item["resume_id"] = resume_id
                all_data.append(item)
    
    if not all_data:
        return [], {}
    
    # Step 2: Create DataFrame with all data at once
    df = pd.DataFrame(all_data)
    
    # Process all fields to handle None values and special characters
    for column in df.columns:
        df[column] = df[column].apply(lambda x: process_field(x))
    
    # Step 3: Get embeddings in batch ASYNC (much faster!)
    all_vectors = {}
    for field in config["embedding_fields"]:
        if field in df.columns:
            texts = df[field].tolist()
            # Use async batch embedding with concurrency control
            vectors = await get_embeddings_batch_async(texts)
            all_vectors[field] = vectors
    
    # Step 4: Convert to records
    all_records = df.to_dict("records")
    
    # Final check: ensure no None values
    for record in all_records:
        for key, value in record.items():
            if value is None:
                record[key] = ""
    
    return all_records, all_vectors


def store_resumes_batch_in_milvus(resume_batch: List[Dict[str, Any]]):
    """
    Store multiple parsed resumes into Milvus in batch (optimized for performance)

    Args:
        resume_batch (List[Dict[str, Any]]): List of parsed resume data
    
    Returns:
        tuple: (success_count, failed_resumes_list)
    """
    if not resume_batch:
        return 0, []
    
    # Ensure connection to Milvus (connect once for the entire batch)
    MilvusConnectionManager.connect()
    
    success_count = 0
    failed_resumes = []
    
    try:
        # Process each collection type
        for collection_name in [
            "personal_infos",
            "educations",
            "work_experiences",
            "project_experiences",
            "skills",
        ]:
            config = COLLECTIONS_CONFIG[collection_name]

            # Initialize or create collection
            try:
                collection = initialize_vector_store(collection_name)
            except VectorDBError as e:
                if "does not exist" in str(e):
                    logger.info(f"Collection {collection_name} does not exist, creating it...")
                    collection = create_milvus_collection(config, dim=1024)
                else:
                    raise

            # First, delete existing data for these resumes to avoid duplicates
            resume_ids = [r["id"] for r in resume_batch]
            try:
                # Build expression to delete records with these resume_ids
                # Milvus expression format: resume_id in ["ID0001", "ID0002", ...]
                if collection.num_entities > 0:
                    delete_expr = f"resume_id in {json.dumps(resume_ids)}"
                    collection.delete(expr=delete_expr)
                    logger.info(f"Deleted existing data for {len(resume_ids)} resumes from {collection_name}")
            except Exception as e:
                # If deletion fails (e.g., no matching records), just log and continue
                logger.debug(f"No existing data to delete for {collection_name}: {e}")
            
            # Prepare all data for this collection with batch embedding
            try:
                all_records, all_vectors = prepare_batch_data_for_milvus(resume_batch, collection_name)
            except Exception as e:
                logger.error(f"Failed to prepare batch data for {collection_name}: {e}")
                for resume_data in resume_batch:
                    if resume_data.get('id') not in [r['id'] for r in failed_resumes]:
                        failed_resumes.append({'id': resume_data.get('id'), 'error': str(e)})
                continue

            # Batch insert all records for this collection
            if all_records:
                try:
                    # For batch insert, we bypass the query check and directly insert
                    entities = []
                    for field in collection.schema.fields:
                        if field.name == "id":
                            continue  # Skip auto-generated ID field
                        elif field.name.endswith("_vector"):
                            original_field_name = field.name[:-7]
                            if original_field_name in all_vectors:
                                entities.append(all_vectors[original_field_name])
                        else:
                            entities.append([record.get(field.name, "") for record in all_records])
                    
                    collection.insert(entities)
                    collection.load()
                    logger.info(f"Successfully inserted {len(all_records)} records to collection {collection_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to batch insert to {collection_name}: {e}")
                    for resume_data in resume_batch:
                        if resume_data.get('id') not in [r['id'] for r in failed_resumes]:
                            failed_resumes.append({'id': resume_data.get('id'), 'error': f"Batch insert failed: {str(e)}"})
        
        # Count successes (resumes not in failed list)
        success_count = len(resume_batch) - len(set(r['id'] for r in failed_resumes))
        
    except Exception as e:
        logger.error(f"Batch storage error: {e}")
        raise VectorDBError(f"Error storing resume batch: {str(e)}", error_code="VECTOR_BATCH_STORE_ERROR")
    finally:
        MilvusConnectionManager.disconnect()
    
    return success_count, failed_resumes


async def store_resumes_batch_in_milvus_async(resume_batch: List[Dict[str, Any]]):
    """
    Store multiple parsed resumes into Milvus in batch using ASYNC (10x faster!)
    
    Uses async embedding with controlled concurrency (10 concurrent requests) for maximum throughput.

    Args:
        resume_batch (List[Dict[str, Any]]): List of parsed resume data
    
    Returns:
        tuple: (success_count, failed_resumes_list)
    """
    if not resume_batch:
        return 0, []
    
    # Ensure connection to Milvus (connect once for the entire batch)
    MilvusConnectionManager.connect()
    
    failed_resumes = []
    
    try:
        # Process each collection type
        for collection_name in [
            "personal_infos",
            "educations",
            "work_experiences",
            "project_experiences",
            "skills",
        ]:
            config = COLLECTIONS_CONFIG[collection_name]

            # Initialize or create collection
            try:
                collection = initialize_vector_store(collection_name)
            except VectorDBError as e:
                if "does not exist" in str(e):
                    logger.info(f"Collection {collection_name} does not exist, creating it...")
                    collection = create_milvus_collection(config, dim=1024)
                else:
                    raise

            # First, delete existing data for these resumes to avoid duplicates
            resume_ids = [r["id"] for r in resume_batch]
            try:
                if collection.num_entities > 0:
                    delete_expr = f"resume_id in {json.dumps(resume_ids)}"
                    collection.delete(expr=delete_expr)
                    logger.info(f"Deleted existing data for {len(resume_ids)} resumes from {collection_name}")
            except Exception as e:
                logger.debug(f"No existing data to delete for {collection_name}: {e}")
            
            # Prepare all data for this collection with ASYNC batch embedding
            try:
                all_records, all_vectors = await prepare_batch_data_for_milvus_async(resume_batch, collection_name)
            except Exception as e:
                logger.error(f"Failed to prepare batch data for {collection_name}: {e}")
                for resume_data in resume_batch:
                    if resume_data.get('id') not in [r['id'] for r in failed_resumes]:
                        failed_resumes.append({'id': resume_data.get('id'), 'error': str(e)})
                continue

            # Batch insert all records for this collection
            if all_records:
                try:
                    # For batch insert, we bypass the query check and directly insert
                    entities = []
                    for field in collection.schema.fields:
                        if field.name == "id":
                            continue  # Skip auto-generated ID field
                        elif field.name.endswith("_vector"):
                            original_field_name = field.name[:-7]
                            if original_field_name in all_vectors:
                                entities.append(all_vectors[original_field_name])
                        else:
                            entities.append([record.get(field.name, "") for record in all_records])
                    
                    collection.insert(entities)
                    collection.load()
                    
                    logger.info(f"Successfully inserted {len(all_records)} records into {collection_name}")
                except Exception as e:
                    logger.error(f"Failed to insert data into {collection_name}: {e}")
                    for resume_data in resume_batch:
                        if resume_data.get('id') not in [r['id'] for r in failed_resumes]:
                            failed_resumes.append({'id': resume_data.get('id'), 'error': str(e)})

        # Count successes (resumes not in failed list)
        success_count = len(resume_batch) - len(set(r['id'] for r in failed_resumes))
        
    except Exception as e:
        logger.error(f"Batch storage error (async): {e}")
        raise VectorDBError(f"Error storing resume batch (async): {str(e)}", error_code="VECTOR_BATCH_STORE_ERROR_ASYNC")
    finally:
        MilvusConnectionManager.disconnect()
    
    return success_count, failed_resumes


