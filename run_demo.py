# run_demo.py - Simple script to run demo with .env validation

import os
from dotenv import load_dotenv

def validate_env_file():
    """Validate .env file has all required variables"""
    
    # Load .env file
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("📝 Creating template .env file...")
        
        template = """# Azure OpenAI Configuration
OPENAI_API_VERSION=2024-02-15-preview
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_DEPLOYMENT_NAME=your-deployment-name
AZURE_OPENAI_API_KEY=your-api-key-here
"""
        with open('.env', 'w') as f:
            f.write(template)
        
        print("✅ Template .env file created")
        print("📝 Please edit .env file with your Azure OpenAI credentials")
        return False
    
    load_dotenv()
    
    # Check required variables
    required_vars = {
        'OPENAI_API_VERSION': 'OpenAI API Version (e.g., 2024-02-15-preview)',
        'AZURE_OPENAI_ENDPOINT': 'Azure OpenAI Endpoint URL',
        'AZURE_OPENAI_DEPLOYMENT_NAME': 'Azure OpenAI Deployment Name',
        'AZURE_OPENAI_API_KEY': 'Azure OpenAI API Key'
    }
    
    missing_vars = []
    placeholder_vars = []
    
    for var, description in required_vars.items():
        value = os.getenv(var)
        if not value:
            missing_vars.append(f"   {var}: {description}")
        elif value in ['your-api-key-here', 'your-deployment-name', 'https://your-resource.openai.azure.com/']:
            placeholder_vars.append(f"   {var}: {description}")
    
    if missing_vars:
        print("❌ Missing required environment variables:")
        for var in missing_vars:
            print(var)
        return False
    
    if placeholder_vars:
        print("⚠️  Please update placeholder values in .env file:")
        for var in placeholder_vars:
            print(var)
        return False
    
    print("✅ All environment variables are configured:")
    print(f"   🔗 Endpoint: {os.getenv('AZURE_OPENAI_ENDPOINT')}")
    print(f"   🚀 Deployment: {os.getenv('AZURE_OPENAI_DEPLOYMENT_NAME')}")
    print(f"   📅 API Version: {os.getenv('OPENAI_API_VERSION')}")
    print(f"   🔑 API Key: {'*' * 20}...{os.getenv('AZURE_OPENAI_API_KEY', '')[-4:]}")
    
    return True

def main():
    """Main function to run demo"""
    print("🚀 Multi-Agent Demo with .env Configuration")
    print("=" * 50)
    
    if not validate_env_file():
        print("\n❌ Please fix .env file configuration first")
        return
    
    print("\n🎯 Choose demo type:")
    print("1. 📄 Local file logging only")
    print("2. 🌐 Real Google A2A Protocol")
    print("3. 🐳 Docker with observability stack")
    
    choice = input("\nEnter choice (1-3): ").strip()
    
    if choice == "1":
        print("\n📄 Running local file logging demo...")
        print("📁 Logs will be saved to local files")
        try:
            from local_main import run_local_demo
            query = "What are the benefits of using OpenTelemetry for AI applications?"
            run_local_demo(query)
        except ImportError:
            print("❌ local_main.py not found. Using basic demo...")
            from main import run_multi_agent_demo
            query = "What are the benefits of using OpenTelemetry for AI applications?"
            run_multi_agent_demo(query)
    
    elif choice == "2":
        print("\n🌐 Running Google A2A Protocol demo...")
        print("🔗 Agents will communicate via HTTP using A2A protocol")
        try:
            import asyncio
            from a2a_demo import main as a2a_main
            asyncio.run(a2a_main())
        except ImportError:
            print("❌ a2a_demo.py not found. Please ensure file exists.")
    
    elif choice == "3":
        print("\n🐳 Running Docker deployment...")
        print("📊 Full observability stack with OpenLIT, Jaeger, etc.")
        import subprocess
        try:
            subprocess.run(["docker-compose", "up", "--build"], check=True)
        except subprocess.CalledProcessError:
            print("❌ Docker deployment failed. Check docker-compose.yml")
        except FileNotFoundError:
            print("❌ Docker not found. Please install Docker first.")
    
    else:
        print("❌ Invalid choice")

if __name__ == "__main__":
    main()