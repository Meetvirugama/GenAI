import base64

def image_to_data_uri(filepath: str) -> str:
    # Gradio's gr.Image(type="filepath") gives you a local path
    with open(filepath, "rb") as f:
        encoded = base64.b64encode(f.read()).decode("utf-8")
    return f"data:image/jpeg;base64,{encoded}"
