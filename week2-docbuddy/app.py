import gradio as gr
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from document_processor import index_documents
from chat_engine import respond

with gr.Blocks(title="DocBuddy Pro") as demo:
    gr.Markdown("## DocBuddy — Ask Your Documents")

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=420)
            msg_box = gr.Textbox(placeholder="Ask a question about your documents…")
            with gr.Accordion("Advanced Settings", open=False):
                top_k_slider = gr.Slider(minimum=1, maximum=50, value=5, step=1, label="Chunks to Retrieve (Top-K)")

        with gr.Column(scale=2):
            file_upload = gr.File(
                file_count="multiple",
                file_types=[".pdf"],
                label="Upload PDFs",
            )
            index_btn = gr.Button("Index Documents")
            status_label = gr.Textbox(label="Status", interactive=False)
            
            context_box = gr.Accordion("🔍 Retrieved Context", open=False)
            with context_box:
                context_display = gr.Markdown()

    index_btn.click(
        fn=index_documents,
        inputs=[file_upload],
        outputs=[status_label]
    )
    
    msg_box.submit(
        fn=respond,
        inputs=[msg_box, chatbot, top_k_slider],
        outputs=[chatbot, context_display]
    ).then(
        fn=lambda: "",
        inputs=None,
        outputs=[msg_box]
    )

if __name__ == "__main__":
    demo.launch()
