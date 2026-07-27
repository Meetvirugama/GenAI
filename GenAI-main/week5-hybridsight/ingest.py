import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

def index_pdf(filepath: str) -> int:
    """Indexes a single PDF file and returns the number of chunks."""
    if not filepath:
        return 0

    loader = PyPDFLoader(filepath)
    pages = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=80)
    chunks = splitter.split_documents(pages)

    if not chunks:
        return 0

    for chunk in chunks:
        filename = os.path.basename(chunk.metadata.get("source", ""))
        chunk.metadata["source"] = filename
        chunk.metadata["page"] = chunk.metadata.get("page", 0) + 1

    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})

    Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory="./chroma_store",
        collection_name="lecture_notes"
    )

    return len(chunks)
