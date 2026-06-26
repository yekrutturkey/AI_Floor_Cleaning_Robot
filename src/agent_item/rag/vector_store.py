from langchain_chroma import Chroma
from agent_item.utils.config_handler import chroma_config
from agent_item.models.factory import embed_model
from langchain_text_splitters import RecursiveCharacterTextSplitter
from agent_item.utils.path_tool import get_abs_path
from agent_item.utils.file_handler import (
    pdf_loader,
    txt_loader,
    listdir_with_allowed_type,
    get_file_md5_hex,
)
from agent_item.utils.logger_handler import logger
from langchain_core.documents import Document
import os


print("[0] vector_store.py 开始执行", flush=True)
print("[1] 准备导入模型", flush=True)
print("[2] 模型导入完成", flush=True)
print("[3] 所有模块导入完成", flush=True)


class VectorStoreService:
    def __init__(self):
        chroma_db_path = get_abs_path(chroma_config["persist_directory"])

        self.vector_store = Chroma(
            collection_name=chroma_config["collection_name"],
            embedding_function=embed_model,
            persist_directory=chroma_db_path,
        )

        self.spliter = RecursiveCharacterTextSplitter(
            chunk_size=chroma_config["chunk_size"],
            chunk_overlap=chroma_config["chunk_overlap"],
            separators=chroma_config["separators"],
            length_function=len,
        )

    def get_retriever(self):
        return self.vector_store.as_retriever(search_kwargs={"k": chroma_config["k"]})

    def load_document(self):
        def check_md5_hex(md5_for_check: str):
            if not os.path.exists(get_abs_path(chroma_config["md5_hex_store"])):
                open(get_abs_path(chroma_config["md5_hex_store"]), "w", encoding="utf-8").close()
                return False

            with open(get_abs_path(chroma_config["md5_hex_store"]), "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line == md5_for_check:
                        return True
                return False

        def save_md5_hex(md5_for_check: str):
            with open(get_abs_path(chroma_config["md5_hex_store"]), "a", encoding="utf-8") as f:
                f.write(md5_for_check + "\n")

        def get_file_documents(read_path: str):
            if read_path.endswith(".pdf"):
                return pdf_loader(read_path)
            elif read_path.endswith(".txt"):
                return txt_loader(read_path)
            return []

        allowed_files_path: list[str] = listdir_with_allowed_type(
            get_abs_path(chroma_config["data_path"]),
            tuple(chroma_config["allow_knowledge_file_type"]),
        )

        for path in allowed_files_path:
            md5_hex = get_file_md5_hex(path)
            if check_md5_hex(md5_hex):
                logger.info(f"[加载知识库] {path}内容已经存在知识库中。跳过")
                continue

            try:
                documents: list[Document] = get_file_documents(path)
                if not documents:
                    logger.warning(f"[加载知识库] {path}内容没有有效文本内容。跳过")
                    continue
                split_document: list[Document] = self.spliter.split_documents(documents)
                if not split_document:
                    logger.warning(f"[加载知识库] {path}分片后，内容没有有效文本内容。跳过")
                    continue
                self.vector_store.add_documents(split_document)
                save_md5_hex(md5_hex)
                logger.info(f"[加载知识库] {path} 内容加载完成")
            except Exception as e:
                logger.error(
                    f"[加载知识库] {path} 加载失败，请检查文件格式是否正确。错误信息：{str(e)}",
                    exc_info=True,
                )


# if __name__ == "__main__":
#     vc = VectorStoreService()

#     vc.load_document()

#     retriever = vc.get_retriever()

#     res = retriever.invoke("迷路")
#     for r in res:
#         print(r.page_content)
#         print("-"*20)

#     print("执行完毕")


if __name__ == "__main__":
    print("[4] 已进入 main", flush=True)

    vc = VectorStoreService()
    print("[5] VectorStoreService 初始化完成", flush=True)

    vc.load_document()
    print("[6] load_document 执行完成", flush=True)

    retriever = vc.get_retriever()
    print("[7] retriever 创建完成", flush=True)

    print("[8] 准备执行检索", flush=True)
    res = retriever.invoke("迷路")
    print(f"[9] 检索完成，结果数量：{len(res)}", flush=True)

    for index, document in enumerate(res, start=1):
        print(f"第 {index} 条结果：")
        print(document.page_content)
        print("-" * 20)

    print("[10] 执行完毕", flush=True)
