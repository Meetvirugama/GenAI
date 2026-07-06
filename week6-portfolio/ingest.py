import os
# pyrefly: ignore [missing-import]
from langchain_community.document_loaders import PyPDFLoader
# pyrefly: ignore [missing-import]
from langchain.text_splitter import RecursiveCharacterTextSplitter
# pyrefly: ignore [missing-import]
from langchain_community.vectorstores import Chroma
# pyrefly: ignore [missing-import]
from langchain_community.embeddings import HuggingFaceEmbeddings

import gradio as gr

def index_pdf(filepath: str, progress=gr.Progress()) -> int:
    """Indexes a single PDF file and returns the number of chunks."""
    if not filepath:
        return 0

    progress(0.1, desc="Loading PDF...")
    loader = PyPDFLoader(filepath)
    pages = loader.load()

    progress(0.3, desc="Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=80)
    chunks = splitter.split_documents(pages)

    if not chunks:
        return 0

    progress(0.5, desc="Preparing metadata...")
    for chunk in chunks:
        filename = os.path.basename(chunk.metadata.get("source", ""))
        chunk.metadata["source"] = filename
        chunk.metadata["page"] = chunk.metadata.get("page", 0) + 1

    progress(0.7, desc="Embedding chunks...")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})

    progress(0.9, desc="Writing to ChromaDB...")
    Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory="./chroma_store",
        collection_name="lecture_notes"
    )

    progress(1.0, desc="Done!")
    return len(chunks)
