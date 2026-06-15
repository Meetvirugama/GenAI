import gradio as gr
from agent import run_agent_with_trace
import uuid

def chat(message, history, session_id, trace_display):
    return history, session_id, trace_display

with gr.Blocks() as demo:
    session_id = gr.State(value=lambda: str(uuid.uuid4()))
    chatbot = gr.Chatbot(height=420, label="Conversation")
    msg_box = gr.Textbox(placeholder="Ask anything...", label="Your question")
    submit_btn = gr.Button("Send", variant="primary")
    trace_box = gr.Textbox(label="Tools called", lines=6)

    def handle_submit(message, history, session_id):
        return chat(message, history, session_id, "")

    submit_btn.click(
        handle_submit,
        inputs=[msg_box, chatbot, session_id],
        outputs=[chatbot, session_id, trace_box]
    ).then(lambda: "", outputs=msg_box)

print("Generating API info...")
info = demo.get_api_info()
print("Success!")
