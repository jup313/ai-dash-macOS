#!/bin/bash
# Quick memory availability check for 28GB Apple Silicon systems

if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 required for memory check"
    exit 1
fi

python3 -c "
import psutil

mem = psutil.virtual_memory()
swap = psutil.swap_memory()

total_gb = mem.total / (1024**3)
avail_gb = mem.available / (1024**3)
used_gb = mem.used / (1024**3)
pct = mem.percent

print(f'Memory Report')
print(f'=============')
print(f'Total:     {total_gb:.1f} GB')
print(f'Used:      {used_gb:.1f} GB')
print(f'Available: {avail_gb:.1f} GB')
print(f'Usage:     {pct:.1f}%')
print(f'Swap Used: {swap.used / (1024**3):.1f} GB')
print()

if pct >= 75:
    print('❌ CRITICAL: Memory usage above 75%')
    print('   Heavy model loading BLOCKED')
elif pct >= 65:
    print('⚠️  WARNING: Memory usage above 65%')
    print('   Consider freeing resources before loading models')
else:
    print('✅ HEALTHY: Memory available for model loading')
    print(f'   Can load models up to ~{avail_gb * 0.7:.1f} GB safely')
" 2>/dev/null || echo "❌ Failed to read memory (psutil may not be installed)"
