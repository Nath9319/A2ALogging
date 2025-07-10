# Real Google A2A Protocol Implementation
# File: a2a_demo.py

import json
import asyncio
import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime
import aiohttp
from langchain_openai import AzureChatOpenAI
import openlit
from traceloop.sdk import Traceloop

# Initialize OpenTelemetry for A2A communication
openlit.init()
Traceloop.init(app_name="a2a-protocol-demo", disable_batch=True)

@dataclass
class AgentCard:
    """Google A2A AgentCard specification"""
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[str]
    communication_protocols: List[str]
    endpoint: str
    authentication: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None

@dataclass
class TaskRequest:
    """A2A Task Request"""
    task_id: str
    requesting_agent: str
    target_agent: str
    task_type: str
    parameters: Dict[str, Any]
    timestamp: str
    callback_url: Optional[str] = None

@dataclass
class TaskResponse:
    """A2A Task Response"""
    task_id: str
    responding_agent: str
    status: str  # "success", "error", "in_progress"
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: str = None

class A2AAgent:
    """Base A2A Protocol Agent"""
    
    def __init__(self, agent_card: AgentCard, port: int):
        self.agent_card = agent_card
        self.port = port
        self.running = False
        self.discovered_agents: Dict[str, AgentCard] = {}
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
            api_version="2024-02-15-preview",
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0.1
        )
    
    @openlit.trace
    async def start_server(self):
        """Start A2A protocol server"""
        from aiohttp import web
        
        app = web.Application()
        app.router.add_get('/agent-card', self.get_agent_card)
        app.router.add_post('/discover', self.handle_discovery)
        app.router.add_post('/task', self.handle_task_request)
        app.router.add_get('/health', self.health_check)
        
        self.running = True
        print(f"🚀 A2A Agent '{self.agent_card.name}' starting on port {self.port}")
        
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()
        
        return runner
    
    async def get_agent_card(self, request):
        """Return this agent's capabilities (A2A AgentCard)"""
        from aiohttp import web
        return web.json_response(asdict(self.agent_card))
    
    @openlit.trace
    async def handle_discovery(self, request):
        """Handle agent discovery requests"""
        from aiohttp import web
        
        data = await request.json()
        requesting_agent_card = AgentCard(**data)
        
        # Store discovered agent
        self.discovered_agents[requesting_agent_card.agent_id] = requesting_agent_card
        
        print(f"🔍 Discovered agent: {requesting_agent_card.name}")
        print(f"   Capabilities: {requesting_agent_card.capabilities}")
        
        # Return our agent card
        return web.json_response({
            "status": "discovered",
            "agent_card": asdict(self.agent_card)
        })
    
    @openlit.trace
    async def handle_task_request(self, request):
        """Handle incoming task requests from other agents"""
        from aiohttp import web
        
        data = await request.json()
        task_request = TaskRequest(**data)
        
        print(f"📨 Received task from {task_request.requesting_agent}")
        print(f"   Task: {task_request.task_type}")
        
        # Process task
        try:
            result = await self.process_task(task_request)
            response = TaskResponse(
                task_id=task_request.task_id,
                responding_agent=self.agent_card.agent_id,
                status="success",
                result=result,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            response = TaskResponse(
                task_id=task_request.task_id,
                responding_agent=self.agent_card.agent_id,
                status="error",
                error=str(e),
                timestamp=datetime.now().isoformat()
            )
        
        return web.json_response(asdict(response))
    
    async def health_check(self, request):
        """Health check endpoint"""
        from aiohttp import web
        return web.json_response({"status": "healthy", "agent": self.agent_card.name})
    
    @openlit.trace
    async def discover_agent(self, target_url: str) -> Optional[AgentCard]:
        """Discover another A2A agent"""
        try:
            async with aiohttp.ClientSession() as session:
                # Send discovery request
                discovery_data = asdict(self.agent_card)
                async with session.post(f"{target_url}/discover", json=discovery_data) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        agent_card = AgentCard(**data['agent_card'])
                        self.discovered_agents[agent_card.agent_id] = agent_card
                        print(f"✅ Successfully discovered: {agent_card.name}")
                        return agent_card
                    else:
                        print(f"❌ Discovery failed: {resp.status}")
                        return None
        except Exception as e:
            print(f"❌ Discovery error: {e}")
            return None
    
    @openlit.trace
    async def send_task_request(self, target_agent_id: str, task_type: str, parameters: Dict[str, Any]) -> Optional[TaskResponse]:
        """Send task request to another agent via A2A protocol"""
        
        if target_agent_id not in self.discovered_agents:
            print(f"❌ Agent {target_agent_id} not discovered yet")
            return None
        
        target_agent = self.discovered_agents[target_agent_id]
        task_id = str(uuid.uuid4())
        
        task_request = TaskRequest(
            task_id=task_id,
            requesting_agent=self.agent_card.agent_id,
            target_agent=target_agent_id,
            task_type=task_type,
            parameters=parameters,
            timestamp=datetime.now().isoformat()
        )
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{target_agent.endpoint}/task", json=asdict(task_request)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        response = TaskResponse(**data)
                        print(f"✅ Task completed by {target_agent.name}")
                        return response
                    else:
                        print(f"❌ Task failed: {resp.status}")
                        return None
        except Exception as e:
            print(f"❌ Task error: {e}")
            return None
    
    async def process_task(self, task_request: TaskRequest) -> Dict[str, Any]:
        """Process task - to be implemented by specific agents"""
        raise NotImplementedError("Subclasses must implement process_task")

class ResearcherA2AAgent(A2AAgent):
    """Researcher agent using A2A protocol"""
    
    def __init__(self, port: int = 8001):
        agent_card = AgentCard(
            agent_id="researcher-001",
            name="Research Agent",
            description="Conducts research on given topics",
            version="1.0.0",
            capabilities=["research", "fact-finding", "web-search"],
            communication_protocols=["A2A-v1"],
            endpoint=f"http://localhost:{port}"
        )
        super().__init__(agent_card, port)
    
    @openlit.trace
    async def process_task(self, task_request: TaskRequest) -> Dict[str, Any]:
        """Process research tasks"""
        if task_request.task_type == "research":
            topic = task_request.parameters.get("topic", "")
            
            # Use LLM to research
            prompt = f"Research the topic: {topic}. Provide 3 key facts with sources."
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.llm.invoke([{"role": "user", "content": prompt}])
            )
            
            return {
                "research_data": response.content,
                "topic": topic,
                "agent_id": self.agent_card.agent_id
            }
        else:
            raise ValueError(f"Unknown task type: {task_request.task_type}")

