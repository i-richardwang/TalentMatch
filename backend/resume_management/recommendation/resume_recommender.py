import os
import asyncio
from typing import Dict, Optional, List
from utils.core.logging import get_project_logger
from utils.core.exceptions import ValidationError
from backend.resume_management.recommendation.recommendation_requirements import (
    RecommendationRequirements,
)
from backend.resume_management.recommendation.resume_search_strategy import (
    ResumeSearchStrategyGenerator,
    CollectionSearchStrategyGenerator,
)
from backend.resume_management.recommendation.resume_scorer import ResumeScorer
from backend.resume_management.recommendation.recommendation_reason_generator import (
    RecommendationReasonGenerator,
)
from backend.resume_management.recommendation.recommendation_output_generator import (
    RecommendationOutputGenerator,
)
import uuid

# Configure logging
logger = get_project_logger(__name__)


class ResumeRecommender:
    """
    Main class for the resume recommendation system, integrating all asynchronous components 
    of the recommendation process.
    """

    def __init__(self):
        self.requirements = RecommendationRequirements()
        self.strategy_generator = ResumeSearchStrategyGenerator()
        self.collection_strategy_generator = CollectionSearchStrategyGenerator()
        self.scorer = ResumeScorer()
        self.output_generator = RecommendationOutputGenerator()
        self.reason_generator = RecommendationReasonGenerator()
        self.overall_search_strategy = None
        self.detailed_search_strategy = None
        self.ranked_resume_scores = None
        self.resume_details = None
        self.recommendation_reasons = None
        self.final_recommendations = None
        self.session_id: str = str(uuid.uuid4())


    async def process_query(self, query: str, session_id: Optional[str] = None) -> str:
        """
        Process user's initial query and start the recommendation process.

        Args:
            query (str): User's initial query
            session_id (Optional[str]): Session ID

        Returns:
            str: Processing status, either 'need_more_info' or 'ready'
        """
        return await self.requirements.confirm_requirements(query, session_id)

    def get_next_question(self) -> Optional[str]:
        """
        Retrieve the next question that needs user response, if any.

        Returns:
            Optional[str]: Next question, or None if there are no more questions
        """
        return self.requirements.get_current_question()

    async def process_answer(
        self, answer: str, session_id: Optional[str] = None
    ) -> str:
        """
        Process user's answer to the question and continue the recommendation process.

        Args:
            answer (str): User's answer
            session_id (Optional[str]): Session ID

        Returns:
            str: Processing status, either 'need_more_info' or 'ready'
        """
        return await self.requirements.confirm_requirements(answer, session_id)

    async def generate_overall_search_strategy(
        self, session_id: Optional[str] = None
    ) -> None:
        """
        Generate overall resume search strategy.

        Args:
            session_id (Optional[str]): Session ID
        """
        if session_id is None:
            session_id = self.session_id

        refined_query = self.requirements.get_refined_query()
        if not refined_query:
            logger.error("Refined query not found. Unable to generate search strategy.")
            raise ValidationError("Refined query not found. Unable to generate search strategy.", error_code="MISSING_REFINED_QUERY")

        self.overall_search_strategy = (
            await self.strategy_generator.generate_resume_search_strategy(
                refined_query, session_id
            )
        )

    async def generate_detailed_search_strategy(
        self, session_id: Optional[str] = None
    ) -> None:
        """
        Generate detailed search strategy.

        Args:
            session_id (Optional[str]): Session ID
        """
        if session_id is None:
            session_id = self.session_id

        if not self.overall_search_strategy:
            logger.error("Missing required information to generate detailed search strategy.")
            raise ValidationError("Missing required information to generate detailed search strategy.", error_code="MISSING_SEARCH_STRATEGY")

        self.detailed_search_strategy = await self.collection_strategy_generator.generate_collection_search_strategy(
            self.requirements.get_refined_query(),
            self.overall_search_strategy,
            session_id,
        )

    def get_overall_search_strategy(self) -> Optional[List[Dict[str, float]]]:
        """
        Get overall search strategy.

        Returns:
            Optional[List[Dict[str, float]]]: Overall search strategy, or None if not generated yet
        """
        return self.overall_search_strategy

    async def calculate_resume_scores(self, top_n: int = 3):
        """
        Calculate resume scores.

        Args:
            top_n (int): Number of top matching resumes to return
        """
        if not self.overall_search_strategy or not self.detailed_search_strategy:
            logger.error("Search strategy not yet generated. Unable to calculate resume scores.")
            raise ValidationError("Search strategy not yet generated. Unable to calculate resume scores.", error_code="MISSING_SEARCH_STRATEGIES")

        self.ranked_resume_scores = await self.scorer.calculate_overall_resume_scores(
            self.requirements.get_refined_query(),
            self.overall_search_strategy,
            self.detailed_search_strategy,
            top_n,
        )

    async def generate_recommendation_reasons(self, session_id: Optional[str] = None):
        """
        Generate recommendation reasons.

        Args:
            session_id (Optional[str]): Session ID
        """
        if self.resume_details is None:
            self.resume_details = await self.output_generator.fetch_resume_details(
                self.ranked_resume_scores
            )

        self.recommendation_reasons = (
            await self.reason_generator.generate_recommendation_reasons(
                self.requirements.get_refined_query(),
                self.resume_details,
                session_id or self.session_id,
            )
        )

    async def prepare_final_recommendations(self):
        """Prepare final recommendation results."""
        if self.resume_details is None or self.recommendation_reasons is None:
            logger.error("Resume details or recommendation reasons not yet generated. Unable to prepare final recommendation results.")
            raise ValidationError("Resume details or recommendation reasons not yet generated. Unable to prepare final recommendation results.", error_code="MISSING_RECOMMENDATION_DATA")

        self.final_recommendations = await self.output_generator.prepare_final_output(
            self.resume_details, self.recommendation_reasons
        )

    def get_recommendations(self) -> Optional[List[Dict]]:
        """
        Get final recommendation results.

        Returns:
            Optional[List[Dict]]: List of recommendation results, or None if not generated yet
        """
        return (
            self.final_recommendations.to_dict("records")
            if self.final_recommendations is not None
            else None
        )

    def get_refined_query(self) -> Optional[str]:
        """
        Get refined query.

        Returns:
            Optional[str]: Refined query, or None if not generated yet
        """
        return self.requirements.get_refined_query()
