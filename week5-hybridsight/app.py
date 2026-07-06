import uuid
import gradio as gr
from agent import agent, DEFAULT_CONFIG_EXTRA
from ingest import index_pdf
from image_utils import image_to_data_uri

def handle_pdf_upload(file):
    if file is None:
        return "No file uploaded."
    n_chunks = index_pdf(file.name)
    return f"Indexed {n_chunks} chunks into ChromaDB."

def chat(message, image, history, session_id):
    if image is not None:
        data_uri = image_to_data_uri(image)
        message = f"{message}\n\n[Attached image: {data_uri}]"

    config = {
        "configurable": {"thread_id": session_id},
        **DEFAULT_CONFIG_EXTRA,
    }
    trace_log, final_answer = [], ""
    for event in agent.stream(
        {"messages": [{"role": "user", "content": message}]},
        config=config, stream_mode="values",
    ):
        last = event["messages"][-1]
        if getattr(last, "tool_calls", None):
            for tc in last.tool_calls:
                trace_log.append(f"→ {tc['name']}: {tc['args']}")
        elif last.type == "ai" and not hasattr(last, "tool_calls"):
            final_answer = last.content

    history = history + [[message, final_answer]]
    return history, session_id, "\n".join(trace_log) or "No tools were called."

with gr.Blocks(title="HybridSight") as demo:
    session_id = gr.State(value=lambda: str(uuid.uuid4()))
    gr.Markdown("# 👁️ HybridSight — RAG + Web + Vision Agent")

    with gr.Row():
        pdf_upload = gr.File(label="Upload a PDF", file_types=[".pdf"])
        image_upload = gr.Image(label="Upload an image", type="filepath")
    index_status = gr.Textbox(label="Indexing status", interactive=False)
    pdf_upload.change(handle_pdf_upload, inputs=pdf_upload, outputs=index_status)

    chatbot = gr.Chatbot(height=420, label="Conversation")
    msg_box = gr.Textbox(placeholder="Ask anything...", label="Your message")
    submit_btn = gr.Button("Send", variant="primary")

    with gr.Accordion("🔍 Agent Reasoning Trace", open=False):
        trace_box = gr.Textbox(label="Tools called during last response", lines=6, interactive=False)

    submit_btn.click(
        chat, inputs=[msg_box, image_upload, chatbot, session_id],
        outputs=[chatbot, session_id, trace_box],
    ).then(lambda: "", outputs=msg_box)

if __name__ == "__main__":
    demo.launch()
