import time
import pytest
from langchain.schema import Document
from app.rag.retrieval import RetrieverFactory, RetrievalStrategy
import os
import shutil

# Synthetic Dataset
DATASET = [
    ("Doc1", "The quick brown fox jumps over the lazy dog.", "fox"),
    ("Doc2", "Artificial Intelligence is transforming the tech industry.", "ai"),
    ("Doc3", "Machine learning algorithms learn from data.", "ai"),
    ("Doc4", "The Eiffel Tower is located in Paris, France.", "geography"),
    ("Doc5", "Photosynthesis is how plants convert light into energy.", "biology"),
    ("Doc6", "Quantum computing leverages quantum mechanics to process information faster.", "tech"),
    ("Doc7", "In 1969, Neil Armstrong became the first man to walk on the moon.", "history"),
    ("Doc8", "Python is a high-level, interpreted programming language.", "tech"),
    ("Doc9", "The capital of Japan is Tokyo.", "geography"),
    ("Doc10", "Deep learning is a subset of machine learning based on artificial neural networks.", "ai")
]

def generate_benchmark_report(results):
    report = "# Retrieval Benchmark Report\n\n"
    report += "| Strategy | Latency (s) | Recall | Precision |\n"
    report += "|---|---|---|---|\n"
    
    for strategy, metrics in results.items():
        report += f"| {strategy.value} | {metrics['latency']:.4f} | {metrics['recall']:.2f} | {metrics['precision']:.2f} |\n"
        
    with open("docs/architecture/benchmark_report.md", "w") as f:
        f.write(report)

@pytest.mark.skip(reason="Requires a live Vector Store or mock. Running manually for benchmarks.")
def test_benchmark_all_strategies():
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings
    
    # Setup test DB
    persist_dir = "./test_chroma_db"
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
    
    docs = []
    for title, content, topic in DATASET:
        # parent_text simulation for ParentStrategy
        docs.append(Document(page_content=content, metadata={"session_id": "test_session", "topic": topic, "parent_id": topic, "parent_text": content + " (Full Context)"}))
        
    db = Chroma.from_documents(docs, embeddings, persist_directory=persist_dir)
    
    query = "Tell me about artificial intelligence and machine learning."
    target_topics = {"ai", "tech"} # expected relevant topics
    
    results = {}
    
    for strategy in RetrievalStrategy:
        try:
            retriever = RetrieverFactory.get_retriever(strategy, db, "test_session", k=3)
            
            t0 = time.time()
            retrieved_docs = retriever.invoke(query)
            latency = time.time() - t0
            
            # Evaluate
            relevant_retrieved = sum(1 for doc in retrieved_docs if doc.metadata.get("topic") in target_topics)
            total_retrieved = len(retrieved_docs) if retrieved_docs else 1
            total_relevant_in_db = 4 # (2 AI, 2 tech)
            
            precision = relevant_retrieved / total_retrieved
            recall = relevant_retrieved / total_relevant_in_db
            
            results[strategy] = {
                "latency": latency,
                "precision": precision,
                "recall": recall
            }
        except Exception as e:
            print(f"Strategy {strategy} failed: {e}")
            results[strategy] = {"latency": 0.0, "precision": 0.0, "recall": 0.0}
            
    generate_benchmark_report(results)
    
    # cleanup
    shutil.rmtree(persist_dir)
