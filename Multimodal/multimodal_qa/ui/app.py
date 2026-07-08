import uuid
import gradio as gr
from core.logger import get_logger
from ui.callbacks import AppCallbacks
from ui.sidebar import build_sidebar
from ui.tabs.document_qa import build_document_qa_tab
from ui.tabs.image_studio import build_image_studio_tab

logger = get_logger(__name__)

CSS = """
/* The existing CSS as before */
body {
    background-color: #f8fafc !important;
    color: #1e293b !important;
}
.app-wrapper {
    max-width: 1000px;
    margin: 0 auto;
    padding: 2rem;
}
.sidebar {
    background: #ffffff;
    border-right: 1px solid #e2e8f0;
    padding: 1.5rem;
    height: 100vh;
}
.main-header {
    text-align: center;
    margin-bottom: 2rem;
}
.main-header h1 {
    font-size: 2.5rem;
    font-weight: 800;
    color: #0f172a;
    margin-bottom: 0.5rem;
    background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
.main-header p {
    font-size: 1.1rem;
    color: #64748b;
}
.status-box {
    padding: 1rem;
    border-radius: 8px;
    background-color: #f1f5f9;
    border: 1px solid #e2e8f0;
    margin-top: 1rem;
    text-align: center;
    color: #475569;
}
.chatbot {
    border-radius: 12px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03) !important;
    background: #ffffff !important;
    min-height: 500px !important;
}
.input-row {
    align-items: center;
    margin-top: 1rem;
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 24px;
    padding: 0.25rem;
    box-shadow: 0 2px 4px rgba(0,0,0,0.02);
}
.input-box {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
}
.input-box textarea {
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    color: #1e293b !important;
}
.input-box textarea:focus {
    border: none !important;
    box-shadow: none !important;
}
.send-btn {
    border-radius: 20px !important;
}
.footer-text {
    text-align: center;
    color: #94a3b8;
    font-size: 0.875rem;
    margin-top: 2rem;
}
"""

