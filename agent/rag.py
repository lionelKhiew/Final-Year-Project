import os
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

# 初始化模型
embedding_model = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def build_vector_store(file_paths):
    """
    读取 PDF/TXT 文件并构建 FAISS 向量库
    """
    if not file_paths:
        return None

    all_docs = []

    for path in file_paths:
        try:
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
                all_docs.extend(loader.load())
            elif path.endswith(".txt"):
                # --- FIX: 加上 encoding='utf-8' ---
                loader = TextLoader(path, encoding="utf-8")
                all_docs.extend(loader.load())
        except Exception as e:
            # 打印错误但不让程序崩溃
            print(f"⚠️ Error loading {path}: {e}")
            continue  # 跳过这个出错的文件，继续处理下一个

    if not all_docs:
        return None

    # 切分文本
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    splits = text_splitter.split_documents(all_docs)

    # 构建向量库
    vector_store = FAISS.from_documents(splits, embedding_model)
    return vector_store
