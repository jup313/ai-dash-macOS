#!/bin/bash
# Quick Ollama connectivity check

OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"

echo "Checking Ollama at $OLLAMA_URL..."

if curl -s --connect-timeout 5 "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    echo "✅ Ollama is reachable"
    echo ""
    echo "Available models:"
    curl -s "$OLLAMA_URL/api/tags" | python3 -c "
import sys, json
data = json.load(sys.stdin)
models = data.get('models', [])
if models:
    for m in models:
        size_gb = m.get('size', 0) / (1024**3)
        print(f'  - {m[\"name\"]} ({size_gb:.1f}GB)')
else:
    print('  (no models installed)')
" 2>/dev/null || echo "  (could not parse model list)"
    exit 0
else
    echo "❌ Ollama not reachable at $OLLAMA_URL"
    echo ""
    echo "To start Ollama:"
    echo "  ollama serve"
    echo ""
    echo "To install Ollama:"
    echo "  https://ollama.ai"
    exit 1
fi
