# trace_viewer.py - Simple local trace viewer

import json
import os
from datetime import datetime
from typing import List, Dict
import argparse

class LocalTraceViewer:
    """Simple viewer for locally stored traces"""
    
    def __init__(self, trace_dir="./"):
        self.trace_dir = trace_dir
        
    def view_traces(self, trace_file="local_agent_traces.jsonl"):
        """View traces in a human-readable format"""
        trace_path = os.path.join(self.trace_dir, trace_file)
        
        if not os.path.exists(trace_path):
            print(f"❌ Trace file not found: {trace_path}")
            return
            
        print(f"📊 Reading traces from: {trace_path}")
        print("=" * 80)
        
        with open(trace_path, 'r') as f:
            for i, line in enumerate(f, 1):
                try:
                    trace = json.loads(line.strip())
                    self._print_trace(trace, i)
                except json.JSONDecodeError:
                    print(f"⚠️  Invalid JSON on line {i}: {line[:50]}...")
                    
    def _print_trace(self, trace: Dict, line_num: int):
        """Print a single trace entry"""
        timestamp = trace.get('timestamp', 'Unknown')
        function = trace.get('function', 'Unknown')
        trace_type = trace.get('type', 'Unknown')
        
        # Color coding based on type
        if trace_type == 'start':
            icon = "🚀"
            color = "\033[94m"  # Blue
        elif trace_type == 'success':
            icon = "✅"
            color = "\033[92m"  # Green
        elif trace_type == 'error':
            icon = "❌"
            color = "\033[91m"  # Red
        else:
            icon = "📝"
            color = "\033[93m"  # Yellow
            
        reset_color = "\033[0m"
        
        print(f"{color}{icon} [{line_num:3d}] {timestamp} | {function} | {trace_type.upper()}{reset_color}")
        
        # Show duration for completed traces
        if 'duration_seconds' in trace:
            duration = trace['duration_seconds']
            print(f"     ⏱️  Duration: {duration:.3f}s")
            
        # Show preview of result or error
        if 'result_preview' in trace and trace['result_preview']:
            print(f"     📤 Result: {trace['result_preview'][:100]}...")
        elif 'error' in trace:
            print(f"     💥 Error: {trace['error']}")
            
        print()
        
    def view_agent_logs(self, agent_name="researcher"):
        """View specific agent logs"""
        log_file = f"{agent_name}_agent.log"
        log_path = os.path.join(self.trace_dir, log_file)
        
        if not os.path.exists(log_path):
            print(f"❌ Agent log not found: {log_path}")
            return
            
        print(f"🤖 {agent_name.upper()} Agent Activity Log")
        print("=" * 60)
        
        with open(log_path, 'r') as f:
            for i, line in enumerate(f, 1):
                try:
                    log_entry = json.loads(line.strip())
                    self._print_agent_log(log_entry, i)
                except json.JSONDecodeError:
                    print(f"⚠️  Invalid JSON on line {i}")
                    
    def _print_agent_log(self, log_entry: Dict, line_num: int):
        """Print agent log entry"""
        timestamp = log_entry.get('timestamp', 'Unknown')
        agent = log_entry.get('agent', 'Unknown')
        action = log_entry.get('action', 'Unknown')
        
        print(f"[{line_num:2d}] {timestamp} | {agent} | {action}")
        
        # Show relevant data
        if 'data' in log_entry and log_entry['data']:
            data = log_entry['data']
            for key, value in data.items():
                print(f"     📊 {key}: {value}")
        print()
        
    def view_workflow_summary(self):
        """Show workflow summary"""
        workflows_file = os.path.join(self.trace_dir, "workflow_log.jsonl")
        results_file = os.path.join(self.trace_dir, "workflow_results.jsonl")
        
        print("📋 WORKFLOW SUMMARY")
        print("=" * 50)
        
        # Show workflow starts
        if os.path.exists(workflows_file):
            print("🚀 Workflow Executions:")
            with open(workflows_file, 'r') as f:
                for i, line in enumerate(f, 1):
                    try:
                        workflow = json.loads(line.strip())
                        timestamp = workflow.get('timestamp', 'Unknown')
                        query = workflow.get('query', 'Unknown')
                        print(f"  {i}. {timestamp}")
                        print(f"     Query: {query}")
                    except json.JSONDecodeError:
                        pass
        
        print()
        
        # Show results
        if os.path.exists(results_file):
            print("✅ Workflow Results:")
            with open(results_file, 'r') as f:
                for i, line in enumerate(f, 1):
                    try:
                        result = json.loads(line.strip())
                        timestamp = result.get('timestamp', 'Unknown')
                        report = result.get('final_report', 'No report')
                        print(f"  {i}. {timestamp}")
                        print(f"     Report: {report[:100]}...")
                    except json.JSONDecodeError:
                        pass
        
        print()
        
    def list_available_files(self):
        """List all available trace files"""
        print("📁 Available Trace Files:")
        print("-" * 30)
        
        trace_files = [
            "local_agent_traces.jsonl",
            "researcher_agent.log", 
            "analyst_agent.log",
            "reporter_agent.log",
            "workflow_log.jsonl",
            "workflow_results.jsonl",
            "agent_traces.log"
        ]
        
        for file in trace_files:
            file_path = os.path.join(self.trace_dir, file)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                print(f"  ✅ {file} ({size} bytes)")
            else:
                print(f"  ❌ {file} (not found)")
                
def main():
    parser = argparse.ArgumentParser(description="View local agent traces")
    parser.add_argument("--dir", default="./", help="Directory containing trace files")
    parser.add_argument("--traces", action="store_true", help="View function traces")
    parser.add_argument("--agent", type=str, help="View specific agent logs (researcher/analyst/reporter)")
    parser.add_argument("--summary", action="store_true", help="View workflow summary")
    parser.add_argument("--list", action="store_true", help="List available files")
    
    args = parser.parse_args()
    
    viewer = LocalTraceViewer(args.dir)
    
    if args.list:
        viewer.list_available_files()
    elif args.traces:
        viewer.view_traces()
    elif args.agent:
        viewer.view_agent_logs(args.agent)
    elif args.summary:
        viewer.view_workflow_summary()
    else:
        print("🏠 Local Trace Viewer")
        print("=" * 40)
        viewer.list_available_files()
        print()
        viewer.view_workflow_summary()
        print()
        print("📖 Usage examples:")
        print("  python trace_viewer.py --traces    # View function traces")
        print("  python trace_viewer.py --agent researcher  # View agent logs")
        print("  python trace_viewer.py --summary   # View workflow summary")

if __name__ == "__main__":
    main()