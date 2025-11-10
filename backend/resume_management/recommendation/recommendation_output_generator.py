import pandas as pd
from typing import Dict, List
from backend.resume_management.storage.resume_repository import ResumeRepository
import asyncio
from utils.core.logging import get_project_logger

logger = get_project_logger(__name__)


class RecommendationOutputGenerator:
    """Resume recommendation output generator, responsible for fetching resume details and preparing final output."""

    def __init__(self):
        pass

    async def fetch_single_resume_details(self, resume_id: str) -> Dict:
        """
        Asynchronously fetch detailed information for a single resume.

        Args:
            resume_id (str): Resume ID

        Returns:
            Dict: Dictionary containing resume details
        """
        full_resume = await asyncio.to_thread(ResumeRepository.get_full_resume, resume_id)
        if full_resume:
            return {
                "resume_id": resume_id,
                "characteristics": full_resume.get("characteristics", ""),
                "experience": full_resume.get("experience_summary", ""),
                "skills_overview": full_resume.get("skills_overview", ""),
            }
        return None

    async def fetch_resume_details(
        self, ranked_resume_scores: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Asynchronously fetch detailed information for ranked resumes.

        Args:
            ranked_resume_scores (pd.DataFrame): DataFrame containing ranked resume scores.

        Returns:
            pd.DataFrame: DataFrame containing resume details.

        Raises:
            ValueError: If input DataFrame is empty.
        """
        if ranked_resume_scores is None or ranked_resume_scores.empty:
            raise ValueError("Ranked resume score data cannot be empty. Unable to fetch resume details.")

        top_resume_ids = ranked_resume_scores["resume_id"].tolist()

        tasks = [
            self.fetch_single_resume_details(resume_id) for resume_id in top_resume_ids
        ]
        resume_details = await asyncio.gather(*tasks)
        resume_details = [detail for detail in resume_details if detail is not None]

        if not resume_details:
            # If no resume details found, create an empty DataFrame with necessary columns
            resume_details_df = pd.DataFrame(columns=["resume_id", "characteristics", "experience", "skills_overview"])
        else:
            resume_details_df = pd.DataFrame(resume_details)

        merged_df = pd.merge(
            ranked_resume_scores, resume_details_df, on="resume_id", how="left"
        )

        logger.info("Retrieved detailed information for candidate resumes")
        return merged_df

    async def prepare_final_output(
        self, resume_details: pd.DataFrame, recommendation_reasons: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Asynchronously prepare final recommendation output.

        Args:
            resume_details (pd.DataFrame): DataFrame containing resume details.
            recommendation_reasons (pd.DataFrame): DataFrame containing recommendation reasons.

        Returns:
            pd.DataFrame: DataFrame containing final recommendation results.

        Raises:
            ValueError: If input DataFrames are empty.
        """
        if (
            resume_details is None
            or resume_details.empty
            or recommendation_reasons is None
            or recommendation_reasons.empty
        ):
            raise ValueError("Resume details or recommendation reasons cannot be empty. Unable to prepare final output.")

        # Use asyncio.to_thread to execute pandas operations asynchronously
        final_recommendations = await asyncio.to_thread(
            pd.merge, resume_details, recommendation_reasons, on="resume_id", how="left"
        )

        columns_order = [
            "resume_id",
            "total_score",
            "characteristics",
            "experience",
            "skills_overview",
            "reason",
        ]
        final_recommendations = final_recommendations[columns_order]

        final_recommendations = await asyncio.to_thread(
            final_recommendations.sort_values, "total_score", ascending=False
        )

        final_recommendations = final_recommendations.rename(
            columns={
                "resume_id": "简历ID",
                "total_score": "总分",
                "characteristics": "个人特征",
                "experience": "工作经验",
                "skills_overview": "技能概览",
                "reason": "推荐理由",
            }
        )

        logger.info("Recommendation results generation completed, ready to display")
        return final_recommendations
