import gradio as gr
import app

print("Generating API info...")
info = app.demo.get_api_info()
print("Success!")
