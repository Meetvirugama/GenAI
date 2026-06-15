import uuid
import gradio as gr
import gradio_client.utils as client_utils

# Monkey patch for Gradio json schema parser bug with boolean additionalProperties
_original_schema_parser = client_utils._json_schema_to_python_type
def _patched_schema_parser(schema, defs):
    if isinstance(schema, dict) and "additionalProperties" in schema and isinstance(schema["additionalProperties"], bool):
        schema = schema.copy()
        del schema["additionalProperties"]
    return _original_schema_parser(schema, defs)
client_utils._json_schema_to_python_type = _patched_schema_parser

from agent import run_agent_with_trace

def chat(message, history, session_id, trace_display):
    if not message.strip():
        return history, session_id, trace_display

    answer, trace = run_agent_with_trace(message, session_id)
    history = history + [[message, answer]]
    return history, session_id, trace

with gr.Blocks(title="AgentX — Research Agent") as demo:
    session_id = gr.State(value=lambda: str(uuid.uuid4()))

    gr.Markdown("# 🤖 AgentX\nA research agent with web search, Wikipedia, and memory.")

    chatbot = gr.Chatbot(height=420, label="Conversation")
    msg_box = gr.Textbox(placeholder="Ask anything...", label="Your question")
    submit_btn = gr.Button("Send", variant="primary")

    with gr.Accordion("🔍 Agent Reasoning Trace", open=False):
        trace_box = gr.Textbox(
            label="Tools called during last response",
            lines=6, interactive=False
        )

    def handle_submit(message, history, session_id):
        return chat(message, history, session_id, "")

    submit_btn.click(
        handle_submit,
        inputs=[msg_box, chatbot, session_id],
        outputs=[chatbot, session_id, trace_box]
    ).then(lambda: "", outputs=msg_box)

    msg_box.submit(
        handle_submit,
        inputs=[msg_box, chatbot, session_id],
        outputs=[chatbot, session_id, trace_box]
    ).then(lambda: "", outputs=msg_box)

if __name__ == "__main__":
    demo.launch(share=True)
