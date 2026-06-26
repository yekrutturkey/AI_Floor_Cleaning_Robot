import os
import hashlib
from agent_item.utils.logger_handler import logger
from langchain_core.documents import Document
from langchain_community.document_loaders import PyPDFLoader, TextLoader


# 获取文件的md5的十六进制字符串
def get_file_md5_hex(filepath: str):

    if not os.path.exists(filepath):
        logger.error(f"[md5计算] 文件{filepath}不存在")
        return

    if not os.path.isfile(filepath):
        logger.error(f"[md5计算] 路径{filepath} 不是一个文件")
        return

    md5_obj = hashlib.md5()

    # 避免文件比较大，不会一次性计算，而是要分片（以下是通用写法）
    chunk_size = 4096  # 4KB分片，避免文件过大，爆内存
    try:
        with open(filepath, "rb") as f:  # 必须读取二进制
            while chunk := f.read(chunk_size):
                md5_obj.update(chunk)
            """
            旧写法
            chunk = f.read(chunk_size)
                while chunk:
                md5_obj.update(chunk)
                chunk = f.read(chunk_size)
            """
            md5_hex = md5_obj.hexdigest()
            return md5_hex
    except Exception as e:
        logger.error(f"[md5计算] 文件{filepath}计算md5失败：{str(e)}")
        return None


# 返回文件夹内的文件列表（允许的文件后缀）
def listdir_with_allowed_type(path: str, allowed_types: tuple[str]):
    files = []

    if not os.path.isdir(path):
        logger.error(f"[文件列表获取] 路径{path} 不是一个文件夹")
        return tuple()

    for f in os.listdir(path):
        if f.endswith(allowed_types):
            files.append(os.path.join(path, f))

    return tuple(files)


def pdf_loader(filepath: str, password: str = None) -> list[Document]:
    return PyPDFLoader(filepath, password).load()


def txt_loader(filelpath: str) -> list[Document]:
    return TextLoader(filelpath, encoding="utf-8").load()
