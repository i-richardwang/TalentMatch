import streamlit as st
import sys
import os
import pandas as pd
import uuid
import asyncio
import tempfile
from pathlib import Path

# Add project root directory to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)


from langchain_core.globals import set_llm_cache
from langchain_community.cache import SQLiteCache

# Setup LLM cache with fallback to temp directory for cloud deployment
def setup_llm_cache():
    """
    Setup LLM cache with support for both local and cloud deployment.
    - Local: uses data/llm_cache/langchain.db
    - Cloud (Streamlit): uses system temp directory
    """
    # Try local cache directory first
    local_cache_dir = Path(project_root) / "data" / "llm_cache"
    local_cache_path = local_cache_dir / "langchain.db"

    try:
        # Ensure directory exists and is writable
        local_cache_dir.mkdir(parents=True, exist_ok=True)
        # Test write permission by creating a test file
        test_file = local_cache_dir / ".write_test"
        test_file.touch()
        test_file.unlink()

        # If successful, use local cache
        cache_path = local_cache_path
    except (OSError, PermissionError):
        # Fallback to system temp directory (for Streamlit Cloud)
        temp_cache_dir = Path(tempfile.gettempdir()) / "talentmatch_cache"
        temp_cache_dir.mkdir(exist_ok=True)
        cache_path = temp_cache_dir / "langchain.db"

    set_llm_cache(SQLiteCache(database_path=str(cache_path)))

setup_llm_cache()

from backend.resume_management.recommendation.resume_recommender import (
    ResumeRecommender,
)
from frontend.ui_components import apply_common_styles, display_project_info

# Global variables
chat_container = None


def display_hr_insights():
    """
    Display the value and application scenarios of talent recommendation.
    """
    with st.expander("💡 About", expanded=True):
        st.markdown("""
        通过 AI 语义理解能力，快速匹配最合适的候选人。从技能、工作经验、教育背景等多个维度智能分析，
        自动生成推荐理由，大幅提升招聘效率。

        **适用场景**：简历初筛、候选人搜索

        **💡 使用提示**：直接用自然语言描述招聘需求即可，例如：
        - "需要一位有 5 年以上经验的 Python 后端工程师"
        - "找一个数据分析师，熟悉 SQL 和数据可视化"
        - "推荐几位有机器学习项目经验的算法工程师"
        """)


def display_chat_history():
    """Display chat history"""
    with chat_container.container():
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                if isinstance(msg["content"], str):
                    st.write(msg["content"])
                elif isinstance(msg["content"], dict):
                    if msg["content"]["type"] == "search_strategy":
                        st.write("根据您的需求，我们生成了以下检索策略：")
                        st.table(msg["content"]["data"])
                    elif msg["content"]["type"] == "recommendations":
                        st.write("以下是根据您的需求推荐的简历：")
                        display_recommendations(msg["content"]["data"])


def display_recommendations(recommendations):
    """Display recommended resumes"""
    for idx, rec in enumerate(recommendations, 1):
        with st.expander(
            f"推荐 {idx}: 简历ID {rec['简历ID']} (总分: {rec['总分']:.2f})"
        ):
            col1, col2 = st.columns([2, 5])

            with col1:
                st.markdown("#### 推荐理由")
                st.info(rec["推荐理由"])

            with col2:
                st.markdown("#### 个人概况")
                st.write(rec["个人特征"])

                st.markdown("#### 工作经验")
                st.write(rec["工作经验"])

                st.markdown("#### 技能概览")
                st.write(rec["技能概览"])


async def process_user_input(prompt: str):
    """Process user input"""
    st.session_state.messages.append({"role": "user", "content": prompt})
    display_chat_history()

    if st.session_state.current_stage == "initial_query":
        with st.spinner("正在分析您的需求..."):
            status = await st.session_state.recommender.process_query(
                prompt, st.session_state.session_id
            )
        st.session_state.current_stage = (
            "refining_query"
            if status == "need_more_info"
            else "generating_recommendations"
        )
    elif st.session_state.current_stage == "refining_query":
        with st.spinner("正在处理您的回答..."):
            status = await st.session_state.recommender.process_answer(
                prompt, st.session_state.session_id
            )
        if status == "ready":
            st.session_state.current_stage = "generating_recommendations"

    next_question = st.session_state.recommender.get_next_question()
    if next_question:
        st.session_state.messages.append(
            {"role": "assistant", "content": next_question}
        )
        display_chat_history()
    elif st.session_state.current_stage == "generating_recommendations":
        refined_query = st.session_state.recommender.get_refined_query()
        if refined_query:
            st.session_state.refined_query = refined_query
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": f"根据您的需求，我们总结出以下招聘描述：\n\n{refined_query}",
                }
            )
            display_chat_history()

        st.session_state.processing = True
        st.session_state.strategy_displayed = False


