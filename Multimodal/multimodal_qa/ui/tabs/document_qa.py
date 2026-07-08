import gradio as gr

def build_document_qa_tab():
    with gr.TabItem("Document Q&A", id="docs"):
        with gr.Row():
            with gr.Column(scale=1):
                pdf_upload = gr.File(
                    label="Upload PDFs",
                    file_types=[".pdf"],
                    file_count="multiple",
                )
                with gr.Row():
                    index_btn = gr.Button("Index Documents", variant="primary")
                    clear_docs_btn = gr.Button("Clear All Docs", variant="secondary")
                pdf_status = gr.Markdown(
                    value="_Upload PDFs and click Index Documents to begin._",
                    elem_classes="status-box"
                )

            with gr.Column(scale=2):
                doc_chatbot = gr.Chatbot(label="Document Q&A", show_label=False, scale=1, elem_classes="chatbot")
                with gr.Row(elem_classes="input-row"):
                    doc_input = gr.Textbox(
                        placeholder="Ask a question about your PDFs...",
                        show_label=False,
                        scale=8,
                        container=False,
                        elem_classes="input-box"
                    )
                    doc_send_btn = gr.Button("Ask", variant="primary", scale=1, elem_classes="send-btn", min_width=80)
                    
    return {
        "pdf_upload": pdf_upload,
        "index_btn": index_btn,
        "clear_docs_btn": clear_docs_btn,
        "pdf_status": pdf_status,
        "doc_chatbot": doc_chatbot,
        "doc_input": doc_input,
        "doc_send_btn": doc_send_btn
    }
