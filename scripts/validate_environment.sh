#!/bin/bash
# ai-dash-macOS Environment Validation Script
# Validates all requirements for running on Apple Silicon

set -euo pipefail

echo ""
echo "🔍 ai-dash-macOS Environment Validation"
echo "========================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

pass() {
    echo "✅ $1"
    PASS_COUNT=$((PASS_COUNT + 1))
}

fail() {
    echo "❌ $1"
    FAIL_COUNT=$((FAIL_COUNT + 1))
}

warn() {
    echo "⚠️  $1"
}

# Check 1: Architecture
ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    pass "Architecture: $ARCH"
else
    fail "Architecture: $ARCH (arm64 required)"
fi

# Check 2: Platform
PLATFORM=$(uname -s)
if [ "$PLATFORM" = "Darwin" ]; then
    pass "Platform: macOS ($PLATFORM)"
else
    fail "Platform: $PLATFORM (Darwin/macOS required)"
fi

# Check 3: Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
    PYTHON_MAJOR=$(python3 -c "import sys; print(sys.version_info.major)")
    PYTHON_MINOR=$(python3 -c "import sys; print(sys.version_info.minor)")
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 11 ]; then
        pass "Python: $PYTHON_VERSION"
    else
        fail "Python: $PYTHON_VERSION (3.11+ required)"
    fi
else
    fail "Python3 not found"
fi

# Check 4: Rosetta detection
if [ "$ARCH" = "arm64" ]; then
    TRANSLATED=$(sysctl -n sysctl.proc_translated 2>/dev/null || echo "0")
    if [ "$TRANSLATED" = "0" ]; then
        pass "No Rosetta translation detected"
    else
        fail "Running under Rosetta translation"
    fi
else
    warn "Cannot check Rosetta (not ARM64)"
fi

# Check 5: Memory
if command -v python3 &> /dev/null; then
    MEMORY_INFO=$(python3 -c "
import psutil
mem = psutil.virtual_memory()
total_gb = mem.total / (1024**3)
avail_gb = mem.available / (1024**3)
pct = mem.percent
print(f'{total_gb:.1f}|{avail_gb:.1f}|{pct:.1f}')
" 2>/dev/null || echo "")
    if [ -n "$MEMORY_INFO" ]; then
        TOTAL_GB=$(echo "$MEMORY_INFO" | cut -d'|' -f1)
        AVAIL_GB=$(echo "$MEMORY_INFO" | cut -d'|' -f2)
        PCT_USED=$(echo "$MEMORY_INFO" | cut -d'|' -f3)
        pass "Memory: ${TOTAL_GB}GB total, ${AVAIL_GB}GB available (${PCT_USED}% used)"
    else
        warn "Could not read memory info (psutil may not be installed)"
    fi
else
    warn "Cannot check memory (Python3 not found)"
fi

# Check 6: Ollama
OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
if curl -s --connect-timeout 5 "$OLLAMA_URL/api/tags" > /dev/null 2>&1; then
    MODEL_COUNT=$(curl -s "$OLLAMA_URL/api/tags" 2>/dev/null | python3 -c "import sys,json; print(len(json.load(sys.stdin).get('models',[])))" 2>/dev/null || echo "?")
    pass "Ollama reachable at $OLLAMA_URL ($MODEL_COUNT models available)"
else
    fail "Ollama not reachable at $OLLAMA_URL (run: ollama serve)"
fi

# Check 7: Node.js (optional for Phase 5)
if command -v node &> /dev/null; then
    NODE_VERSION=$(node -v)
    NODE_ARCH=$(node -p "process.arch")
    if [ "$NODE_ARCH" = "arm64" ]; then
        pass "Node.js: $NODE_VERSION ($NODE_ARCH)"
    else
        warn "Node.js: $NODE_VERSION ($NODE_ARCH) — arm64 recommended"
    fi
else
    warn "Node.js not found (needed for Phase 5)"
fi

# Check 8: .env file
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
if [ -f "$PROJECT_DIR/.env" ]; then
    pass "Environment configuration loaded (.env)"
else
    if [ -f "$PROJECT_DIR/.env.example" ]; then
        warn "No .env file found. Copy from .env.example:"
        echo "        cp $PROJECT_DIR/.env.example $PROJECT_DIR/.env"
    else
        fail "No .env or .env.example found"
    fi
fi

# Summary
echo ""
echo "========================================"
TOTAL=$((PASS_COUNT + FAIL_COUNT))
if [ "$FAIL_COUNT" -eq 0 ]; then
    echo "🎉 All $PASS_COUNT checks passed. Ready for Phase 1."
else
    echo "⚠️  $PASS_COUNT/$TOTAL checks passed, $FAIL_COUNT failed."
    echo "   Fix the issues above before proceeding."
fi
echo ""
