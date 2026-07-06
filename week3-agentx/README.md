# Week 3: AgentX — ReAct Agents & Tool Calling

Welcome to the **Week 3** project of the GenAI Track. This week, we elevate LLMs from passive text generators to **Autonomous Agents**. 

An Agent is an LLM given access to a suite of external tools (like Web Search, Calculators, or APIs) and an internal reasoning loop. Instead of just trying to predict the next word, the agent actively decides *when* it lacks information, *which* tool to use to get it, and *how* to synthesize the final answer.

---

## 🧠 Core Concepts & Theory (with Real-World Examples)

### 1. The ReAct Architecture
ReAct stands for **Reason + Act**. It is the fundamental loop that powers autonomous agents.
1. **Thought**: The LLM analyzes the user's prompt and realizes it needs external data.
2. **Action**: The LLM decides to call a specific tool with specific arguments (e.g., `DuckDuckGo("latest AI news 2026")`).
3. **Observation**: The tool executes in Python and returns the raw data back to the LLM.
4. **Thought**: The LLM reads the observation. If it has enough data, it generates the final answer. If not, it loops back to step 2.
> **🏢 Modern Example:** When you use **ChatGPT with Web Browsing**, it uses a ReAct loop. It realizes you asked about today's weather, triggers a Bing search tool, reads the search results (Observation), and then writes your response. Advanced AI software engineers like **Devin** use massive ReAct loops to read terminal outputs, write code, run tests, and debug themselves iteratively over hundreds of steps.

### 2. LangGraph
LangGraph is a library for building stateful, multi-actor applications with LLMs. Unlike simple linear chains in LangChain, LangGraph allows for cyclical execution (the ReAct loop). It models the agent as a graph with nodes (the LLM, the Tools) and edges determining the routing logic.

### 3. Tool Binding
We don't have to write complex parsers to figure out what tool the LLM wants to use. Modern models (like `llama-3.3-70b-versatile`) are fine-tuned for **Function Calling**. We simply pass a list of Python functions (wrapped as `@tool`) to the model's API, and the model returns structured JSON containing the tool name and arguments it wishes to execute.
> **🏢 Modern Example:** Customer support bots at companies like **Klarna** or **Expedia** use function calling heavily. When a user says "Cancel my flight", the LLM doesn't just output text; it triggers a backend Python function `cancel_booking(reservation_id="12345")`, which actually executes the refund in their database.

### 4. Stateful Memory (`MemorySaver`)
Conversational context is crucial for an agent. LangGraph provides checkpointers (like `MemorySaver`) that save the state of the graph after every execution. When the user asks a follow-up question, the agent loads the previous graph state and continues the conversation seamlessly.
> **🏢 Modern Example:** When you return to a Claude or ChatGPT thread from three days ago and say "Write another paragraph like the last one", it instantly knows what you mean because its conversational state (memory) was saved to a database and re-loaded into the context window for this new turn.

---

## 🛠️ Key Code & Functions

### Defining a Custom Tool
The docstring is incredibly important! The LLM reads the docstring to understand *when* to use the tool.
```python
from langchain_core.tools import tool
import datetime

@tool
def get_current_date() -> str:
    """Returns today's date. Use before searching when the query
    involves 'latest', 'current', 'today', or 'this year'."""
    return datetime.date.today().isoformat()
```

### Compiling the Agent Graph
```python
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

memory = MemorySaver()
agent = create_react_agent(
    model=llm,
    tools=[search, wiki, get_current_date],
    checkpointer=memory,
    prompt=SYSTEM_PROMPT,
)
```

### Streaming the Agent's Trace
Because the agent can loop multiple times before answering, we stream the graph's execution to capture a "Reasoning Trace" (showing the user exactly what tools were called).
```python
for event in agent.stream(
    {"messages": [{"role": "user", "content": user_input}]},
    config={"configurable": {"thread_id": session_id}},
    stream_mode="values",
):
    last_msg = event["messages"][-1]
    if hasattr(last_msg, "tool_calls") and last_msg.tool_calls:
        print(f"Calling Tool: {last_msg.tool_calls[0]['name']}")
```

---

## 🚀 Setup & Execution

### Prerequisites
- Python 3.10+
- Groq API Key (from [console.groq.com](https://console.groq.com/))

### Installation
1. Navigate to the directory:
   ```bash
   cd week3-agentx
   ```
2. Activate your virtual environment:
   ```bash
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Configure your environment variables:
   ```bash
   cp .env.example .env
   # Open .env and add your GROQ_API_KEY
   ```

### Running the App
```bash
python app.py
```
Open `http://127.0.0.1:7860` in your browser. Ask a question about a recent event and watch the "Reasoning Trace" accordion to see the agent actively search the web!

---

## 🎯 Learning Outcomes
By completing this week, you should understand:
1. The mechanics of the ReAct loop.
2. How to define and inject custom Python functions as tools for an LLM.
3. How to use LangGraph to manage stateful, cyclical agent workflows.
4. The importance of highly specific Tool descriptions for accurate routing.
