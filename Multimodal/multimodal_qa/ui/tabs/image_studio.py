import gradio as gr

def build_image_studio_tab():
    with gr.TabItem("Image Studio", id="vision"):
        with gr.Row():
            with gr.Column(scale=1):
                image_upload = gr.Image(
                    label="Upload Image",
                    type="filepath",
                )
                load_image_btn = gr.Button("Load Image", variant="primary")
                image_status = gr.Markdown(
                    value="_Upload an image and click Load Image._",
                    elem_classes="status-box"
                )

            with gr.Column(scale=2):
                img_chatbot = gr.Chatbot(label="Image Q&A", show_label=False, scale=1, elem_classes="chatbot")
                with gr.Row(elem_classes="input-row"):
                    img_input = gr.Textbox(
                        placeholder="Ask about the image...",
                        show_label=False,
                        scale=8,
                        container=False,
                        elem_classes="input-box"
                    )
                    img_send_btn = gr.Button("Ask", variant="primary", scale=1, elem_classes="send-btn", min_width=80)
                    
    return {
        "image_upload": image_upload,
        "load_image_btn": load_image_btn,
        "image_status": image_status,
        "img_chatbot": img_chatbot,
        "img_input": img_input,
        "img_send_btn": img_send_btn
    }
