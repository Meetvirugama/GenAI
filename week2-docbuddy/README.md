# Week 2: DocBuddy Pro — Retrieval-Augmented Generation (RAG)

Welcome to the **Week 2** project of the GenAI Track. This week shifts our focus from pure prompt engineering to **Data Contextualization**. 

Language models are frozen in time and have no access to your personal files. **Retrieval-Augmented Generation (RAG)** solves this by retrieving relevant text from your documents and injecting it into the prompt *before* the model generates an answer. This grounds the model in your specific truth, preventing hallucinations and enabling precise source citations.

---

## 🧠 Core Concepts & Theory (with Real-World Examples)

### 1. The RAG Pipeline
RAG fundamentally consists of two phases:
- **Indexing (Data Ingestion)**: Reading a document, breaking it into smaller pieces (chunks), converting those chunks into mathematical vectors (embeddings), and storing them in a Vector Database.
- **Retrieval (Querying)**: Taking a user's question, converting it into a vector, finding the most mathematically similar chunks in the database, and sending those chunks to the LLM as context.
> **🏢 Modern Example:** When you use features like **Notion AI** or enterprise tools like **Glean**, they are using RAG under the hood. They index all of your company's Confluence pages, Slack messages, and Google Docs so that when an employee asks "What is our WFH policy?", the AI retrieves the exact HR document and summarizes it, rather than making up a generic policy.

### 2. Document Loading & Text Splitting
You cannot feed a 500-page PDF directly into an LLM because it exceeds the model's Context Window (memory limit).
- **Loaders**: Tools like `PyPDFLoader` extract raw text from files.
- **Splitters**: Tools like `RecursiveCharacterTextSplitter` break the text into manageable chunks (e.g., 800 characters). We use an **overlap** (e.g., 150 characters) between chunks so that sentences aren't cut off abruptly, preserving the semantic meaning.

### 3. Embeddings & ChromaDB
- **Embeddings**: An embedding model (like HuggingFace's `all-MiniLM-L6-v2`) converts a text chunk into a high-dimensional array of numbers. Text with similar meanings will have vectors that are closer together in space.
- **Vector Database (ChromaDB)**: A database optimized for storing and querying these mathematical vectors. When a user asks a question, ChromaDB calculates the "distance" between the question's vector and the document vectors to find the most relevant chunks.
> **🏢 Modern Example:** Massive law firms use Vector Databases (like Pinecone or ChromaDB) to store millions of past case files. When a lawyer searches for "cases involving negligence in software deployment," the vector DB understands the *semantic meaning* of the query, finding relevant cases even if the exact keyword "software deployment negligence" was never written in the original 1990s court documents.

### 4. Anti-Hallucination Prompting
RAG relies on strict instructions. The system prompt must explicitly state: *"Answer the user's question ONLY using the provided context. If the context does not contain the answer, say 'I don't know'."* This is critical for building trustworthy enterprise AI.
> **🏢 Modern Example:** In healthcare or fintech (like Morgan Stanley's internal OpenAI assistant), anti-hallucination prompting is heavily enforced. If a wealth manager asks about a specific stock and it's not in the retrieved financial reports, the bot is strictly programmed to refuse to answer rather than risk giving hallucinated financial advice.

---

## 🛠️ Key Code & Functions

### Chunking the PDF
```python
from langchain.text_splitter import RecursiveCharacterTextSplitter

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800, 
    chunk_overlap=150
)
chunks = splitter.split_documents(loader_docs)
```

### Storing Vectors in ChromaDB
```python
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

vectorstore = Chroma.from_documents(
    documents=chunks,
    embedding=embedding_model,
    persist_directory="./chroma_store",
    collection_name="docbuddy"
)
```

### Retrieving Context
```python
# Convert the vectorstore into a retriever that fetches the top 4 chunks (k=4)
retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
retrieved_docs = retriever.invoke(user_question)
```

---

## 🚀 Setup & Execution

### Prerequisites
- Python 3.10+
- Groq API Key (from [console.groq.com](https://console.groq.com/))

### Installation
1. Navigate to the directory:
   ```bash
   cd week2-docbuddy
   ```
2. Activate your virtual environment:
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment variables:
   ```bash
   cp .env.example .env
   # Open .env and add your GROQ_API_KEY
   ```

### Running the App
```bash
python app.py
```
Open `http://127.0.0.1:7860` in your browser. Upload one or more PDFs, wait for the indexing to complete, and then ask questions. Verify that the model cites the exact page number and source file!

---

## 🎯 Learning Outcomes
By completing this week, you should understand:
1. How to process and chunk raw documents.
2. What vector embeddings are and how to store them locally using ChromaDB.
3. How to retrieve context based on semantic similarity.
4. How to engineer a prompt that forces the LLM to cite its sources and prevents hallucination.
