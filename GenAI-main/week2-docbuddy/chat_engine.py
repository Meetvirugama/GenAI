import os
from groq import Groq
from document_processor import get_vectorstore

def respond(message, history, top_k):
    """Chat function — yields (history, updated_context_for_accordion)."""
    vectorstore = get_vectorstore()
    
    if not vectorstore:
        history.append((message, "Please upload and index a document first."))
        yield history, ""
        return
        
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    retriever = vectorstore.as_retriever(search_kwargs={"k": int(top_k)})
    raw_chunks = retriever.invoke(message)
    
    # Format context for display in the Accordion
    context_display = "\n\n".join([
        f"**[{doc.metadata.get('source','?')} · Page {doc.metadata.get('page','?')}]**\n{doc.page_content}"
        for doc in raw_chunks
    ])
    
    context_block = "\n\n---\n\n".join([
        f"[Source {i}: {doc.metadata.get('source','?')}, page {doc.metadata.get('page','?')}]\n{doc.page_content}"
        for i, doc in enumerate(raw_chunks, 1)
    ])
    
    system_prompt = """You are a precise document assistant.
Answer the user's question using ONLY the context provided below.
Rules:
- If the answer is not in the context, say exactly: "I don't have that information in the uploaded documents."
- Never use your general training knowledge to supplement the context.
- After your answer, add a 'Sources:' line citing the [Source N] labels you used.
- Keep answers concise and factual.
- Retain markdown formatting, lists, and tables if present in the context."""

    user_message = f"""Context:
{context_block}

Question: {message}"""

    messages = [{"role": "system", "content": system_prompt}]
    
    # Optional Challenge: Memory
    for user_msg, ai_msg in history[-2:]: # Last 2 turns
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": ai_msg})
        
    messages.append({"role": "user", "content": user_message})

    # Optional Challenge: Streaming
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        temperature=0,
        stream=True
    )
    
    history.append((message, ""))
    for chunk in response:
        delta = chunk.choices[0].delta.content
        if delta:
            history[-1] = (message, history[-1][1] + delta)
            yield history, context_display
