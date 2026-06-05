# DocBuddy Pro — Q&A Over Multiple PDFs with Source Citations

## What is RAG?
Retrieval-Augmented Generation (RAG) is a technique that grounds a large language model on your own private documents. Instead of retraining the model, RAG first retrieves the most relevant chunks of text from your documents based on semantic similarity to your question, and then feeds those chunks directly into the LLM's prompt. The LLM acts as an intelligent reader, synthesizing an answer solely from the provided context. This avoids hallucinations and allows the model to correctly cite sources.

## Installation

1. Clone the repository and navigate to `week2-docbuddy/`.
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy `.env.example` to `.env` and insert your Groq API key:
   ```bash
   cp .env.example .env
   ```
   Add your `GROQ_API_KEY` to the `.env` file.

## Usage

Start the application:
```bash
python app.py
```
Open your browser to the URL provided in the terminal (usually `http://127.0.0.1:7860`). Upload multiple PDF files, click **Index Documents**, and then start asking questions!

## Testing Results

*(Include your screenshots here)*

- **Anti-Hallucination:** When asked "What is the capital of France?" the model correctly responds that it does not have that information based on the documents.
- **Multi-Document Retrieval:** Successfully answers questions by drawing context from different uploaded PDFs, citing the correct source and page number.

## Improvements
- Added support for multiple PDF indexing with proper context citation including filenames.
- Built an expandable "Retrieved Context" section so users can see exactly what text chunks are fed to the model.