class AnalystA2AAgent(A2AAgent):
    """Analyst agent using A2A protocol"""
    
    def __init__(self, port: int = 8002):
        agent_card = AgentCard(
            agent_id="analyst-001",
            name="Analysis Agent", 
            description="Analyzes research data and provides insights",
            version="1.0.0",
            capabilities=["analysis", "insights", "data-processing"],
            communication_protocols=["A2A-v1"],
            endpoint=f"http://localhost:{port}"
        )
        super().__init__(agent_card, port)
    
    @openlit.trace
    async def process_task(self, task_request: TaskRequest) -> Dict[str, Any]:
        """Process analysis tasks"""
        if task_request.task_type == "analyze":
            research_data = task_request.parameters.get("research_data", "")
            
            # Use LLM to analyze
            prompt = f"Analyze this research data and provide key insights: {research_data}"
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.llm.invoke([{"role": "user", "content": prompt}])
            )
            
            return {
                "analysis_result": response.content,
                "source_data_length": len(research_data),
                "agent_id": self.agent_card.agent_id
            }
        else:
            raise ValueError(f"Unknown task type: {task_request.task_type}")

class ReporterA2AAgent(A2AAgent):
    """Reporter agent using A2A protocol"""
    
    def __init__(self, port: int = 8003):
        agent_card = AgentCard(
            agent_id="reporter-001",
            name="Report Agent",
            description="Creates reports from analysis data", 
            version="1.0.0",
            capabilities=["reporting", "document-generation", "summarization"],
            communication_protocols=["A2A-v1"],
            endpoint=f"http://localhost:{port}"
        )
        super().__init__(agent_card, port)
    
    @openlit.trace
    async def process_task(self, task_request: TaskRequest) -> Dict[str, Any]:
        """Process reporting tasks"""
        if task_request.task_type == "report":
            analysis_data = task_request.parameters.get("analysis_data", "")
            
            # Use LLM to create report
            prompt = f"Create a brief executive report from this analysis: {analysis_data}"
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.llm.invoke([{"role": "user", "content": prompt}])
            )
            
            return {
                "final_report": response.content,
                "report_length": len(response.content),
                "agent_id": self.agent_card.agent_id
            }
        else:
            raise ValueError(f"Unknown task type: {task_request.task_type}")

