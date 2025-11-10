"""
Vector database utilities module

Provides Milvus vector database operations, including collection management, 
data insertion, and search.
"""

from typing import List, Dict, Any
from pymilvus import (
    Collection,
    FieldSchema,
    CollectionSchema,
    DataType,
)
from .connections import MilvusConnectionManager
from ..core.logging import get_project_logger
from ..core.exceptions import VectorDBError, ValidationError

# Configure logging
logger = get_project_logger(__name__)


def initialize_vector_store(collection_name: str) -> Collection:
    """
    Initialize or load vector store.

    Args:
        collection_name (str): Collection name.

    Returns:
        Collection: Milvus collection object.

    Raises:
        VectorDBError: If collection does not exist.
    """
    return MilvusConnectionManager.get_collection(collection_name)


def create_milvus_collection(collection_config: Dict[str, Any], dim: int) -> Collection:
    """
    Create Milvus collection with support for multiple vector fields and index creation.

    Args:
        collection_config (Dict[str, Any]): Collection configuration.
        dim (int): Vector dimension.

    Returns:
        Collection: Created Milvus collection object.
    """
    # Ensure connection to Milvus
    MilvusConnectionManager.connect()
    
    fields = [
        FieldSchema(name="id", dtype=DataType.INT64, is_primary=True, auto_id=True),
    ]
    for field in collection_config["fields"]:
        fields.append(
            FieldSchema(name=field["name"], dtype=DataType.VARCHAR, max_length=65535)
        )
        if field.get("is_vector", False):
            fields.append(
                FieldSchema(
                    name=f"{field['name']}_vector", dtype=DataType.FLOAT_VECTOR, dim=dim
                )
            )

    schema = CollectionSchema(fields, collection_config["description"])
    collection = Collection(collection_config["name"], schema)

    # Create indexes for vector fields
    for field in collection.schema.fields:
        if field.name.endswith("_vector"):
            index_params = {
                "metric_type": "IP",
                "index_type": "IVF_FLAT",
                "params": {"nlist": 1024},
            }
            collection.create_index(field.name, index_params)

    collection.load()
    return collection


def update_milvus_records(
    collection: Collection,
    data: List[Dict[str, Any]],
    vectors: Dict[str, List[List[float]]],
    embedding_fields: List[str],
):
    """
    Update records in Milvus collection with support for multiple vector fields.
    Inserts new records if they don't exist.

    Args:
        collection (Collection): Milvus collection object.
        data (List[Dict[str, Any]]): Data to update, each dictionary represents a row.
        vectors (Dict[str, List[List[float]]]): Corresponding vector data, keys are field names, values are vector lists.
        embedding_fields (List[str]): List of field names used for generating vectors.
    """
    try:
        for record in data:
            # Build query expression using all embedding_fields
            query_expr = " && ".join(
                [f"{field} == '{record[field]}'" for field in embedding_fields]
            )
            existing_records = collection.query(
                expr=query_expr,
                output_fields=["id"],
            )

            if existing_records:
                # Update existing records
                collection.delete(expr=f"id in {[r['id'] for r in existing_records]}")

            # Insert records (whether new or updated)
            entities = []
            for field in collection.schema.fields:
                if field.name not in ["id"] and not field.name.endswith("_vector"):
                    entities.append([record.get(field.name)])
                elif field.name.endswith("_vector"):
                    original_field_name = field.name[:-7]  # Remove "_vector" suffix
                    entities.append([vectors[original_field_name][data.index(record)]])

            collection.insert(entities)

        collection.load()
        logger.info(f"Successfully updated {len(data)} records to collection {collection.name}")
        
    except Exception as e:
        logger.error(f"Failed to update vector records: {e}")
        raise VectorDBError(f"Failed to update vector records: {e}", error_code="VECTOR_UPDATE_ERROR")