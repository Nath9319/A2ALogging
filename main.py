# Simple A2A Multi-Agent Demo with OpenTelemetry
# File: main.py

import os
from typing import Dict, Any
from dataclasses import dataclass
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolExecutor
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage
import openlit
from traceloop.sdk import Traceloop
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Verify required environment variables
required_vars = [
    'AZURE_OPENAI_ENDPOINT',
    'AZURE_OPENAI_DEPLOYMENT_NAME',
    'AZURE_OPENAI_API_KEY',
    'OPENAI_API_VERSION'
]

missing_vars = [var for var in required_vars if not os.getenv(var)]
if missing_vars:
    print(f"❌ Missing required environment variables: {missing_vars}")
    print("📝 Please check your .env file")
    exit(1)

print("✅ Environment variables loaded from .env file:")
print(f"   🔗 Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
print(f"   🚀 Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
print(f"   📅 API Version: {os.getenv('OPENAI_API_VERSION')}")
print(f"   🔑 API Key: {'*' * 20}...{os.getenv('AZURE_OPENAI_API_KEY', '')[-4:]}")
print()

# Initialize OpenTelemetry observability - COMPLETELY LOCAL
# Option 1: Console logging (immediate output)
from opentelemetry.sdk.trace.export import ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from traceloop.sdk import Traceloop
# For local development - see traces immediately in console
openlit.init()  # No endpoint = console output only

# For local OTLP collector (still local, no external calls)
Traceloop.init(
    app_name="a2a-multi-agent-local",
    api_endpoint="http://localhost:4318",  # Local collector only
    disable_batch=True,  # See traces immediately
    exporter=ConsoleSpanExporter()  # Also log to console
)

@dataclass
class AgentState:
    """Simple state for agent communication"""
    messages: list
    current_agent: str
    task_complete: bool = False
    research_data: str = ""
    analysis_result: str = ""

class SimpleAgent:
    """Base agent class with OpenTelemetry tracing"""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_version=os.getenv("OPENAI_API_VERSION"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0.1
        )

    @openlit.trace
    def process(self, state: AgentState) -> AgentState:
        """Process with automatic tracing"""
        print(f"🤖 {self.name} ({self.role}) is processing...")
        
        # Create prompt based on agent role
        if self.name == "researcher":
            prompt = f"Research the topic: {state.messages[-1].content}. Provide 3 key facts."
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state.research_data = response.content
            state.current_agent = "analyst"
            
        elif self.name == "analyst":
            prompt = f"Analyze this research data and provide insights: {state.research_data}"
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state.analysis_result = response.content
            state.current_agent = "reporter"
            
        elif self.name == "reporter":
            prompt = f"Create a brief report from this analysis: {state.analysis_result}"
            response = self.llm.invoke([HumanMessage(content=prompt)])
            state.messages.append(AIMessage(content=response.content))
            state.task_complete = True
        
        return state

# Create agents
researcher = SimpleAgent("researcher", "Data Researcher")
analyst = SimpleAgent("analyst", "Data Analyst") 
reporter = SimpleAgent("reporter", "Report Writer")

# LangGraph workflow definition
def create_workflow():
    """Create the multi-agent workflow"""
    
    def research_node(state: AgentState) -> AgentState:
        return researcher.process(state)
    
    def analysis_node(state: AgentState) -> AgentState:
        return analyst.process(state)
    
    def reporting_node(state: AgentState) -> AgentState:
        return reporter.process(state)
    
    def router(state: AgentState) -> str:
        """Route to next agent based on current state"""
        if state.current_agent == "analyst":
            return "analysis"
        elif state.current_agent == "reporter":
            return "reporting"
        else:
            return END
    
    # Build the graph
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("research", research_node)
    workflow.add_node("analysis", analysis_node)
    workflow.add_node("reporting", reporting_node)
    
    # Add edges
    workflow.set_entry_point("research")
    workflow.add_conditional_edges("research", router)
    workflow.add_conditional_edges("analysis", router)
    workflow.add_edge("reporting", END)
    
    return workflow.compile()

@openlit.trace
def run_multi_agent_demo(query: str):
    """Run the complete multi-agent workflow"""
    print(f"🚀 Starting multi-agent workflow for: {query}")
    
    # Initialize state
    initial_state = AgentState(
        messages=[HumanMessage(content=query)],
        current_agent="researcher"
    )
    
    # Create and run workflow
    workflow = create_workflow()
    result = workflow.invoke(initial_state)
    
    print(f"✅ Workflow complete!")
    print(f"📊 Final report: {result['messages'][-1].content}")
    
    return result

if __name__ == "__main__":
    # Example usage
    query = "What are the benefits of using OpenTelemetry for AI applications?"
    result = run_multi_agent_demo(query)