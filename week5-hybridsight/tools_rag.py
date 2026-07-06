# pyrefly: ignore [missing-import]
from langchain_core.tools import tool
# pyrefly: ignore [missing-import]
from langchain_community.vectorstores import Chroma
# pyrefly: ignore [missing-import]
from langchain_community.embeddings import HuggingFaceEmbeddings
import os

# Initialize only if directory exists to avoid errors on startup before indexing
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
persist_dir = "./chroma_store"
collection_name = "lecture_notes"

if os.path.exists(persist_dir):
    vectorstore = Chroma(
        persist_directory=persist_dir,
        embedding_function=embedding_model,
        collection_name=collection_name,
    )
else:
    vectorstore = None

@tool
def search_documents(query: str) -> str:
    """Search the user's uploaded documents for information relevant to
    the query. Use this when the user asks about content from a PDF they
    uploaded, or references 'the document', 'my notes', or 'the file'.
    Do NOT use this for general knowledge or current events."""
    if vectorstore is None or vectorstore._collection.count() == 0:
        return "No documents uploaded yet."

    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    chunks = retriever.invoke(query)

    if not chunks:
        return "No relevant content found in the uploaded documents."

    return "\n\n".join([
        f"[p.{c.metadata.get('page','?')}] {c.page_content}"
        for c in chunks
    ])
