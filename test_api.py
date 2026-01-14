import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60 + "\n")

# 1. Check health
print_section("1. Checking System Health")
response = requests.get(f"{BASE_URL}/health")
print(json.dumps(response.json(), indent=2))

# 2. Upload a file (if you have one)
print_section("2. Uploading Document")
try:
    with open("documents/ai_basics.txt", "rb") as f:
        files = {"file": ("ai_basics.txt", f, "text/plain")}
        response = requests.post(f"{BASE_URL}/upload", files=files)
        print(json.dumps(response.json(), indent=2))
except FileNotFoundError:
    print("⚠️  File not found. Make sure documents/ai_basics.txt exists")

# 3. Initialize system
print_section("3. Initializing System (this will take a few minutes)")
response = requests.post(f"{BASE_URL}/initialize")
print(json.dumps(response.json(), indent=2))

# 4. Ask questions
print_section("4. Asking Questions")

questions = [
    "What is FastAPI?",
    "What is machine learning?",
    "What are the benefits of using local RAG?"
]

for question in questions:
    print(f"\n❓ Question: {question}")
    print("🤔 Thinking...\n")
    
    response = requests.post(
        f"{BASE_URL}/ask",
        json={"question": question}
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Answer:\n{result['answer']}\n")
        print(f"📚 Sources: {len(result['sources'])} documents used")
    else:
        print(f"❌ Error: {response.text}")
    
    time.sleep(2)  # Wait between questions

print_section("✅ Testing Complete!")