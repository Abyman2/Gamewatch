import json
import sys
sys.stdout.reconfigure(encoding='utf-8')

transcript_path = r"C:\Users\25194\.gemini\antigravity-ide\brain\6f9c61b6-d78b-436a-b68d-32d6c6b500ee\.system_generated\logs\transcript.jsonl"
with open(transcript_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

print(f"Total lines: {len(lines)}")
print(f"Total lines: {len(lines)}")
data = json.loads(lines[4798])
print("=== CONTENT OF 4798 ===")
print(data.get("content"))
