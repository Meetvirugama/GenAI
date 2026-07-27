import os, sys
import uuid
import gradio as gr
from agent import run_agent_with_trace
from ingest import index_pdf
from image_utils import image_to_data_uri
from safe_call import safe_call

# ── Guard at startup ──
if not os.getenv("GROQ_API_KEY"):
    print("ERROR: GROQ_API_KEY is not set. Add it to .env or HF Spaces Secrets.")
    sys.exit(1)

@safe_call
def handle_pdf_upload(file):
    if file is None:
        return "No file uploaded."
    n_chunks = index_pdf(file.name)
    return f"✅ Indexed {n_chunks} chunks into ChromaDB."

@safe_call
def handle_chat(message, history, session_id):
    if not message.strip():
        return history, session_id, ""
    
    answer, trace = run_agent_with_trace(message, session_id)
    return history + [[message, answer]], session_id, trace

@safe_call
def handle_image(filepath, session_id):
    if filepath is None:
        return "Please upload an image first.", ""
    
    data_uri = image_to_data_uri(filepath)
    # The agent routes image uploads automatically when the URI is in the prompt
    message = f"Describe this image: [Attached image: {data_uri}]"
    
    answer, trace = run_agent_with_trace("", session_id, message_with_image=message)
    return answer, trace


with gr.Blocks(
    title="HybridSight — GenAI Portfolio App",
    theme=gr.themes.Soft()
) as demo:
    session_id = gr.State(value=lambda: str(uuid.uuid4()))

    gr.Markdown(
        """# 👁️ HybridSight
        *A hybrid GenAI agent — documents, web search, and vision in one app.*"""
    )

    with gr.Tabs():

        # ── TAB 1: Main Hybrid Chat ──────────────────────────────────────
        with gr.Tab("💬 Hybrid Chat"):
            with gr.Row():
                with gr.Column(scale=3):
                    chatbot = gr.Chatbot(height=440, label="Conversation")
                    msg_box = gr.Textbox(placeholder="Ask anything...", show_label=False)
                    submit_btn = gr.Button("Send", variant="primary")
                    
                    submit_btn.click(
                        handle_chat,
                        inputs=[msg_box, chatbot, session_id],
                        outputs=[chatbot, session_id, trace_box]
                    ).then(lambda: "", outputs=msg_box)

                    msg_box.submit(
                        handle_chat,
                        inputs=[msg_box, chatbot, session_id],
                        outputs=[chatbot, session_id, trace_box]
                    ).then(lambda: "", outputs=msg_box)

                with gr.Column(scale=1):
                    gr.Markdown("### 🔍 Reasoning Trace")
                    trace_box = gr.Textbox(lines=14, interactive=False, show_label=False)

        # ── TAB 2: Document QA ───────────────────────────────────────────
        with gr.Tab("📄 Document QA"):
            with gr.Row():
                pdf_upload = gr.File(label="Upload a PDF", file_types=[".pdf"])
                index_status = gr.Textbox(label="Indexing status", interactive=False)
            pdf_upload.change(handle_pdf_upload, inputs=pdf_upload, outputs=index_status)
            
            gr.Markdown("""
            *After uploading your PDF, go back to the **Hybrid Chat** tab to ask questions about it!*
            """)

        # ── TAB 3: Image Studio ──────────────────────────────────────────
        with gr.Tab("🖼️ Image Studio"):
            with gr.Row():
                img_upload = gr.Image(label="Upload image", type="filepath")
                img_output = gr.Textbox(label="Vision analysis", lines=8)
            img_btn = gr.Button("Analyse Image", variant="primary")
            
            img_btn.click(
                handle_image, 
                inputs=[img_upload, session_id], 
                outputs=[img_output, trace_box]
            )

if __name__ == "__main__":
    demo.launch()
