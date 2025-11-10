# TalentMatch

**🤖 智能人才推荐系统**

基于AI技术的精简版人才推荐平台，专注于候选人智能匹配和推荐功能，采用向量相似度搜索和大语言模型技术。

> 💡 **注意**：本项目采用 vibe coding 方式开发，注重快速实验和学习体验，代码质量未达生产级别。欢迎探索和学习！

## ✨ 功能特性

- **AI 候选人匹配**: 基于向量相似度算法，实现精准的候选人推荐
- **智能需求分析**: 自然语言处理招聘需求，自动生成搜索策略
- **多维度评分**: 从技能、经验、教育背景等多个维度综合评估候选人
- **数据导入工具**: 便捷的简历数据集导入功能

## 🚦 快速开始

### 环境要求

- Python 3.12 或更高版本
- uv 包管理器
- MySQL 数据库
- Milvus 向量数据库

### 安装部署

1. **克隆代码仓库**
   ```bash
   git clone https://github.com/i-richardwang/TalentMatch.git
   cd TalentMatch
   ```

2. **安装项目依赖**
   ```bash
   uv sync
   ```

3. **环境配置**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，填入 API 密钥和数据库连接信息
   ```

4. **数据库初始化**
   ```bash
   uv run python scripts/init_project.py
   ```

5. **导入示例数据（可选）**
   ```bash
   uv run python scripts/import_resume_data.py
   ```

6. **启动应用服务**
   ```bash
   uv run streamlit run frontend/app.py
   ```

系统将在 `http://localhost:8501` 启动运行。

## 🏗️ 项目结构

```
TalentMatch/
├── frontend/           # 前端界面（Streamlit）
│   └── page/          # 推荐页面
├── backend/           # 后端核心业务逻辑
│   └── resume_management/
│       ├── recommendation/ # AI推荐系统模块
│       └── storage/       # 数据存储模块
├── utils/             # 通用工具模块
│   ├── ai/           # LLM和嵌入客户端
│   ├── database/     # 数据库连接
│   └── data/         # 数据模型
├── scripts/          # 数据导入和初始化脚本
└── data/             # 配置文件和数据集
```

## ⚙️ 配置说明

主要配置项（需在 `.env` 文件中设置）：

- **LLM_PROVIDER**: AI 服务提供商（支持 DEEPSEEK/SILICONCLOUD）
- **LLM_MODEL**: 大语言模型配置
- **MYSQL_***: MySQL 数据库连接参数
- **VECTOR_DB_***: Milvus 向量数据库配置参数
- **EMBEDDING_***: 文本嵌入服务相关配置

## 🔧 技术栈

- **前端框架**: Streamlit
- **后端技术**: Python 3.12, Pydantic, AsyncIO
- **AI/ML**: LangChain, 大语言模型, 向量嵌入技术
- **数据库**: MySQL（结构化数据）, Milvus（向量数据库）

## 📝 使用说明

1. **数据导入**: 使用提供的脚本导入现有简历数据集
2. **智能查询**: 用自然语言输入招聘需求
3. **AI分析**: 系统分析需求并生成搜索策略
4. **候选人匹配**: 获得排序的候选人推荐及详细理由
5. **多维度评分**: 查看不同标准下的综合评估结果

## 📄 开源许可

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🤝 参与贡献

欢迎提交 Issue 和 Pull Request，共同完善项目！

---

*本项目为精简版演示系统，专注展示 AI 技术在人才推荐领域的应用。*