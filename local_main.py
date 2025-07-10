# Local-Only Multi-Agent Demo
# File: local_main.py

import os
import json
import logging
from datetime import datetime
from typing import Dict, Any
from dataclasses import dataclass, asdict
from langgraph.graph import StateGraph, END
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage

# Setup local logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('agent_traces.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MultiAgentDemo")

# Simple local tracing decorator
class LocalTracer:
    def __init__(self, log_file="traces.jsonl"):
        self.log_file = log_file
        
    def trace(self, func_name):
        def decorator(func):
            def wrapper(*args, **kwargs):
                start_time = datetime.now()
                
                # Log start
                trace_data = {
                    "timestamp": start_time.isoformat(),
                    "function": func_name,
                    "type": "start",
                    "args": str(args)[:200],  # Truncate long args
                }
                self._log_trace(trace_data)
                
                try:
                    result = func(*args, **kwargs)
                    
                    # Log success
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    trace_data = {
                        "timestamp": end_time.isoformat(),
                        "function": func_name,
                        "type": "success",
                        "duration_seconds": duration,
                        "result_preview": str(result)[:200] if result else None
                    }
                    self._log_trace(trace_data)
                    
                    return result
                    
                except Exception as e:
                    # Log error
                    end_time = datetime.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    trace_data = {
                        "timestamp": end_time.isoformat(),
                        "function": func_name,
                        "type": "error",
                        "duration_seconds": duration,
                        "error": str(e)
                    }
                    self._log_trace(trace_data)
                    raise
                    
            return wrapper
        return decorator
    
    def _log_trace(self, data):
        # Log to JSON Lines file for easy parsing
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(data) + '\n')

# Initialize local tracer
tracer = LocalTracer("local_agent_traces.jsonl")

@dataclass
class AgentState:
    """Simple state for agent communication"""
    messages: list
    current_agent: str
    task_complete: bool = False
    research_data: str = ""
    analysis_result: str = ""
    
    def to_dict(self):
        """Convert to dict for logging"""
        return {
            "current_agent": self.current_agent,
            "task_complete": self.task_complete,
            "research_data": self.research_data[:100] + "..." if len(self.research_data) > 100 else self.research_data,
            "analysis_result": self.analysis_result[:100] + "..." if len(self.analysis_result) > 100 else self.analysis_result,
            "message_count": len(self.messages)
        }

