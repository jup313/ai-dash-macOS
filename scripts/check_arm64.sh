#!/bin/bash
# Quick ARM64 architecture check

ARCH=$(uname -m)
if [ "$ARCH" = "arm64" ]; then
    echo "✅ Architecture: $ARCH (Apple Silicon confirmed)"
    exit 0
else
    echo "❌ Architecture: $ARCH (ARM64 required)"
    exit 1
fi