class A2AOrchestrator:
    """Orchestrates A2A multi-agent workflow"""
    
    def __init__(self):
        self.agents = {}
        self.workflow_results = {}
    
    async def add_agent(self, agent: A2AAgent):
        """Add agent to orchestrator"""
        self.agents[agent.agent_card.agent_id] = agent
        await agent.start_server()
        await asyncio.sleep(1)  # Give server time to start
    
    @openlit.trace
    async def discover_all_agents(self):
        """Make all agents discover each other"""
        print("🔍 Starting agent discovery process...")
        
        agent_list = list(self.agents.values())
        
        # Each agent discovers all others
        for i, agent1 in enumerate(agent_list):
            for j, agent2 in enumerate(agent_list):
                if i != j:  # Don't discover self
                    await agent1.discover_agent(agent2.agent_card.endpoint)
        
        print("✅ Agent discovery completed")
    
    @openlit.trace
    async def run_a2a_workflow(self, query: str) -> Dict[str, Any]:
        """Run multi-agent workflow using A2A protocol"""
        
        print(f"🚀 Starting A2A Workflow: {query}")
        
        # Get agent references
        researcher = None
        analyst = None
        reporter = None
        
        for agent in self.agents.values():
            if "research" in agent.agent_card.capabilities:
                researcher = agent
            elif "analysis" in agent.agent_card.capabilities:
                analyst = agent
            elif "reporting" in agent.agent_card.capabilities:
                reporter = agent
        
        if not all([researcher, analyst, reporter]):
            raise ValueError("Missing required agents")
        
        # Step 1: Research (A2A communication)
        print("📊 Step 1: Research phase...")
        research_response = await researcher.send_task_request(
            target_agent_id=researcher.agent_card.agent_id,
            task_type="research",
            parameters={"topic": query}
        )
        
        if not research_response or research_response.status != "success":
            raise Exception("Research task failed")
        
        research_data = research_response.result["research_data"]
        
        # Step 2: Analysis (A2A communication)
        print("🔍 Step 2: Analysis phase...")
        analysis_response = await analyst.send_task_request(
            target_agent_id=analyst.agent_card.agent_id,
            task_type="analyze", 
            parameters={"research_data": research_data}
        )
        
        if not analysis_response or analysis_response.status != "success":
            raise Exception("Analysis task failed")
        
        analysis_data = analysis_response.result["analysis_result"]
        
        # Step 3: Reporting (A2A communication)
        print("📝 Step 3: Reporting phase...")
        report_response = await reporter.send_task_request(
            target_agent_id=reporter.agent_card.agent_id,
            task_type="report",
            parameters={"analysis_data": analysis_data}
        )
        
        if not report_response or report_response.status != "success":
            raise Exception("Reporting task failed")
        
        final_report = report_response.result["final_report"]
        
        result = {
            "query": query,
            "research_data": research_data,
            "analysis_data": analysis_data,
            "final_report": final_report,
            "workflow_complete": True,
            "agents_used": [
                researcher.agent_card.agent_id,
                analyst.agent_card.agent_id,
                reporter.agent_card.agent_id
            ]
        }
        
        print("✅ A2A Workflow completed successfully!")
        print(f"📊 Final Report: {final_report}")
        
        return result

async def main():
    """Main A2A demo function"""
    print("🌐 Starting Google A2A Protocol Demo")
    print("=" * 50)
    
    # Create orchestrator
    orchestrator = A2AOrchestrator()
    
    # Create A2A agents
    researcher = ResearcherA2AAgent(port=8001)
    analyst = AnalystA2AAgent(port=8002)
    reporter = ReporterA2AAgent(port=8003)
    
    try:
        # Add agents to orchestrator
        await orchestrator.add_agent(researcher)
        await orchestrator.add_agent(analyst)
        await orchestrator.add_agent(reporter)
        
        # Agent discovery phase
        await orchestrator.discover_all_agents()
        
        # Run A2A workflow
        query = "What are the benefits of using OpenTelemetry for AI applications?"
        result = await orchestrator.run_a2a_workflow(query)
        
        # Save results locally
        with open("a2a_workflow_results.json", "w") as f:
            json.dump(result, f, indent=2)
        
        print("\n📁 Results saved to: a2a_workflow_results.json")
        
    except KeyboardInterrupt:
        print("\n👋 Shutting down A2A demo...")
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    import os
    asyncio.run(main())