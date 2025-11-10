from typing import List, Dict, Optional
from pydantic import BaseModel
from backend.resume_management.recommendation.recommendation_state import (
    QueryRefinement,
)
from utils.ai.llm_client import LanguageModelChain, init_language_model
from utils.ai.langfuse_client import create_langfuse_config
from utils.core.logging import get_project_logger
import uuid
import os
import asyncio

logger = get_project_logger(__name__)

# Initialize language model
language_model = init_language_model(
    model_name=os.getenv("SMART_LLM_MODEL")
)


class RecommendationRequirements:
    """Process and refine user query requirements"""

    def __init__(self):
        self.query_history: List[str] = []
        self.refined_query: Optional[str] = None
        self.current_question: Optional[str] = None
        self.session_id: str = str(uuid.uuid4())

    system_message = """
    你是一个智能简历推荐系统的预处理助手。你的任务是评估并完善用户的查询，以生成精确的简历检索策略。请遵循以下指南：

    1. 分析用户的查询，关注以下关键方面（无需涵盖所有方面）：
       - 工作经历：对职位、工作职责、工作经验的要求
       - 项目经历: 对过往特定项目和工作的要求
       - 技能：对必要的专业技能、工具使用能力的要求
       - 教育背景：对学历、专业的要求
       - 个人特质：对个人特点或其他方面的要求

    2. 评估查询的完整性：
       - 如果查询已经包含足够的信息（至少涵盖2-3个关键方面），直接完善并总结查询。
       - 如果信息不足（只提到1-2个方面）或不明确，生成简洁的问题以获取必要信息。

    3. 当需要更多信息时：
       - 提出简洁、有针对性的问题，一次性列出所有需要澄清的点。
       - 将输出状态设置为 "need_more_info"。

    4. 当信息充足时：
       - 总结并完善查询，确保它是一个流畅、自然的句子或段落，类似于用户的原始输入方式。
       - 将输出状态设置为 "ready"。

    请记住，目标是在最少的交互中获得有效信息，生成自然、流畅的查询描述，而不是格式化的列表。
    """

    human_message_template = """
    用户查询历史：
    {query_history}

    用户最新回答：
    {latest_response}

    请评估当前信息，并按照指示生成适当的响应。如果需要更多信息，请简明扼要地提出所有必要的问题。如果信息充足，请生成一个自然、流畅的查询描述。
    """

    query_refiner = LanguageModelChain(
        QueryRefinement, system_message, human_message_template, language_model
    )()


    async def confirm_requirements(
        self, user_input: Optional[str] = None, session_id: Optional[str] = None
    ) -> str:
        """
        Confirm and refine user query requirements.

        Args:
            user_input (Optional[str]): User's new query input or answer
            session_id (Optional[str]): Session ID

        Returns:
            str: Status of next operation, either "ready" or "need_more_info"
        """
        if session_id is None:
            session_id = self.session_id

        if user_input:
            self.query_history.append(user_input)
            latest_response = user_input
        else:
            latest_response = self.query_history[-1] if self.query_history else ""

        query_history_for_model = self.query_history[:-1]

        config = create_langfuse_config(
            session_id=session_id,
            run_name="confirm_requirements",
            task_name="resume_recommendation"
        )
        
        refinement_result = await self.query_refiner.ainvoke(
            {
                "query_history": "\n".join(query_history_for_model),
                "latest_response": latest_response,
            },
            config=config,
        )

        refined_query = QueryRefinement(**refinement_result)

        if refined_query.status == "ready":
            self.refined_query = refined_query.content
            self.current_question = None
            logger.info("Requirement analysis completed, preparing to search for suitable resumes")
        else:
            self.current_question = refined_query.content
            logger.info("Further confirming your requirements")

        return refined_query.status

    def get_current_question(self) -> Optional[str]:
        """
        Get the current question that needs user response.

        Returns:
            Optional[str]: Current question, or None if there are none
        """
        return self.current_question

    def get_refined_query(self) -> Optional[str]:
        """
        Get refined query.

        Returns:
            Optional[str]: Refined query, or None if not yet generated
        """
        return self.refined_query
