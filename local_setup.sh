#!/bin/bash
# local_setup.sh - Completely local logging setup

echo "🏠 Setting up LOCAL-ONLY Multi-Agent Demo"
echo "📝 All traces and logs will be saved locally - NO external endpoints!"

# Create local directories
echo "📁 Creating local log directories..."
mkdir -p logs
mkdir -p local_traces  
mkdir -p trace_files
mkdir -p jaeger_data

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << 'EOF'
# Azure OpenAI Configuration
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
EOF
    echo "📝 Please edit .env file with your Azure OpenAI credentials"
    echo "   Then run this script again."
    exit 1
fi

echo "🐳 Building Docker container..."
docker build -t multi-agent-local .

# Option 1: Run with completely local file logging
echo ""
echo "Choose logging option:"
echo "1) 📄 File-only logging (no UI, just local files)"
echo "2) 🖥️  File logging + Local Jaeger UI" 
echo "3) 🔧 File logging + Local OpenTelemetry Collector"
echo ""
read -p "Enter choice (1-3): " choice

case $choice in
    1)
        echo "📄 Running with file-only logging..."
        docker run -it --rm \
            --env-file .env \
            -v $(pwd)/logs:/app/logs \
            -v $(pwd)/local_traces:/app/traces \
            multi-agent-local python local_main.py
        ;;
    2)
        echo "🖥️  Starting with local Jaeger UI..."
        docker-compose -f docker-compose-local.yml up -d jaeger-local
        sleep 5
        
        docker run -it --rm \
            --env-file .env \
            --network "$(basename $(pwd))_default" \
            -v $(pwd)/logs:/app/logs \
            -v $(pwd)/local_traces:/app/traces \
            multi-agent-local python local_main.py
        ;;
    3)
        echo "🔧 Starting with local OpenTelemetry collector..."
        docker-compose -f docker-compose-local.yml up -d file-collector
        sleep 10
        
        docker run -it --rm \
            --env-file .env \
            --network "$(basename $(pwd))_default" \
            -v $(pwd)/logs:/app/logs \
            -v $(pwd)/local_traces:/app/traces \
            multi-agent-local python local_main.py
        ;;
    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "✅ Demo completed! Check these LOCAL files:"
echo "   📂 ./logs/ - Agent activity logs"
echo "   📂 ./local_traces/ - Structured trace data"
echo "   📂 ./trace_files/ - OpenTelemetry trace files (if option 3)"
echo ""

if [ "$choice" = "2" ]; then
    echo "🌐 Jaeger UI: http://localhost:16686"
fi

if [ "$choice" = "3" ]; then
    echo "📊 Collector health: http://localhost:8888/metrics"
    echo "📄 Trace files: ./trace_files/"
fi

echo ""
echo "🧹 To clean up Docker containers:"
echo "   docker-compose -f docker-compose-local.yml down"