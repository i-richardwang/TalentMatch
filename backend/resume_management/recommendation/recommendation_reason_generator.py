from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import pandas as pd
import os
from utils.core.logging import get_project_logger
from utils.ai.llm_client import LanguageModelChain, init_language_model
from utils.ai.langfuse_client import create_langfuse_config
import uuid
import asyncio

logger = get_project_logger(__name__)


class RecommendationReason(BaseModel):
    """Recommendation reason model"""

    reason: str = Field(
        ..., description="A concise and compelling recommendation reason explaining why this resume suits the user's needs"
    )


class RecommendationReasonGenerator:
    """Recommendation reason generator, responsible for generating detailed reasons for each recommended resume"""

    def __init__(self):
        self.language_model = init_language_model(
            model_name=os.getenv("SMART_LLM_MODEL"),
        )
        self.system_message = """
        你是一个企业内部使用的智能简历推荐系统。你的任务是生成客观、简洁的推荐理由，解释为什么某份简历符合用户的查询需求。

        请遵循以下指南：
        1. 直接回应用户的具体要求，不要添加不必要的修饰。
        2. 重点关注简历中与用户需求最相关的经验和技能。
        3. 保持简洁，总字数控制在100-150字左右。
        4. 使用客观、中立的语言，避免过度赞美或主观评价。
        5. 不要使用候选人的姓名，也不要使用"他"或"她"等代词，直接陈述相关经验和技能。
        6. 简历评分仅用于比较各方面的相对强度，数值本身不具有意义。
        7. 重点说明简历中的具体经验和技能如何匹配用户需求，避免空泛的表述。
        8. 使用中文撰写理由。
        """

        self.human_message_template = """
        用户查询：
        {refined_query}

        简历评分：
        {resume_score}

        简历概述：
        {resume_overview}

        基于以上信息，请生成一个简洁、客观的推荐理由，解释为何这份简历适合用户的查询需求。回应应该是一段连贯的文字，包含在RecommendationReason结构的reason字段中。
        """

        self.recommendation_reason_chain = LanguageModelChain(
            RecommendationReason,
            self.system_message,
            self.human_message_template,
            self.language_model,
        )()


    async def generate_single_recommendation_reason(
        self,
        refined_query: str,
        resume: pd.Series,
        session_id: str,
        semaphore: asyncio.Semaphore,
    ) -> Dict[str, str]:
        """Generate recommendation reason for a single resume"""
        async with semaphore:
            resume_score = {
                "resume_id": resume["resume_id"],
                "total_score": resume["total_score"],
            }
            for dimension in [
                "work_experiences",
                "skills",
                "educations",
                "personal_infos",
            ]:
                if dimension in resume:
                    resume_score[dimension] = resume[dimension]

            resume_overview = {
                "characteristics": resume["characteristics"],
                "experience": resume["experience"],
                "skills_overview": resume["skills_overview"],
            }

            config = create_langfuse_config(
                session_id=session_id,
                run_name="generate_recommendation_reason",
                task_name="resume_recommendation"
            )
            reason_result = await self.recommendation_reason_chain.ainvoke(
                {
                    "refined_query": refined_query,
                    "resume_score": resume_score,
                    "resume_overview": resume_overview,
                },
                config=config,
            )

            return {"resume_id": resume["resume_id"], "reason": reason_result["reason"]}

    async def generate_recommendation_reasons(
        self,
        refined_query: str,
        resume_details: pd.DataFrame,
        session_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Generate detailed recommendation reasons for each recommended resume.

        Args:
            refined_query (str): Refined user query
            resume_details (pd.DataFrame): DataFrame containing resume details
            session_id (Optional[str]): Session ID for logging and tracking

        Returns:
            pd.DataFrame: DataFrame containing generated recommendation reasons

        Raises:
            ValueError: If resume details are empty or refined query is empty
        """
        if not refined_query:
            raise ValueError("Refined query cannot be empty. Unable to generate recommendation reasons.")

        if resume_details.empty:
            raise ValueError("Resume details cannot be empty. Unable to generate recommendation reasons.")

        session_id = session_id or str(uuid.uuid4())
        semaphore = asyncio.Semaphore(3)  # Limit concurrency to 3

        tasks = [
            self.generate_single_recommendation_reason(
                refined_query, resume, session_id, semaphore
            )
            for _, resume in resume_details.iterrows()
        ]

        reasons = await asyncio.gather(*tasks)
        reasons_df = pd.DataFrame(reasons)

        logger.info("Generated detailed recommendation reasons for each recommended resume")
        return reasons_df
