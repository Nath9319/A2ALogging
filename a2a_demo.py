# Real Google A2A Protocol Implementation
# File: a2a_demo.py

import os
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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")
openlit.init() # Automatically reads OTLP endpoint from environment variables
Traceloop.init(app_name="a2a-protocol-demo", api_endpoint=OTLP_ENDPOINT, disable_batch=True)
print(f"✅ OpenTelemetry configured to send traces to: {OTLP_ENDPOINT}")

@dataclass
class AgentCard:
    agent_id: str
    name: str
    description: str
    version: str
    capabilities: List[str]
    endpoint: str

@dataclass
class TaskRequest:
    task_id: str
    requesting_agent: str
    target_agent: str
    task_type: str
    parameters: Dict[str, Any]
    timestamp: str

@dataclass
class TaskResponse:
    task_id: str
    responding_agent: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    timestamp: Optional[str] = None

class A2AAgent:
    def __init__(self, agent_card: AgentCard, port: int):
        self.agent_card = agent_card
        self.port = port
        self.llm = AzureChatOpenAI(
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            azure_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME"),
            api_version=os.getenv("OPENAI_API_VERSION"),
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            temperature=0.1
        )

    async def start_server(self):
        from aiohttp import web
        app = web.Application()
        app.router.add_get('/agent-card', self.get_agent_card)
        app.router.add_post('/task', self.handle_task_request)
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', self.port)
        await site.start()
        print(f"🚀 Agent '{self.agent_card.name}' listening on port {self.port}")

    async def get_agent_card(self, request):
        from aiohttp import web
        return web.json_response(asdict(self.agent_card))

    @openlit.trace
    async def handle_task_request(self, request):
        from aiohttp import web
        data = await request.json()
        task_request = TaskRequest(**data)
        print(f"📨 Agent '{self.agent_card.name}' received task '{task_request.task_type}'")
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

    async def process_task(self, task_request: TaskRequest) -> Dict[str, Any]:
        raise NotImplementedError

class ResearcherA2AAgent(A2AAgent):
    def __init__(self, port: int):
        super().__init__(AgentCard(
            agent_id="researcher-agent",
            name="Research Agent",
            description="Conducts research",
            version="1.0",
            capabilities=["research"],
            endpoint=f"http://researcher-agent:{port}"
        ), port)

    @openlit.trace
    async def process_task(self, task_request: TaskRequest) -> Dict[str, Any]:
        topic = task_request.parameters.get("topic", "")
        prompt = f"Research the topic: {topic}. Provide 3 key facts with sources."
        response = await self.llm.ainvoke(prompt)
        return {"research_data": response.content}

class AnalystA2AAgent(A2AAgent):
    def __init__(self, port: int):
        super().__init__(AgentCard(
            agent_id="analyst-agent",
            name="Analysis Agent",
            description="Analyzes data",
            version="1.0",
            capabilities=["analysis"],
            endpoint=f"http://analyst-agent:{port}"
        ), port)

    @openlit.trace
    async def process_task(self, task_request: TaskRequest) -> Dict[str, Any]:
        research_data = task_request.parameters.get("research_data", "")
        prompt = f"Analyze this research data and provide key insights: {research_data}"
        response = await self.llm.ainvoke(prompt)
        return {"analysis_result": response.content}

class ReporterA2AAgent(A2AAgent):
    def __init__(self, port: int):
        super().__init__(AgentCard(
            agent_id="reporter-agent",
            name="Report Agent",
            description="Creates reports",
            version="1.0",
            capabilities=["reporting"],
            endpoint=f"http://reporter-agent:{port}"
        ), port)

    @openlit.trace
    async def process_task(self, task_request: TaskRequest) -> Dict[str, Any]:
        analysis_data = task_request.parameters.get("analysis_data", "")
        prompt = f"Create a brief executive report from this analysis: {analysis_data}"
        response = await self.llm.ainvoke(prompt)
        return {"final_report": response.content}

class A2AOrchestrator:
    @openlit.trace
    async def send_task_request(self, endpoint: str, task_type: str, parameters: Dict[str, Any]) -> Optional[TaskResponse]:
        task_request = TaskRequest(
            task_id=str(uuid.uuid4()),
            requesting_agent="orchestrator",
            target_agent=endpoint,
            task_type=task_type,
            parameters=parameters,
            timestamp=datetime.now().isoformat()
        )
        print(f"➡️  Orchestrator sending task '{task_type}' to '{endpoint}/task'")
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(f"{endpoint}/task", json=asdict(task_request)) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return TaskResponse(**data)
                    else:
                        print(f"❌ Task to '{endpoint}' failed with status: {resp.status} - {await resp.text()}")
                        return None
        except Exception as e:
            print(f"❌ Exception during task request to '{endpoint}': {e}")
            return None

    @openlit.trace
    async def run_workflow(self, query: str):
        print("\n🚀 Starting A2A Workflow...")
        research_response = await self.send_task_request("http://researcher-agent:8001", "research", {"topic": query})
        if not research_response or research_response.status != "success": return
        
        analysis_response = await self.send_task_request("http://analyst-agent:8002", "analysis", research_response.result)
        if not analysis_response or analysis_response.status != "success": return

        report_response = await self.send_task_request("http://reporter-agent:8003", "reporting", analysis_response.result)
        if not report_response or report_response.status != "success": return

        final_report = report_response.result["final_report"]
        print("✅ A2A Workflow completed successfully!")
        print(f"📊 Final Report: {final_report}")
        
        results_dir = "/app/results"
        os.makedirs(results_dir, exist_ok=True)
        with open(os.path.join(results_dir, "a2a_workflow_results.json"), "w") as f:
            json.dump(report_response.result, f, indent=2)
        print(f"\n📁 Results saved to ./results/a2a_workflow_results.json")

# --- Main execution block ---
if __name__ == "__main__":
    role = os.getenv("DOCKER_CONTAINER_ROLE", "orchestrator")

    async def run_agent(agent_class, port):
        agent = agent_class(port)
        await agent.start_server()
        await asyncio.Event().wait() # Run forever

    if role == "agent":
        agent_type = os.getenv("AGENT_TYPE")
        port = int(os.getenv("AGENT_PORT"))
        agent_map = {
            "researcher": ResearcherA2AAgent,
            "analyst": AnalystA2AAgent,
            "reporter": ReporterA2AAgent,
        }
        if agent_type in agent_map:
            asyncio.run(run_agent(agent_map[agent_type], port))
    else:
        orchestrator = A2AOrchestrator()
        query = "What are the benefits of using OpenTelemetry for AI applications?"
        asyncio.run(orchestrator.run_workflow(query))
