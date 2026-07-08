# Setup & Installation

## Prerequisites
- **Python:** 3.10 or higher
- **OS:** macOS, Linux, or Windows
- **API Keys:**
  - `GROQ_API_KEY` (Required for LLM and Vision)
  - `PINECONE_API_KEY` (Optional, defaults to local ChromaDB if missing)

## Installation

1. **Clone the repository:**
```bash
git clone https://github.com/your-username/multimodal-qa-pro.git
cd multimodal-qa-pro
```

2. **Create a virtual environment:**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

## Environment Variables
Create a `.env` file in the root directory:

```env
# Required
GROQ_API_KEY=gsk_your_api_key_here

# Optional: For Cloud Vector Database
PINECONE_API_KEY=pcsk_your_api_key_here
PINECONE_INDEX_NAME=multimodal-qa

# Optional: Configuration
LLM_MODEL=llama3-70b-8192
EMBEDDING_MODEL=all-MiniLM-L6-v2
```

## Run the Application

Start the Gradio server:
```bash
python main.py
```
The application will be accessible at `http://localhost:7860`.

## Testing

Run the automated test suite using `pytest`:
```bash
pytest tests/
```
Ensure `pytest-asyncio` is installed (included in `requirements.txt`) to run asynchronous test cases.

## Deployment (HuggingFace Spaces)
This application is designed to be easily deployed to HuggingFace Spaces as a Gradio app.
1. Create a new Space and select "Gradio" as the SDK.
2. Upload the repository files.
3. Add `GROQ_API_KEY` to the Space's Repository Secrets.
4. The Space will automatically install `requirements.txt` and run `main.py` (ensure `main.py` is renamed to `app.py` or configured as the startup script in HF).
