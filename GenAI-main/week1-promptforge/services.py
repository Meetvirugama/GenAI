import os
import json
from groq import Groq
from dotenv import load_dotenv
from config import PERSONAS

# Load environment variables
load_dotenv()

# Initialize Groq client safely
api_key = os.getenv("GROQ_API_KEY")
client = Groq(api_key=api_key) if api_key else None

def build_messages(persona_name, user_message, chat_history):
    """
    Constructs the message payload for the Groq API:
    1. System prompt
    2. Few-shot examples for the persona
    3. Conversation history
    4. Latest user message
    """
    persona = PERSONAS[persona_name]
    messages = [{"role": "system", "content": persona["system_prompt"]}]
    
    # Prepend few-shot examples
    for example in persona["few_shot_examples"]:
        messages.append({
            "role": example["role"],
            "content": example["content"]
        })
        
    # Append conversation history
    for user_hist, assistant_hist in chat_history:
        if user_hist:
            messages.append({"role": "user", "content": user_hist})
        if assistant_hist:
            messages.append({"role": "assistant", "content": assistant_hist})
            
    # Append latest message
    messages.append({"role": "user", "content": user_message})
    return messages

def chat_stream(message, history, persona_name, temperature):
    """
    Generator function that streams response chunks and updates the Gradio Chatbot history.
    """
    if not client:
        yield history + [[message, "⚠️ **API Key Missing:** Please verify you have created a `.env` file containing your `GROQ_API_KEY` and restart the application."]]
        return
        
    if not message.strip():
        yield history
        return
        
    persona = PERSONAS[persona_name]
    messages = build_messages(persona_name, message, history)
    
    try:
        stream = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=float(temperature),
            stream=True
        )
    except Exception as e:
        yield history + [[message, f"❌ **Error calling Groq API:** {str(e)}"]]
        return

    accumulated = ""
    new_history = history + [[message, ""]]
    
    for chunk in stream:
        delta = chunk.choices[0].delta.content or ""
        accumulated += delta
        
        # During stream, show raw output to user
        new_history[-1][1] = accumulated
        yield new_history
        
    # Post-processing: try formatting if we are in Code Reviewer mode
    if persona["output_format"] == "json":
        cleaned = accumulated.strip()
        # Clean markdown code fences if outputted by the model
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()
        
        try:
            parsed = json.loads(cleaned)
            severity = parsed.get("severity", "unknown").lower()
            
            severity_colors = {
                "low": "🟢 **Low**",
                "medium": "🟡 **Medium**",
                "high": "🔴 **High**"
            }
            severity_badge = severity_colors.get(severity, f"⚪ **{severity.capitalize()}**")
            
            issues_list = parsed.get("issues", [])
            issues_md = "\n".join([f"- {issue}" for issue in issues_list]) if issues_list else "*No specific issues found.*"
            
            suggestions_list = parsed.get("suggestions", [])
            suggestions_md = "\n".join([f"- {suggestion}" for suggestion in suggestions_list]) if suggestions_list else "*No suggestions for improvement.*"
            
            formatted_md = (
                f"### 🔍 Code Review Report\n\n"
                f"**Overall Severity:** {severity_badge}\n\n"
                f"#### ⚠️ Issues Identified:\n"
                f"{issues_md}\n\n"
                f"#### 💡 Suggestions for Improvement:\n"
                f"{suggestions_md}"
            )
            
            new_history[-1][1] = formatted_md
            yield new_history
        except Exception as e:
            # Fallback: display warning and raw output
            warning_md = (
                f"⚠️ **Warning: Failed to parse structured JSON response.** (Error: {str(e)})\n\n"
                f"**Raw Output:**\n```json\n{accumulated}\n```"
            )
            new_history[-1][1] = warning_md
            yield new_history
