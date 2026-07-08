import os
import asyncio
import uuid
import gradio as gr
from typing import Tuple, List, Optional
from core.logger import get_logger
from core.context import session_id_var, image_path_var
from core.crud import save_message, fetch_user_sessions, load_session_history, delete_session

logger = get_logger(__name__)

class AppCallbacks:
    def __init__(self, vector_store, doc_loader, agent, get_current_user):
        self.vector_store = vector_store
        self.doc_loader = doc_loader
        self.agent = agent
        self.get_current_user = get_current_user

    def get_user_id(self, request: gr.Request):
        if self.get_current_user and hasattr(request, 'request'):
            return self.get_current_user(request.request)
        return None

    def get_user_email(self, request: gr.Request):
        if hasattr(request, 'request'):
            return request.request.session.get('user_email')
        return None

    def check_auth_state(self, request: gr.Request):
        user_id = self.get_user_id(request)
        user_email = self.get_user_email(request)
        
        if user_id and user_email:
            sessions = fetch_user_sessions(user_id)
            return (
                gr.update(visible=False), # login_btn
                gr.update(value=f"👤 **{user_email}**", visible=True), # profile_text
                gr.update(visible=True),  # logout_btn
                gr.update(visible=True),  # new_chat_btn
                gr.update(choices=sessions, visible=True), # session_list
                gr.update(visible=True),  # load_chat_btn
                gr.update(visible=True)   # delete_chat_btn
            )
        else:
            return (
                gr.update(visible=True),  # login_btn
                gr.update(visible=False), # profile_text
                gr.update(visible=False), # logout_btn
                gr.update(visible=False), # new_chat_btn
                gr.update(visible=False), # session_list
                gr.update(visible=False), # load_chat_btn
                gr.update(visible=False)  # delete_chat_btn
            )

    async def handle_pdf_upload(self, files, session_id: str, progress=gr.Progress()) -> str:
        session_id_var.set(session_id)
        if not files:
            return "No files uploaded."
            
        total_size = sum(os.path.getsize(f.name) for f in files)
        if total_size > 15 * 1024 * 1024:
            return "Total file size exceeds 15MB limit. Please upload smaller PDFs."
            
        try:
            progress(0, desc="Extracting text from PDFs...")
            paths = [f.name for f in files]
            docs = await asyncio.to_thread(self.doc_loader.load_pdfs, paths)
            
            if not docs:
                return "Could not extract text from the uploaded PDFs."
            
            progress(0.5, desc="Embedding and saving to vector store...")
            await asyncio.to_thread(self.vector_store.add_documents, docs, session_id)
            
            progress(1.0, desc="Done!")
            return f"Successfully indexed {len(docs)} chunks from {len(paths)} PDF(s). You can now ask questions!"
        except Exception as e:
            logger.error(f"PDF upload error: {e}")
            return f"Error processing PDFs: {e}"

    async def clear_docs(self, session_id: str):
        session_id_var.set(session_id)
        await asyncio.to_thread(self.vector_store.clear_session, session_id)
        return "All indexed documents cleared."

    def doc_chat(self, msg: str, history: List, sid: str, request: gr.Request):
        session_id_var.set(sid)
        ans, trace = self.agent.run(msg, history=history)
        
        user_id = self.get_user_id(request)
        if user_id:
            save_message(sid, "user", msg, user_id)
            save_message(sid, "assistant", ans, user_id)
            
        return history + [(msg, ans)], ""

    def img_chat(self, msg: str, history: List, sid: str, path: str, request: gr.Request):
        session_id_var.set(sid)
        image_path_var.set(path)
        ans, _ = self.agent.run(msg, history=history)
        
        user_id = self.get_user_id(request)
        if user_id:
            save_message(sid, "user", msg, user_id)
            save_message(sid, "assistant", ans, user_id)
            
        return history + [(msg, ans)], ""

    def handle_image_upload(self, image_path: Optional[str], session_id: str) -> Tuple[str, Optional[str]]:
        session_id_var.set(session_id)
        image_path_var.set(image_path)
        if not image_path:
            return "No image provided.", None
        if not os.path.exists(image_path):
            return "Image file not found.", None
        return "Image loaded successfully. You can now ask questions about it!", image_path

    def load_session(self, selected_session: str, request: gr.Request):
        """Loads a selected session from the dropdown."""
        user_id = self.get_user_id(request)
        if not selected_session or not user_id:
            return selected_session, [], [], None, "_Upload an image and click Load Image._", None
        
        history = load_session_history(selected_session)
        return selected_session, history, history, None, "_Upload an image and click Load Image._", None

    def create_new_chat(self):
        new_sid = str(uuid.uuid4())
        return new_sid, [], [], None, "_Upload an image and click Load Image._", None

    def delete_selected_session(self, sid: str, request: gr.Request):
        user_id = self.get_user_id(request)
        if user_id and sid:
            delete_session(sid)
            # Fetch new list of sessions
            sessions = fetch_user_sessions(user_id)
            return str(uuid.uuid4()), [], [], None, "_Upload an image and click Load Image._", None, gr.update(choices=sessions)
        return sid, [], [], None, "_Upload an image and click Load Image._", None, gr.update()
