"""Quick test to see detailed output"""
import subprocess
import sys

result = subprocess.run(
    [sys.executable, "sanity_test.py"],
    capture_output=True,
    text=True,
    cwd=r"c:\Users\vijay\.gemini\antigravity\scratch\learning_orchestrator"
)

print(result.stdout)
print(result.stderr)