def main():
    """Main function to run the intelligent resume recommendation system"""
    # Initialize session state
    if "recommender" not in st.session_state:
        st.session_state.recommender = ResumeRecommender()
        st.session_state.messages = [
            {
                "role": "assistant",
                "content": "您好，我是智能简历推荐助手。请告诉我您的招聘需求。",
            }
        ]
        st.session_state.current_stage = "initial_query"
        st.session_state.search_strategy = None
        st.session_state.recommendations = None
        st.session_state.processing = False
        st.session_state.strategy_displayed = False
        st.session_state.refined_query = None
        st.session_state.top_n = 3  # Default recommendation count
        st.session_state.session_id = str(uuid.uuid4())

    # Apply custom styles
    apply_common_styles()

    # Main interface
    st.title("👥 智能人才推荐")
    st.markdown("---")
    
    # Display project info
    display_project_info()

    # Display value and application scenarios
    display_hr_insights()

    st.markdown("## 人才推荐")

    # Add advanced settings
    with st.expander("高级设置", expanded=False):
        st.session_state.top_n = st.number_input(
            "推荐简历数量", min_value=1, max_value=10, value=st.session_state.top_n
        )

    # Create a container to display chat history
    global chat_container
    chat_container = st.empty()

    # Initial display of chat history
    display_chat_history()

    # Handle user input
    if prompt := st.chat_input("输入您的需求或回答"):
        asyncio.run(process_user_input(prompt))

    # Handle recommendation generation process
    if st.session_state.processing:

        async def generate_recommendations():
            with st.spinner("正在生成整体简历搜索策略..."):
                await st.session_state.recommender.generate_overall_search_strategy(
                    st.session_state.session_id
                )

            # Display overall search strategy
            collection_relevances = (
                st.session_state.recommender.get_overall_search_strategy()
            )
            if collection_relevances and not st.session_state.strategy_displayed:
                dimension_descriptions = {
                    "work_experiences": "工作经历",
                    "skills": "专业技能",
                    "educations": "教育背景",
                    "project_experiences": "项目经验",
                    "personal_infos": "个人概况",
                }
                table_data = [
                    {
                        "维度": dimension_descriptions.get(
                            relevance["collection_name"], relevance["collection_name"]
                        ),
                        "重要程度": f"{relevance['relevance_score'] * 100:.0f}%",
                    }
                    for relevance in collection_relevances
                ]
                st.session_state.search_strategy = pd.DataFrame(table_data)

                strategy_message = {
                    "type": "search_strategy",
                    "data": st.session_state.search_strategy,
                }
                st.session_state.messages.append(
                    {"role": "assistant", "content": strategy_message}
                )
                display_chat_history()
                st.session_state.strategy_displayed = True

            with st.spinner("正在生成详细的检索策略..."):
                await st.session_state.recommender.generate_detailed_search_strategy(
                    st.session_state.session_id
                )

            with st.spinner("正在计算简历得分..."):
                await st.session_state.recommender.calculate_resume_scores(
                    st.session_state.top_n
                )

            with st.spinner("正在获取简历详细信息..."):
                st.session_state.recommender.resume_details = await st.session_state.recommender.output_generator.fetch_resume_details(
                    st.session_state.recommender.ranked_resume_scores
                )

            with st.spinner("正在生成推荐理由..."):
                await st.session_state.recommender.generate_recommendation_reasons(
                    st.session_state.session_id
                )

            with st.spinner("正在准备最终推荐结果..."):
                await st.session_state.recommender.prepare_final_recommendations()

            # Update recommendation results
            recommendations = st.session_state.recommender.get_recommendations()
            if recommendations:
                st.session_state.recommendations = recommendations

                recommendation_message = {
                    "type": "recommendations",
                    "data": recommendations,
                }

                st.session_state.messages.append(
                    {"role": "assistant", "content": recommendation_message}
                )
                display_chat_history()

                st.info(
                    f"以上是为您推荐的 {len(recommendations)} 份简历，您可以展开查看详细信息。如需进行新的查询，请在下方输入框中输入新的需求。"
                )
            else:
                st.warning(
                    "抱歉，我们没有找到符合您要求的简历。您可以尝试调整一下需求再试试。"
                )

            st.session_state.current_stage = "initial_query"
            st.session_state.processing = False
            st.session_state.strategy_displayed = False

        asyncio.run(generate_recommendations())


if __name__ == "__main__":
    main()
