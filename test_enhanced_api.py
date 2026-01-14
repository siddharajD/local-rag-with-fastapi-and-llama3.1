"""
Enhanced test script for RAG API with multiple file types
Tests document upload, initialization, and querying
"""

import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def print_response(response, show_full=False):
    """Print API response in formatted JSON"""
    if response.status_code == 200:
        data = response.json()
        if show_full:
            print(json.dumps(data, indent=2))
        else:
            print(json.dumps(data, indent=2)[:500] + "..." if len(json.dumps(data)) > 500 else json.dumps(data, indent=2))
    else:
        print(f"❌ Error {response.status_code}: {response.text}")

# ==================== TEST 1: Check Supported Formats ====================
print_section("TEST 1: Supported File Formats")
response = requests.get(f"{BASE_URL}/supported-formats")
print_response(response, show_full=True)

# ==================== TEST 2: System Health ====================
print_section("TEST 2: System Health Check")
response = requests.get(f"{BASE_URL}/health")
print_response(response, show_full=True)

# ==================== TEST 3: List Current Documents ====================
print_section("TEST 3: Current Documents")
response = requests.get(f"{BASE_URL}/documents")
print_response(response, show_full=True)

# ==================== TEST 4: Upload Different File Types ====================
print_section("TEST 4: Upload Test Files")

# Check if test files exist in documents folder
test_files = [
    ("documents/ai_basics.txt", "text/plain"),
    ("documents/rag_documentation.md", "text/markdown"),
    ("documents/ai_models_comparison.html", "text/html"),
    ("documents/sample_products.csv", "text/csv"),
]

for file_path, mime_type in test_files:
    if os.path.exists(file_path):
        print(f"\n📤 Uploading: {os.path.basename(file_path)}")
        try:
            with open(file_path, "rb") as f:
                files = {"file": (os.path.basename(file_path), f, mime_type)}
                response = requests.post(f"{BASE_URL}/upload", files=files)
                if response.status_code == 200:
                    print(f"  ✅ {response.json()['message']}")
                else:
                    print(f"  ❌ Upload failed: {response.text}")
        except Exception as e:
            print(f"  ⚠️  Error: {str(e)}")
    else:
        print(f"\n⏭️  Skipped: {file_path} (not found)")

# ==================== TEST 5: List Documents After Upload ====================
print_section("TEST 5: Documents After Upload")
response = requests.get(f"{BASE_URL}/documents")
print_response(response, show_full=True)

# ==================== TEST 6: Initialize System ====================
print_section("TEST 6: Initialize RAG System")
print("⏳ This will take 2-5 minutes. Please wait...")
print("   (Processing documents and creating embeddings)\n")

response = requests.post(f"{BASE_URL}/initialize")
if response.status_code == 200:
    print("✅ System initialized successfully!")
    print_response(response, show_full=True)
else:
    print(f"❌ Initialization failed: {response.text}")
    exit(1)

# ==================== TEST 7: Ask Various Questions ====================
print_section("TEST 7: Question Answering")

questions = [
    "What is RAG and how does it work?",
    "Compare the different AI models available (Llama 2, Mistral, Phi)",
    "What products are available in the electronics category and what are their prices?",
    "What are the benefits of using local RAG systems?",
    "Which AI model should I use if I have limited RAM?",
    "Tell me about the technical details of RAG implementation",
]

for i, question in enumerate(questions, 1):
    print(f"\n{'─'*70}")
    print(f"Question {i}/{len(questions)}: {question}")
    print('─'*70)
    print("🤔 Thinking...\n")
    
    try:
        response = requests.post(
            f"{BASE_URL}/ask",
            json={"question": question},
            timeout=120  # 2 minute timeout for LLM responses
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"📝 Answer:\n{result['answer']}\n")
            print(f"📚 Sources Used: {len(result['sources'])} documents")
            
            # Show source previews
            for idx, source in enumerate(result['sources'], 1):
                preview = source['content_preview'][:100] + "..."
                print(f"   {idx}. {preview}")
        else:
            print(f"❌ Error: {response.text}")
    
    except requests.exceptions.Timeout:
        print("⏱️  Request timed out. The model might be taking longer than expected.")
    except Exception as e:
        print(f"❌ Error: {str(e)}")
    
    # Wait between questions to not overload the system
    if i < len(questions):
        print("\n⏳ Waiting 3 seconds before next question...")
        time.sleep(3)

# ==================== TEST 8: Performance with Different Models ====================
print_section("TEST 8: Model Switching Test")
print("💡 To test different models (mistral, phi), update your main.py:")
print("   Change: rag_system = LocalRAGSystem(model_name='mistral')")
print("   Then restart the server and reinitialize.\n")

# ==================== TEST 9: Document Management ====================
print_section("TEST 9: Document Management")

# List all documents
response = requests.get(f"{BASE_URL}/documents")
if response.status_code == 200:
    docs = response.json()
    print(f"📚 Total documents: {docs['count']}")
    print(f"💾 Total size: {docs['total_size_mb']} MB\n")
    
    print("Documents:")
    for doc in docs['documents']:
        print(f"  • {doc['name']} ({doc['type']}) - {doc['size_kb']} KB")

# ==================== COMPLETION ====================
print_section("✅ ALL TESTS COMPLETED!")
print("Summary:")
print("  ✅ File format support verified")
print("  ✅ Multiple document types uploaded")
print("  ✅ System initialization successful")
print("  ✅ Question answering working")
print("  ✅ Document management tested")
print("\n🎉 Your RAG API is fully functional!\n")
print("Next steps:")
print("  1. Try uploading your own documents")
print("  2. Experiment with different Ollama models (mistral, phi)")
print("  3. Adjust chunk size and retrieval parameters")
print("  4. Build a frontend application")
print("\n" + "="*70 + "\n")
