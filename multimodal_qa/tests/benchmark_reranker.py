import os
import shutil
import time

import pytest
from app.services.rag.retrieval import RetrievalStrategy, RetrieverFactory
from langchain.schema import Document

# Complex dataset where pure lexical/dense match might fail, 
# but cross-encoder might excel.
DATASET = [
    ("Doc1", "The company reported a massive loss in Q1 due to supply chain issues.", "finance_negative"),
    ("Doc2", "Our Q1 revenue grew by 20%, but profit margins were hurt by supply chain delays.", "finance_mixed"),
    ("Doc3", "The supply chain is operating at 100% efficiency, driving Q1 profit up.", "finance_positive"),
    ("Doc4", "Apples are a great source of fiber and vitamins.", "food"),
    ("Doc5", "The new iPhone features a revolutionary supply chain tracking app.", "tech")
]

def generate_benchmark_report(results):
    report = "# Reranking Benchmark Report\n\n"
    report += "| Pipeline | Latency (s) | Top-1 Accuracy | Relevant in Top-K |\n"
    report += "|---|---|---|---|\n"
    
    for pipe, metrics in results.items():
        report += f"| {pipe} | {metrics['latency']:.4f} | {metrics['top_1_accuracy']} | {metrics['relevant_in_top_k']} |\n"
        
    with open("docs/architecture/reranker_benchmark_report.md", "w") as f:
        f.write(report)

@pytest.mark.skip(reason="Requires a live Vector Store or mock. Running manually for benchmarks.")
def test_benchmark_reranker():
    from langchain_community.embeddings import HuggingFaceEmbeddings
    from langchain_community.vectorstores import Chroma
    
    persist_dir = "./test_chroma_db_rerank"
    if os.path.exists(persist_dir):
        shutil.rmtree(persist_dir)
        
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={"device": "cpu"})
    
    docs = []
    for title, content, topic in DATASET:
        docs.append(Document(page_content=content, metadata={"session_id": "test_session", "topic": topic}))
        
    db = Chroma.from_documents(docs, embeddings, persist_directory=persist_dir)
    
    # Query designed to be tricky. Needs to find the *positive* finance doc.
    query = "Was the supply chain helpful to Q1 profits?"
    target_topic = "finance_positive"
    
    results = {}
    
    for use_rerank, name in [(False, "Dense Without Reranker"), (True, "Dense WITH BGE Reranker")]:
        try:
            # We want K=2 for the final output
            retriever = RetrieverFactory.get_retriever(
                strategy=RetrievalStrategy.DENSE, 
                vector_store=db, 
                session_id="test_session", 
                k=2,
                use_reranker=use_rerank
            )
            
            t0 = time.time()
            retrieved_docs = retriever.invoke(query)
            latency = time.time() - t0
            
            # Evaluate
            if retrieved_docs:
                top_1_acc = 1 if retrieved_docs[0].metadata.get("topic") == target_topic else 0
                rel_in_k = sum(1 for d in retrieved_docs if d.metadata.get("topic") == target_topic)
            else:
                top_1_acc, rel_in_k = 0, 0
            
            results[name] = {
                "latency": latency,
                "top_1_accuracy": top_1_acc,
                "relevant_in_top_k": rel_in_k
            }
        except Exception as e:
            print(f"Pipeline {name} failed: {e}")
            results[name] = {"latency": 0.0, "top_1_accuracy": 0, "relevant_in_top_k": 0}
            
    generate_benchmark_report(results)
    shutil.rmtree(persist_dir)
