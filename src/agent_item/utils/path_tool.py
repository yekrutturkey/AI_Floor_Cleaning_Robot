"""
为整个工程提供统一的绝对路径
"""

import os


def get_project_root() -> str:
    """
    获取工程所在根目录
    :return: 字符串根目录
    """

    # 工程根目录 = 往上一级(往上一级(当前文件的绝对路径))
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return project_root


def get_abs_path(relative_path: str) -> str:
    """
    传入绝对路径,返回绝对路径
    :param relative_path: 相对路径
    :return: 绝对路径
    """
    project_root = get_project_root()
    return os.path.join(project_root, relative_path)