def build_app(vector_store, doc_loader, agent, get_current_user=None) -> gr.Blocks:
    callbacks = AppCallbacks(vector_store, doc_loader, agent, get_current_user)

    with gr.Blocks(
        css=CSS,
        title="ScriptAI",
        fill_height=True,
        js="""
        function() {
            document.body.classList.remove('dark');
            const observer = new MutationObserver((mutations) => {
                mutations.forEach((mutation) => {
                    if (document.body.classList.contains('dark')) {
                        document.body.classList.remove('dark');
                    }
                });
            });
            observer.observe(document.body, { attributes: true, attributeFilter: ['class'] });
        }
        """,
        theme=gr.themes.Base(
            primary_hue="blue",
            secondary_hue="slate",
            neutral_hue="slate",
            font=[gr.themes.GoogleFont("Inter"), "sans-serif"],
        ).set(
            body_background_fill="#f8fafc",
            body_text_color="#1e293b",
            background_fill_primary="#ffffff",
            background_fill_secondary="#f8fafc",
            border_color_primary="#e2e8f0",
            block_background_fill="#ffffff",
            block_border_color="#e2e8f0",
            block_border_width="1px",
            block_radius="16px",
            input_background_fill="#ffffff",
            button_primary_background_fill="#3b82f6",
            button_primary_background_fill_hover="#2563eb",
            button_primary_text_color="#ffffff",
            button_secondary_background_fill="#f1f5f9",
            button_secondary_background_fill_hover="#e2e8f0",
            button_secondary_text_color="#475569",
        )
    ) as app:
        
        session_id = gr.State(lambda: str(uuid.uuid4()))
        image_path_state = gr.State(None)

        with gr.Row():
            sidebar_ui = build_sidebar()
            
            with gr.Column(elem_classes="app-wrapper", scale=4):
                gr.HTML("""
                <div class="main-header">
                    <h1>ScriptAI</h1>
                    <p>Chat with ScriptAI. Seamlessly ask questions, search docs, and analyze images.</p>
                </div>
                """)
    
                with gr.Tabs():
                    docs_ui = build_document_qa_tab()
                    img_ui = build_image_studio_tab()

                gr.HTML("""
                <div class="footer-text">
                    Built using LangGraph · Groq · ChromaDB · Gradio
                </div>
                """)

        # Connect Sidebar Events
        sidebar_ui["new_chat_btn"].click(
            fn=callbacks.create_new_chat,
            outputs=[
                session_id, 
                docs_ui["doc_chatbot"], 
                img_ui["img_chatbot"],
                img_ui["image_upload"],
                img_ui["image_status"],
                image_path_state
            ]
        )
        
        sidebar_ui["delete_chat_btn"].click(
            fn=callbacks.delete_selected_session,
            inputs=[sidebar_ui["session_list"]],
            outputs=[
                session_id, 
                docs_ui["doc_chatbot"], 
                img_ui["img_chatbot"],
                img_ui["image_upload"],
                img_ui["image_status"],
                image_path_state,
                sidebar_ui["session_list"]
            ]
        )
        
        sidebar_ui["load_chat_btn"].click(
            fn=callbacks.load_session,
            inputs=[sidebar_ui["session_list"]],
            outputs=[
                session_id, 
                docs_ui["doc_chatbot"], 
                img_ui["img_chatbot"],
                img_ui["image_upload"],
                img_ui["image_status"],
                image_path_state
            ]
        )

        # Connect Docs Events
        docs_ui["index_btn"].click(
            fn=callbacks.handle_pdf_upload, 
            inputs=[docs_ui["pdf_upload"], session_id], 
            outputs=[docs_ui["pdf_status"]]
        )
        docs_ui["clear_docs_btn"].click(
            fn=callbacks.clear_docs, 
            inputs=[session_id], 
            outputs=[docs_ui["pdf_status"]]
        )
        docs_ui["doc_send_btn"].click(
            fn=callbacks.doc_chat,
            inputs=[docs_ui["doc_input"], docs_ui["doc_chatbot"], session_id],
            outputs=[docs_ui["doc_chatbot"], docs_ui["doc_input"]],
        )
        docs_ui["doc_input"].submit(
            fn=callbacks.doc_chat,
            inputs=[docs_ui["doc_input"], docs_ui["doc_chatbot"], session_id],
            outputs=[docs_ui["doc_chatbot"], docs_ui["doc_input"]],
        )

        # Connect Image Events
        img_ui["load_image_btn"].click(
            fn=callbacks.handle_image_upload,
            inputs=[img_ui["image_upload"], session_id],
            outputs=[img_ui["image_status"], image_path_state]
        )
        img_ui["image_upload"].change(
            fn=callbacks.handle_image_upload,
            inputs=[img_ui["image_upload"], session_id],
            outputs=[img_ui["image_status"], image_path_state]
        )
        img_ui["img_send_btn"].click(
            fn=callbacks.img_chat,
            inputs=[img_ui["img_input"], img_ui["img_chatbot"], session_id, image_path_state],
            outputs=[img_ui["img_chatbot"], img_ui["img_input"]],
        )
        img_ui["img_input"].submit(
            fn=callbacks.img_chat,
            inputs=[img_ui["img_input"], img_ui["img_chatbot"], session_id, image_path_state],
            outputs=[img_ui["img_chatbot"], img_ui["img_input"]],
        )

        # On Load Auth Check
        app.load(
            fn=callbacks.check_auth_state,
            outputs=[
                sidebar_ui["login_btn"], 
                sidebar_ui["profile_text"], 
                sidebar_ui["logout_btn"], 
                sidebar_ui["new_chat_btn"], 
                sidebar_ui["session_list"], 
                sidebar_ui["load_chat_btn"], 
                sidebar_ui["delete_chat_btn"]
            ]
        )

    return app
