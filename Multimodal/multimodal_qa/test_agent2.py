import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from core.config import Config
Config.validate()
from agent.graph import MultimodalAgent

agent = MultimodalAgent(tools=[])
print(agent.graph.get_graph().nodes)