class LocalAgent:
    """Agent with local logging only"""
    
    def __init__(self, name: str, role: str):
        self.name = name
        self.role = role
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            api_version="2024-02-15-preview",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0.1
        )
        self.log_file = f"{name}_agent.log"

    def _log_agent_action(self, action: str, data: dict):
        """Log agent actions to local file"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "agent": self.name,
            "role": self.role,
            "action": action,
            "data": data
        }
        
        # Log to agent-specific file
        with open(self.log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        # Also log to console
        logger.info(f"🤖 {self.name} ({self.role}): {action}")

    @tracer.trace("agent_process")
    def process(self, state: AgentState) -> AgentState:
        """Process with local tracing"""
        
        self._log_agent_action("started_processing", state.to_dict())
        
        # Create prompt based on agent role
        if self.name == "researcher":
            prompt = f"Research the topic: {state.messages[-1].content}. Provide 3 key facts."
            
            self._log_agent_action("sending_llm_request", {"prompt": prompt[:100]})
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            state.research_data = response.content
            state.current_agent = "analyst"
            
            self._log_agent_action("completed_research", {
                "research_length": len(state.research_data),
                "next_agent": "analyst"
            })
            
        elif self.name == "analyst":
            prompt = f"Analyze this research data and provide insights: {state.research_data}"
            
            self._log_agent_action("sending_llm_request", {"prompt": prompt[:100]})
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            state.analysis_result = response.content
            state.current_agent = "reporter"
            
            self._log_agent_action("completed_analysis", {
                "analysis_length": len(state.analysis_result),
                "next_agent": "reporter"
            })
            
        elif self.name == "reporter":
            prompt = f"Create a brief report from this analysis: {state.analysis_result}"
            
            self._log_agent_action("sending_llm_request", {"prompt": prompt[:100]})
            response = self.llm.invoke([HumanMessage(content=prompt)])
            
            state.messages.append(AIMessage(content=response.content))
            state.task_complete = True
            
            self._log_agent_action("completed_report", {
                "report_length": len(response.content),
                "workflow_complete": True
            })
        
        self._log_agent_action("finished_processing", state.to_dict())
        return state

# Create agents
researcher = LocalAgent("researcher", "Data Researcher")
analyst = LocalAgent("analyst", "Data Analyst") 
reporter = LocalAgent("reporter", "Report Writer")

def create_workflow():
    """Create the multi-agent workflow with local logging"""
    
    def research_node(state: AgentState) -> AgentState:
        logger.info("📊 Starting research phase...")
        return researcher.process(state)
    
    def analysis_node(state: AgentState) -> AgentState:
        logger.info("🔍 Starting analysis phase...")
        return analyst.process(state)
    
    def reporting_node(state: AgentState) -> AgentState:
        logger.info("📝 Starting reporting phase...")
        return reporter.process(state)
    
    def router(state: AgentState) -> str:
        """Route to next agent based on current state"""
        next_step = None
        if state.current_agent == "analyst":
            next_step = "analysis"
        elif state.current_agent == "reporter":
            next_step = "reporting"
        else:
            next_step = END
            
        logger.info(f"🔀 Routing to: {next_step}")
        return next_step
    
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

@tracer.trace("run_workflow")
def run_local_demo(query: str):
    """Run the complete multi-agent workflow with local logging"""
    
    # Create workflow log entry
    workflow_log = {
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "workflow_id": f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    }
    
    with open("workflow_log.jsonl", 'a') as f:
        f.write(json.dumps(workflow_log) + '\n')
    
    logger.info(f"🚀 Starting LOCAL multi-agent workflow")
    logger.info(f"📝 Query: {query}")
    logger.info(f"📂 Logs will be saved to: agent_traces.log, local_agent_traces.jsonl")
    
    # Initialize state
    initial_state = AgentState(
        messages=[HumanMessage(content=query)],
        current_agent="researcher"
    )
    
    # Create and run workflow
    workflow = create_workflow()
    result = workflow.invoke(initial_state)
    
    # Log final result
    final_log = {
        "timestamp": datetime.now().isoformat(),
        "workflow_complete": True,
        "final_report": result['messages'][-1].content,
        "total_messages": len(result['messages'])
    }
    
    with open("workflow_results.jsonl", 'a') as f:
        f.write(json.dumps(final_log) + '\n')
    
    logger.info("✅ Workflow complete!")
    logger.info(f"📊 Final report: {result['messages'][-1].content}")
    logger.info("📁 Check these local files for traces:")
    logger.info("   - agent_traces.log (human readable)")
    logger.info("   - local_agent_traces.jsonl (structured traces)")
    logger.info("   - researcher_agent.log (researcher actions)")
    logger.info("   - analyst_agent.log (analyst actions)")
    logger.info("   - reporter_agent.log (reporter actions)")
    logger.info("   - workflow_log.jsonl (workflow metadata)")
    logger.info("   - workflow_results.jsonl (final results)")
    
    return result

if __name__ == "__main__":
    # Clear previous logs (optional)
    import glob
    log_files = glob.glob("*.log") + glob.glob("*.jsonl")
    for file in log_files:
        try:
            open(file, 'w').close()  # Clear file
        except:
            pass
    
    logger.info("🧹 Cleared previous log files")
    
    # Example usage
    query = "What are the benefits of using OpenTelemetry for AI applications?"
    result = run_local_demo(query)