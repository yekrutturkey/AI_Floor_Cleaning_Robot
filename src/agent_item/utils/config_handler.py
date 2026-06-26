"""
yaml
k:v
"""

import yaml
from agent_item.utils.path_tool import get_abs_path


# 加载RAG配置文件
def load_rag_config(config_path: str = get_abs_path("config/rag.yml"), encoding="utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


# 加载向量数据库配置文件
def load_chroma_config(config_path: str = get_abs_path("config/chroma.yml"), encoding="utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


# 加载Prompts配置文件
def load_Prompts_config(config_path: str = get_abs_path("config/prompts.yml"), encoding="utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


def load_agent_config(config_path: str = get_abs_path("config/agent.yml"), encoding="utf-8"):
    with open(config_path, "r", encoding=encoding) as f:
        return yaml.load(f, Loader=yaml.FullLoader)


rag_config = load_rag_config()
chroma_config = load_chroma_config()
prompts_config = load_Prompts_config()
agent_config = load_agent_config()
