import asyncio
import os
from typing import List, Dict, Tuple

import pandas as pd
from pymilvus import Collection
from utils.core.logging import get_project_logger
from utils.ai.embedding_client import get_embedding_client
from utils.database.connections import MilvusConnectionManager

logger = get_project_logger(__name__)


class ResumeScorer:
    """Resume scorer, responsible for calculating resume scores"""

    def __init__(self):
        self.embedding_client = get_embedding_client()

    async def get_embedding(self, text: str) -> List[float]:
        """
        Asynchronously get text embedding vector.

        Args:
            text (str): Input text

        Returns:
            List[float]: Embedding vector, returns None if error occurs
        """
        return await self.embedding_client.aembed_query(text)

    async def calculate_resume_scores_for_collection(
        self,
        collection: Collection,
        query_contents: List[Dict[str, str]],
        field_relevance_scores: Dict[str, float],
        scoring_method: str = "hybrid",
        max_results: int = 100,
        top_similarities_count: int = 3,
        similarity_threshold: float = 0.5,
        decay_factor: float = 0.35,
    ) -> List[Tuple[str, float]]:
        """
        Asynchronously calculate resume scores for a single collection.

        Args:
            collection (Collection): Milvus collection
            query_contents (List[Dict[str, str]]): List of query contents
            field_relevance_scores (Dict[str, float]): Field relevance scores
            scoring_method (str): Scoring method, defaults to 'hybrid'
            max_results (int): Maximum number of results, defaults to 100
            top_similarities_count (int): Number of top similarities to consider, defaults to 3
            similarity_threshold (float): Similarity threshold, defaults to 0.5
            decay_factor (float): Decay factor, defaults to 0.35

        Returns:
            List[Tuple[str, float]]: List of resume IDs and scores
        """
        resume_scores = {}

        for query in query_contents:
            field_name = query["field_name"]
            query_vector = await self.get_embedding(query["query_content"])
            if query_vector is None:
                logger.warning(f"Unable to get embedding for field {field_name}, skipping this query")
                continue

            search_params = {"metric_type": "IP", "params": {"nprobe": 10}}
            # Milvus topk parameter must be in range [1, 1024]
            # For serverless Zilliz Cloud, the maximum limit is 1024
            limit = min(collection.num_entities, 1024) if collection.num_entities > 0 else 1024

            logger.debug(f"Collection: {collection.name} entity count: {collection.num_entities} limit: {limit}")

            results = collection.search(
                data=[query_vector],
                anns_field=field_name,
                param=search_params,
                limit=limit,
                expr=None,
                output_fields=["resume_id"],
            )

            for hits in results:
                for hit in hits:
                    resume_id = hit.entity.get("resume_id")
                    similarity = hit.score

                    if similarity < similarity_threshold:
                        continue

                    if resume_id not in resume_scores:
                        resume_scores[resume_id] = {}
                    if field_name not in resume_scores[resume_id]:
                        resume_scores[resume_id][field_name] = []
                    resume_scores[resume_id][field_name].append(similarity)

        final_scores = {}
        for resume_id, field_scores in resume_scores.items():
            resume_score = 0
            for field_name, similarities in field_scores.items():
                top_similarities = sorted(similarities, reverse=True)[
                    :top_similarities_count
                ]

                if scoring_method == "sum":
                    field_score = sum(top_similarities)
                elif scoring_method == "max":
                    field_score = max(top_similarities)
                elif scoring_method == "hybrid":
                    field_score = max(top_similarities) + decay_factor * sum(
                        top_similarities[1:]
                    )
                else:
                    raise ValueError("Invalid scoring method")

                resume_score += field_score * field_relevance_scores[field_name]

            final_scores[resume_id] = resume_score

        sorted_scores = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_scores[:max_results]

    async def calculate_overall_resume_scores(
        self,
        refined_query: str,
        collection_relevances: List[Dict],
        collection_search_strategies: Dict,
        top_n: int = 3,
    ) -> pd.DataFrame:
        """
        Asynchronously calculate comprehensive resume scores across all collections and return top N resumes.

        Args:
            refined_query (str): Refined query (for logging purposes)
            collection_relevances (List[Dict]): List of collection relevances
            collection_search_strategies (Dict): Collection search strategies
            top_n (int): Number of best matching resumes to return

        Returns:
            pd.DataFrame: DataFrame containing ranked resume scores
        """
        # Use unified connection manager (supports both Zilliz Cloud and local Milvus)
        MilvusConnectionManager.connect()

        all_scores = {}

        async def process_collection(collection_info):
            collection_name = collection_info["collection_name"]
            collection_weight = collection_info["relevance_score"]

            if collection_weight == 0:
                return

            collection = Collection(collection_name)
            collection_strategy = collection_search_strategies[collection_name]

            query_contents = []
            field_relevance_scores = {}
            for query in collection_strategy.vector_field_queries:
                query_contents.append(
                    {
                        "field_name": query.field_name,
                        "query_content": query.query_content,
                    }
                )
                field_relevance_scores[query.field_name] = query.relevance_score

            collection_scores = await self.calculate_resume_scores_for_collection(
                collection=collection,
                query_contents=query_contents,
                field_relevance_scores=field_relevance_scores,
                scoring_method="hybrid",
                max_results=collection.num_entities,
                top_similarities_count=3,
                similarity_threshold=0.5,
                decay_factor=0.35,
            )

            return collection_name, collection_weight, collection_scores

        tasks = [process_collection(info) for info in collection_relevances]
        results = await asyncio.gather(*tasks)

        for result in results:
            if result is not None:
                collection_name, collection_weight, collection_scores = result
                for resume_id, score in collection_scores:
                    if resume_id not in all_scores:
                        all_scores[resume_id] = {"total_score": 0}
                    all_scores[resume_id][collection_name] = score * collection_weight
                    all_scores[resume_id]["total_score"] += score * collection_weight

        df = pd.DataFrame.from_dict(all_scores, orient="index")
        df.index.name = "resume_id"
        df.reset_index(inplace=True)

        df = df.sort_values("total_score", ascending=False).head(top_n)

        for collection_info in collection_relevances:
            if collection_info["collection_name"] not in df.columns:
                df[collection_info["collection_name"]] = 0

        column_order = ["resume_id", "total_score"] + [
            info["collection_name"] for info in collection_relevances
        ]
        df = df[column_order]

        logger.info(f"Resume scoring completed, query: '{refined_query[:50]}...', filtered top {top_n} matching resumes")

        return df
