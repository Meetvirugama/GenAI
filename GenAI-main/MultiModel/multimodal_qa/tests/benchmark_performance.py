import time
import os
import psutil
import asyncio
from concurrent.futures import ThreadPoolExecutor
from dotenv import load_dotenv
load_dotenv()

def measure_resources():
    process = psutil.Process(os.getpid())
    cpu_percent = process.cpu_percent(interval=None)
    memory_info = process.memory_info()
    return cpu_percent, memory_info.rss / (1024 * 1024)  # MB

def benchmark():
    print("Initializing benchmark...")
    # Initialize psutil CPU measurement
    psutil.Process(os.getpid()).cpu_percent(interval=None)
    
    from app.rag.vector_store import VectorStore
    from langchain.schema import Document
    import random
    import string
    
    num_docs = 500
    print(f"Generating {num_docs} synthetic documents...")
    docs = []
    for i in range(num_docs):
        text = ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=800))
        docs.append(Document(page_content=text, metadata={"source": f"doc_{i}.txt", "doc_hash": str(i)}))

    store = VectorStore()
    session_id = "benchmark_session"
    
    print("\n--- Benchmarking Vector Batch Insert ---")
    start_cpu, start_mem = measure_resources()
    t0 = time.time()
    
    store.add_documents(docs, session_id)
    
    latency = time.time() - t0
    end_cpu, end_mem = measure_resources()
    
    print(f"Insertion Latency: {latency:.2f}s")
    print(f"CPU Usage: {end_cpu - start_cpu:.1f}%")
    print(f"Memory Increase: {end_mem - start_mem:.2f} MB")
    
    print("\n--- Benchmarking Retrieval ---")
    retriever = store.get_retriever(session_id, k=5)
    
    if retriever:
        start_cpu, start_mem = measure_resources()
        t0 = time.time()
        
        for _ in range(50):
            # Fire 50 queries
            retriever.invoke("random query text to retrieve documents")
            
        latency = time.time() - t0
        end_cpu, end_mem = measure_resources()
        
        print(f"50 Queries Latency: {latency:.2f}s")
        print(f"CPU Usage: {end_cpu - start_cpu:.1f}%")
        print(f"Memory Increase: {end_mem - start_mem:.2f} MB")
    
    print("\n--- Benchmarking Async Token Generation (Mock LLM) ---")
    try:
        # We mock the astream method to simulate an LLM returning tokens at 50 tokens/sec
        async def mock_astream():
            for i in range(150):
                yield "token"
                await asyncio.sleep(0.02)
        
        async def run_async_agent():
            start_cpu, start_mem = measure_resources()
            t0 = time.time()
            
            token_count = 0
            try:
                async for token in mock_astream():
                    token_count += 1
            except Exception as e:
                print(f"Error generating tokens: {e}")
                
            latency = time.time() - t0
            end_cpu, end_mem = measure_resources()
            
            print(f"Generation Latency: {latency:.2f}s")
            print(f"Tokens Generated: {token_count}")
            if latency > 0:
                print(f"Token Throughput: {token_count/latency:.2f} tokens/sec")
            print(f"CPU Usage: {end_cpu - start_cpu:.1f}%")
            print(f"Memory Increase: {end_mem - start_mem:.2f} MB")
            
            return token_count, latency

        asyncio.run(run_async_agent())
    except Exception as e:
        print(f"Could not benchmark agent: {e}")

    print("\nCleaning up...")
    store.clear_session(session_id)
    print("Benchmark complete.")

if __name__ == "__main__":
    benchmark()
