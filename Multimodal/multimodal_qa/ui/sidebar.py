import gradio as gr

def build_sidebar():
    with gr.Column(scale=1, min_width=250, elem_classes="sidebar"):
        gr.Markdown("### 📜 Chat History")
        login_btn = gr.Button("Login with Google", link="/login/google")
        profile_text = gr.Markdown(visible=False)
        logout_btn = gr.Button("Logout", link="/logout", visible=False, variant="secondary")
        new_chat_btn = gr.Button("➕ New Chat")
        session_list = gr.Dropdown(label="Select Session", choices=[], interactive=True)
        load_chat_btn = gr.Button("Load Session")
        delete_chat_btn = gr.Button("Delete Session", variant="stop")
        
    return {
        "login_btn": login_btn,
        "profile_text": profile_text,
        "logout_btn": logout_btn,
        "new_chat_btn": new_chat_btn,
        "session_list": session_list,
        "load_chat_btn": load_chat_btn,
        "delete_chat_btn": delete_chat_btn
    }
