from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class QueryRefinement(BaseModel):
    """Query refinement result model"""

    status: Literal["ready", "need_more_info"] = Field(
        ..., description="Whether the query is ready to proceed to the next step"
    )
    content: str = Field(..., description="Content to ask the user or the refined query")


class CollectionRelevance(BaseModel):
    """Resume data collection relevance to user query model"""

    collection_name: str = Field(..., description="Name of the resume data collection")
    relevance_score: float = Field(
        ..., ge=0, le=1, description="Relevance score (float between 0 and 1)"
    )


class ResumeSearchStrategy(BaseModel):
    """Resume search strategy model based on user query"""

    collection_relevances: List[CollectionRelevance] = Field(
        ..., description="List of resume data collection relevances"
    )


class VectorFieldQuery(BaseModel):
    """Query strategy model for a single vector field"""

    field_name: str = Field(..., description="Vector field name")
    query_content: str = Field(..., description="Content for querying")
    relevance_score: float = Field(
        ..., ge=0, le=1, description="Relevance score (float between 0 and 1)"
    )


class CollectionSearchStrategy(BaseModel):
    """Search strategy model for a specific resume data collection"""

    vector_field_queries: List[VectorFieldQuery] = Field(
        ..., description="List of vector field query strategies"
    )
