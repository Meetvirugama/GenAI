import gradio as gr
from config import PERSONAS
from services import chat_stream

# Helper to submit messages and clear the text field instantly
def submit_message(message, history):
    return "", message, history

# Helper to dynamically update the active system prompt markdown in the accordion
def update_system_prompt(persona_name):
    return f"```text\n{PERSONAS[persona_name]['system_prompt']}\n```"

# Read CSS styling from style.css
try:
    with open("style.css", "r", encoding="utf-8") as f:
        custom_css = f.read()
except Exception:
    custom_css = ""

# Build the Gradio interface
with gr.Blocks(
    css=custom_css,
    theme=gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "sans-serif"]
    ),
    title="PromptForge — Multi-Mode AI Assistant"
) as demo:
    
    # 1. Header Banner
    with gr.Row():
        with gr.Column(scale=12):
            gr.HTML(
                "<div class='banner'>"
                "<h1>PromptForge</h1>"
                "<p>A multi-mode AI assistant demonstrating custom system prompts, "
                "few-shot prompt injections, temperature variance, and structured JSON outputs.</p>"
                "</div>"
            )
            
    # 2. Main Content Layout
    with gr.Row():
        # Left Panel (Settings & Sidebar)
        with gr.Column(scale=4, elem_classes=["sidebar-panel"]):
            gr.Markdown("### ⚙️ Persona Configuration")
            
            mode_dropdown = gr.Dropdown(
                choices=list(PERSONAS.keys()),
                value="Coding Teacher",
                label="Active Persona Mode",
                interactive=True
            )
            
            temp_slider = gr.Slider(
                minimum=0.0,
                maximum=1.5,
                step=0.1,
                value=0.7,
                label="Temperature (Creativity)",
                info="Lower is more deterministic/factual; higher is more creative.",
                interactive=True
            )
            
            with gr.Accordion("📜 Active System Prompt", open=False, elem_classes=["system-prompt-acc"]):
                system_prompt_md = gr.Markdown(
                    value=update_system_prompt("Coding Teacher")
                )
                
            # Connect persona dropdown changes to Accordion display
            mode_dropdown.change(
                fn=update_system_prompt,
                inputs=mode_dropdown,
                outputs=system_prompt_md
            )
            
        # Right Panel (Chat Interface)
        with gr.Column(scale=8):
            chatbot = gr.Chatbot(
                label="Conversation",
                bubble_full_width=False,
                height=500
            )
            
            with gr.Row():
                user_msg = gr.Textbox(
                    placeholder="Enter your message or paste code here...",
                    scale=9,
                    container=False
                )
                submit_btn = gr.Button("Send", variant="primary", scale=1, elem_classes=["primary-btn"])
                
            with gr.Row():
                clear_btn = gr.Button("🗑️ Clear Conversation", variant="secondary")
                
            # Temporary state variables to manage messaging flow cleanly
            temp_msg = gr.State()
            
            # Submit Actions (Button click & Enter key press)
            submit_btn.click(
                fn=submit_message,
                inputs=[user_msg, chatbot],
                outputs=[user_msg, temp_msg, chatbot],
                queue=False
            ).then(
                fn=chat_stream,
                inputs=[temp_msg, chatbot, mode_dropdown, temp_slider],
                outputs=chatbot,
                queue=True
            )
            
            user_msg.submit(
                fn=submit_message,
                inputs=[user_msg, chatbot],
                outputs=[user_msg, temp_msg, chatbot],
                queue=False
            ).then(
                fn=chat_stream,
                inputs=[temp_msg, chatbot, mode_dropdown, temp_slider],
                outputs=chatbot,
                queue=True
            )
            
            # Clear Conversation Action
            clear_btn.click(
                fn=lambda: [],
                inputs=None,
                outputs=chatbot,
                queue=False
            )

if __name__ == "__main__":
    demo.queue()
    # Launch with public sharing enabled as required for proxy/headless environments
    demo.launch(share=True)
