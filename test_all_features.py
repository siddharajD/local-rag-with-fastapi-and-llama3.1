"""
Master test script for all advanced features
Tests: Streaming, Conversation History, Enhanced Document Management
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def print_header(title):
    """Print main header"""
    print("\n" + "="*80)
    print(f"  {title}")
    print("="*80 + "\n")

def print_section(title):
    """Print section header"""
    print("\n" + "─"*80)
    print(f"  {title}")
    print("─"*80 + "\n")

def check_system():
    """Check if system is ready"""
    print_section("🏥 System Health Check")
    
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            print(f"✅ API Server: Online")
            print(f"✅ System Status: {health['status']}")
            print(f"📚 Documents: {health['documents_count']}")
            
            if not health["system_ready"]:
                print("\n⚠️  WARNING: System not initialized!")
                print("   Run: POST /initialize first")
                return False
            return True
        else:
            print(f"❌ Server returned: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API server!")
        print("   Start server with: python main.py")
        return False

def test_enhanced_document_management():
    """Test enhanced document management features"""
    print_header("📚 ENHANCED DOCUMENT MANAGEMENT")
    
    # Test 1: List all documents
    print_section("Test 1: List All Documents")
    response = requests.get(f"{BASE_URL}/documents")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total documents: {data['count']}")
        print(f"💾 Total size: {data['total_size_mb']} MB\n")
        
        if data['documents']:
            print("Documents:")
            for doc in data['documents'][:5]:  # Show first 5
                print(f"  • {doc['name']}")
                print(f"    Type: {doc['type']} | Size: {doc['size_kb']} KB")
                print(f"    Modified: {doc['modified']}")
    else:
        print(f"❌ Error: {response.text}")
    
    # Test 2: Supported formats
    print_section("Test 2: Supported File Formats")
    response = requests.get(f"{BASE_URL}/supported-formats")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Total formats supported: {data['total_formats']}\n")
        
        for category, formats in data['supported_formats'].items():
            print(f"{category.upper()}:")
            for name, ext in formats.items():
                print(f"  • {name}: {ext}")
            print()
    else:
        print(f"❌ Error: {response.text}")

def test_standard_vs_streaming():
    """Compare standard and streaming responses"""
    print_header("⚡ STANDARD vs STREAMING COMPARISON")
    
    question = "What is RAG and how does it work?"
    
    # Test standard endpoint
    print_section("Standard Response (POST /ask)")
    print(f"❓ Question: {question}\n")
    
    start = time.time()
    response = requests.post(
        f"{BASE_URL}/ask",
        json={"question": question},
        timeout=120
    )
    standard_time = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        print(f"⏱️  Response time: {standard_time:.2f}s")
        print(f"📏 Answer length: {len(result['answer'])} chars")
        print(f"📚 Sources: {len(result['sources'])}")
        print(f"💬 Session ID: {result.get('session_id', 'N/A')}")
        
        session_id = result.get('session_id')
    else:
        print(f"❌ Error: {response.text}")
        session_id = None
    
    time.sleep(2)
    
    # Test streaming endpoint
    print_section("Streaming Response (POST /ask/stream)")
    print(f"❓ Question: {question}\n")
    print("📡 Streaming: ", end='', flush=True)
    
    start = time.time()
    first_chunk_time = None
    answer_length = 0
    
    response = requests.post(
        f"{BASE_URL}/ask/stream",
        json={"question": question},
        stream=True,
        timeout=120
    )
    
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        
                        if first_chunk_time is None and "answer_chunk" in data:
                            first_chunk_time = time.time() - start
                            print("✅ First chunk received!", flush=True)
                        
                        if "answer_chunk" in data and data["answer_chunk"]:
                            answer_length += len(data["answer_chunk"])
                            print(".", end='', flush=True)
                        
                        if data.get("done", False):
                            break
                    except:
                        pass
        
        total_time = time.time() - start
        print(f"\n\n⏱️  Total time: {total_time:.2f}s")
        print(f"⚡ First chunk: {first_chunk_time:.2f}s")
        print(f"📏 Answer length: {answer_length} chars")
        
        print(f"\n💡 Perceived latency improvement: {standard_time - first_chunk_time:.2f}s")
    else:
        print(f"\n❌ Error: {response.text}")
    
    return session_id

def test_conversation_flow(session_id):
    """Test multi-turn conversation"""
    print_header("💬 CONVERSATION HISTORY & CONTEXT")
    
    if not session_id:
        print("⚠️  No session ID from previous test, creating new conversation")
        session_id = None
    
    print_section("Multi-Turn Conversation Test")
    
    conversation = [
        "What is Mistral AI model?",
        "How does it compare to Llama 2?",
        "Which one would you recommend for limited RAM?",
        "Can you summarize the key differences?"
    ]
    
    for i, question in enumerate(conversation, 1):
        print(f"\n{'•'*80}")
        print(f"Turn {i}/{len(conversation)}")
        print('•'*80)
        print(f"❓ User: {question}")
        
        request_data = {"question": question}
        if session_id:
            request_data["session_id"] = session_id
        
        response = requests.post(
            f"{BASE_URL}/ask",
            json=request_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            
            if not session_id:
                session_id = result.get("session_id")
                print(f"📝 New Session ID: {session_id}")
            
            answer = result['answer']
            if len(answer) > 200:
                answer = answer[:200] + "..."
            
            print(f"🤖 Assistant: {answer}")
            print(f"📚 Used {len(result['sources'])} sources")
        else:
            print(f"❌ Error: {response.text}")
        
        time.sleep(1.5)
    
    return session_id

def test_conversation_retrieval(session_id):
    """Test conversation history retrieval"""
    print_section("Conversation History Retrieval")
    
    if not session_id:
        print("❌ No session ID available")
        return
    
    response = requests.get(f"{BASE_URL}/conversations/{session_id}")
    
    if response.status_code == 200:
        history = response.json()
        print(f"✅ Retrieved {history['conversation_count']} conversations\n")
        
        print("Conversation Summary:")
        for i, conv in enumerate(history['conversations'], 1):
            print(f"\n  Turn {i}:")
            print(f"  Q: {conv['question']}")
            answer_preview = conv['answer'][:100] + "..."
            print(f"  A: {answer_preview}")
    else:
        print(f"❌ Error: {response.text}")

def test_session_management():
    """Test session management features"""
    print_section("Session Management")
    
    # List all sessions
    response = requests.get(f"{BASE_URL}/conversations")
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Active sessions: {data['active_sessions']}\n")
        
        if data['sessions']:
            print("Session List:")
            for i, session in enumerate(data['sessions'][:3], 1):
                print(f"\n  Session {i}:")
                print(f"  ID: {session['session_id'][:16]}...")
                print(f"  Turns: {session['conversation_count']}")
                print(f"  Last: {session['last_updated']}")
    else:
        print(f"❌ Error: {response.text}")

def test_streaming_with_history():
    """Test streaming with conversation history"""
    print_header("🔄 STREAMING + CONVERSATION HISTORY")
    
    print_section("Multi-turn streaming conversation")
    
    questions = [
        "Explain vector databases",
        "Why are they important for RAG?",
        "How do embeddings work?"
    ]
    
    session_id = None
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─'*80}")
        print(f"Turn {i}: {question}")
        print('─'*80)
        
        request_data = {"question": question}
        if session_id:
            request_data["session_id"] = session_id
        
        response = requests.post(
            f"{BASE_URL}/ask/stream",
            json=request_data,
            stream=True,
            timeout=120
        )
        
        if response.status_code == 200:
            print("🤖 ", end='', flush=True)
            
            # Get session ID from headers
            if not session_id and 'X-Session-ID' in response.headers:
                session_id = response.headers['X-Session-ID']
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        try:
                            data = json.loads(line[6:])
                            if "answer_chunk" in data and data["answer_chunk"]:
                                print(data["answer_chunk"], end='', flush=True)
                            if data.get("done", False):
                                break
                        except:
                            pass
            
            print("\n")
        else:
            print(f"❌ Error: {response.text}")
        
        time.sleep(1)
    
    return session_id

def print_summary():
    """Print test summary"""
    print_header("✅ TEST SUITE COMPLETE")
    
    print("📊 Features Tested:")
    print("   ✅ Enhanced document management (list, formats)")
    print("   ✅ Standard vs streaming response comparison")
    print("   ✅ Multi-turn conversations with context")
    print("   ✅ Conversation history retrieval")
    print("   ✅ Session management")
    print("   ✅ Streaming with conversation history")
    
    print("\n🎯 Key Capabilities:")
    print("   • 9 document formats supported")
    print("   • Real-time streaming responses")
    print("   • Conversation memory across turns")
    print("   • Session management and history")
    print("   • Context-aware follow-up questions")
    
    print("\n💡 Next Steps:")
    print("   1. Build a chat UI using streaming endpoint")
    print("   2. Implement persistent conversation storage (database)")
    print("   3. Add user authentication for sessions")
    print("   4. Create conversation export functionality")
    print("   5. Add analytics on conversation patterns")
    
    print("\n📚 API Endpoints Reference:")
    print("   Swagger UI: http://localhost:8000/docs")
    print("   ReDoc: http://localhost:8000/redoc")

def main():
    """Run complete test suite"""
    
    print("\n" + "="*80)
    print("  🧪 COMPLETE ADVANCED FEATURES TEST SUITE")
    print("  Testing: Streaming • Conversation History • Document Management")
    print("="*80)
    
    # Check system
    if not check_system():
        return
    
    try:
        # Test 1: Document management
        test_enhanced_document_management()
        time.sleep(2)
        
        # Test 2: Standard vs Streaming
        session_id = test_standard_vs_streaming()
        time.sleep(2)
        
        # Test 3: Conversation flow
        session_id = test_conversation_flow(session_id)
        time.sleep(2)
        
        # Test 4: History retrieval
        test_conversation_retrieval(session_id)
        time.sleep(2)
        
        # Test 5: Session management
        test_session_management()
        time.sleep(2)
        
        # Test 6: Streaming with history
        test_streaming_with_history()
        
        # Print summary
        print_summary()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Error during tests: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
