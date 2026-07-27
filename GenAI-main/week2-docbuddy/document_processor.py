import os
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

PERSIST_DIR = "./chroma_store"
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})

def get_vectorstore():
    """Returns the loaded vector store if it exists, otherwise None."""
    if os.path.exists(PERSIST_DIR):
        return Chroma(persist_directory=PERSIST_DIR, embedding_function=embedding_model, collection_name="docbuddy")
    return None

def index_documents(pdf_paths):
    """Indexes the provided PDF paths into the Chroma vector store."""
    if not pdf_paths:
        return "No files uploaded."
    
    loader_docs = []
    for path in pdf_paths:
        loader = PyPDFLoader(path)
        pages = loader.load()
        loader_docs.extend(pages)
        
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=150)
    chunks = splitter.split_documents(loader_docs)
    
    if not chunks:
        return "Error: No text could be extracted from the uploaded PDF(s)."
    
    for chunk in chunks:
        # Assign required metadata
        filename = os.path.basename(chunk.metadata.get("source", ""))
        chunk.metadata["source"] = filename
        chunk.metadata["page"] = chunk.metadata.get("page", 0) + 1
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=PERSIST_DIR,
        collection_name="docbuddy"
    )
    
    return f"{len(pdf_paths)} documents indexed — {len(chunks)} total chunks"
