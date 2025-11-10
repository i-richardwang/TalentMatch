#!/usr/bin/env python3
"""
Project initialization script

This script initializes the database and infrastructure for the TalentMatch simplified project.
Only keeps components required for the recommendation system.
"""

import os
import sys

# Add project root directory to path
project_root = os.path.dirname(os.path.dirname(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.database.connections import init_all_connections, cleanup_connections
from backend.resume_management.storage.mysql_base import ResumeTableManager


def main():
    """
    Main initialization process
    """
    print("🚀 开始初始化TalentMatch简化版项目...")
    print("📝 本版本只保留智能推荐功能")

    try:
        # 1. Initialize database connections
        print("📊 初始化数据库连接...")
        init_all_connections()
        print("✅ 数据库连接初始化完成")

        # 2. Initialize MySQL tables
        print("🗄️  初始化MySQL数据表...")
        ResumeTableManager.init_all_tables()
        print("✅ MySQL数据表初始化完成")

        # 3. Verify environment variables
        print("🔧 检查环境变量配置...")
        
        # Base required variables
        base_required_vars = [
            "OPENAI_API_KEY", "OPENAI_API_BASE", "LLM_MODEL",
            "MYSQL_HOST", "MYSQL_USER", "MYSQL_PASSWORD", "MYSQL_DATABASE",
            "EMBEDDING_API_KEY", "EMBEDDING_API_BASE"
        ]
        
        # Vector database configuration (choose one of two modes)
        # Mode 1: Self-hosted Milvus
        milvus_vars = ["VECTOR_DB_HOST", "VECTOR_DB_PORT"]
        # Mode 2: Zilliz Cloud
        zilliz_vars = ["VECTOR_DB_URI", "VECTOR_DB_TOKEN"]
        
        missing_vars = []
        for var in base_required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        # Check vector database configuration
        has_milvus = all(os.getenv(var) for var in milvus_vars)
        has_zilliz = all(os.getenv(var) for var in zilliz_vars)
        
        if not has_milvus and not has_zilliz:
            print(f"⚠️  警告：向量数据库配置不完整")
            print(f"   请选择以下配置之一：")
            print(f"   选项1 (自部署 Milvus): {', '.join(milvus_vars)}")
            print(f"   选项2 (Zilliz Cloud): {', '.join(zilliz_vars)}")
        elif has_zilliz:
            print("✅ 使用 Zilliz Cloud 向量数据库")
        else:
            print("✅ 使用自部署 Milvus 向量数据库")
        
        if missing_vars:
            print(f"⚠️  警告：以下环境变量未设置：")
            for var in missing_vars:
                print(f"   - {var}")
            print("   请检查.env文件配置")
        else:
            print("✅ 基础环境变量检查完成")
        
        print("\n🎉 项目初始化完成！")
        print("💡 提示：")
        print("   - 使用 'uv run streamlit run frontend/app.py' 启动应用")
        print("   - 确保Milvus和MySQL服务已启动")
        print("   - 检查.env文件中的API密钥配置")
        
    except Exception as e:
        print(f"❌ 初始化失败：{e}")
        return 1
    
    finally:
        cleanup_connections()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())