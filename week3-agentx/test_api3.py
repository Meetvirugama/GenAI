import gradio as gr
import gradio_client.utils as client_utils

_original_schema_parser = client_utils._json_schema_to_python_type
def _patched_schema_parser(schema, defs):
    if isinstance(schema, dict) and "additionalProperties" in schema and isinstance(schema["additionalProperties"], bool):
        schema = schema.copy()
        del schema["additionalProperties"]
    return _original_schema_parser(schema, defs)
client_utils._json_schema_to_python_type = _patched_schema_parser

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
