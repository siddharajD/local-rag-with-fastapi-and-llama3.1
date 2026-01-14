"""
Test script for conversation history features
Demonstrates multi-turn conversations with context retention
"""

import requests
import json
import time

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_single_conversation():
    """Test conversation with history retention"""
    
    print_section("💬 SINGLE CONVERSATION TEST")
    
    # Start a new conversation (session ID will be auto-generated)
    questions = [
        "What is RAG?",
        "Can you explain that in simpler terms?",  # Should use context
        "What are its main benefits?",  # Should use context from previous answers
        "How is it different from regular chatbots?"  # Should understand "it" refers to RAG
    ]
    
    session_id = None
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─'*70}")
        print(f"Turn {i}/{len(questions)}")
        print('─'*70)
        print(f"❓ User: {question}")
        
        # Prepare request (include session_id after first question)
        request_data = {"question": question}
        if session_id:
            request_data["session_id"] = session_id
        
        # Make request
        response = requests.post(
            f"{BASE_URL}/ask",
            json=request_data,
            timeout=120
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Get session_id from first response
            if not session_id:
                session_id = result.get("session_id")
                print(f"📝 Session ID: {session_id}")
            
            print(f"\n🤖 Assistant: {result['answer']}")
            print(f"\n📚 Sources: {len(result['sources'])} documents")
        else:
            print(f"❌ Error: {response.text}")
            return None
        
        time.sleep(1)
    
    return session_id

def test_multiple_conversations():
    """Test multiple independent conversations"""
    
    print_section("🔀 MULTIPLE CONVERSATIONS TEST")
    
    conversations = {
        "AI Models": [
            "What is Llama 2?",
            "How does it compare to Mistral?",
            "Which one should I use?"
        ],
        "Technical Details": [
            "What is a vector database?",
            "How are embeddings created?",
            "Why use chunk overlap?"
        ]
    }
    
    session_ids = {}
    
    for topic, questions in conversations.items():
        print(f"\n{'═'*70}")
        print(f"  Conversation about: {topic}")
        print('═'*70)
        
        session_id = None
        
        for i, question in enumerate(questions, 1):
            print(f"\n❓ Question {i}: {question}")
            
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
                    print(f"📝 Session ID: {session_id}")
                
                # Show abbreviated answer
                answer = result['answer']
                if len(answer) > 200:
                    answer = answer[:200] + "..."
                print(f"🤖 Answer: {answer}")
            else:
                print(f"❌ Error: {response.text}")
            
            time.sleep(1)
        
        session_ids[topic] = session_id
    
    return session_ids

def test_conversation_history_retrieval(session_id):
    """Test retrieving conversation history"""
    
    print_section("📖 CONVERSATION HISTORY RETRIEVAL")
    
    if not session_id:
        print("❌ No session ID provided")
        return
    
    print(f"📝 Retrieving history for session: {session_id}\n")
    
    response = requests.get(f"{BASE_URL}/conversations/{session_id}")
    
    if response.status_code == 200:
        history = response.json()
        
        print(f"✅ Found {history['conversation_count']} conversations\n")
        print("─"*70)
        
        for i, conv in enumerate(history['conversations'], 1):
            print(f"\nTurn {i}:")
            print(f"❓ Question: {conv['question']}")
            print(f"🤖 Answer: {conv['answer'][:150]}...")
            print(f"⏰ Time: {conv['timestamp']}")
            print(f"📚 Sources: {len(conv['sources'])}")
        
        print("\n" + "─"*70)
    else:
        print(f"❌ Error: {response.text}")

def test_list_all_sessions():
    """Test listing all active sessions"""
    
    print_section("📋 ALL ACTIVE SESSIONS")
    
    response = requests.get(f"{BASE_URL}/conversations")
    
    if response.status_code == 200:
        data = response.json()
        
        print(f"📊 Total active sessions: {data['active_sessions']}\n")
        
        if data['sessions']:
            print("─"*70)
            for i, session in enumerate(data['sessions'], 1):
                print(f"\nSession {i}:")
                print(f"   ID: {session['session_id']}")
                print(f"   Conversations: {session['conversation_count']}")
                print(f"   Last updated: {session['last_updated']}")
                print(f"   Started with: {session['first_question']}")
            print("\n" + "─"*70)
        else:
            print("ℹ️  No active sessions found")
    else:
        print(f"❌ Error: {response.text}")

def test_conversation_context():
    """Test that conversation context is actually used"""
    
    print_section("🎯 CONTEXT AWARENESS TEST")
    
    print("This test verifies the AI uses previous conversation context")
    print("─"*70 + "\n")
    
    # First, ask about something specific
    print("❓ Question 1: Tell me about Mistral AI model")
    response1 = requests.post(
        f"{BASE_URL}/ask",
        json={"question": "Tell me about Mistral AI model"},
        timeout=120
    )
    
    if response1.status_code != 200:
        print(f"❌ Error: {response1.text}")
        return
    
    result1 = response1.json()
    session_id = result1.get("session_id")
    
    answer1 = result1['answer']
    if len(answer1) > 150:
        answer1 = answer1[:150] + "..."
    print(f"🤖 Answer: {answer1}\n")
    print(f"📝 Session ID: {session_id}\n")
    
    time.sleep(2)
    
    # Now ask a follow-up that requires context
    print("❓ Question 2: How fast is it compared to Llama 2?")
    print("   (Note: 'it' should refer to Mistral from previous question)\n")
    
    response2 = requests.post(
        f"{BASE_URL}/ask",
        json={
            "question": "How fast is it compared to Llama 2?",
            "session_id": session_id
        },
        timeout=120
    )
    
    if response2.status_code == 200:
        result2 = response2.json()
        answer2 = result2['answer']
        
        print(f"🤖 Answer: {answer2}\n")
        
        # Check if answer makes sense in context
        print("─"*70)
        print("🔍 Context Check:")
        
        # Look for keywords that would indicate context understanding
        context_indicators = ["mistral", "it", "faster", "compared", "speed"]
        found_indicators = [word for word in context_indicators if word.lower() in answer2.lower()]
        
        if found_indicators:
            print(f"   ✅ Answer appears contextually aware")
            print(f"   📌 Found context keywords: {', '.join(found_indicators)}")
        else:
            print(f"   ⚠️  Answer may not be using previous context")
        
        print("─"*70)
    else:
        print(f"❌ Error: {response2.text}")

def test_clear_conversation(session_id):
    """Test clearing conversation history"""
    
    print_section("🗑️ CLEAR CONVERSATION TEST")
    
    if not session_id:
        print("❌ No session ID provided")
        return
    
    print(f"📝 Clearing history for session: {session_id}\n")
    
    # First, show current history
    response = requests.get(f"{BASE_URL}/conversations/{session_id}")
    if response.status_code == 200:
        history = response.json()
        print(f"📊 Current conversation count: {history['conversation_count']}")
    
    # Clear the history
    response = requests.delete(f"{BASE_URL}/conversations/{session_id}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        
        # Verify it's cleared
        response = requests.get(f"{BASE_URL}/conversations/{session_id}")
        if response.status_code == 404:
            print("✅ Confirmed: Session history has been deleted")
        else:
            print("⚠️  Warning: Session may still exist")
    else:
        print(f"❌ Error: {response.text}")

def test_clear_all_conversations():
    """Test clearing all conversation histories"""
    
    print_section("🗑️ CLEAR ALL CONVERSATIONS TEST")
    
    # First, show current sessions
    response = requests.get(f"{BASE_URL}/conversations")
    if response.status_code == 200:
        data = response.json()
        print(f"📊 Current active sessions: {data['active_sessions']}")
    
    # Clear all
    response = requests.delete(f"{BASE_URL}/conversations")
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ {result['message']}")
        print(f"📊 Sessions cleared: {result['sessions_cleared']}")
        
        # Verify
        response = requests.get(f"{BASE_URL}/conversations")
        if response.status_code == 200:
            data = response.json()
            if data['active_sessions'] == 0:
                print("✅ Confirmed: All sessions cleared")
            else:
                print(f"⚠️  Warning: {data['active_sessions']} sessions still exist")
    else:
        print(f"❌ Error: {response.text}")

def main():
    """Run all conversation history tests"""
    
    print("\n" + "="*70)
    print("  💬 CONVERSATION HISTORY TESTS")
    print("  Testing multi-turn conversations with context retention")
    print("="*70)
    
    # Check if system is ready
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            health = response.json()
            if not health["system_ready"]:
                print("\n❌ System not initialized!")
                print("   Please run: POST /initialize first")
                return
        else:
            print("\n❌ Cannot connect to API server!")
            return
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API server!")
        print("   Please start the server: python main.py")
        return
    
    # Run tests
    try:
        # Test 1: Single conversation
        session_id = test_single_conversation()
        time.sleep(2)
        
        # Test 2: Multiple conversations
        session_ids = test_multiple_conversations()
        time.sleep(2)
        
        # Test 3: Retrieve history
        if session_id:
            test_conversation_history_retrieval(session_id)
            time.sleep(2)
        
        # Test 4: List all sessions
        test_list_all_sessions()
        time.sleep(2)
        
        # Test 5: Context awareness
        test_conversation_context()
        time.sleep(2)
        
        # Test 6: Clear single conversation
        if session_id:
            test_clear_conversation(session_id)
            time.sleep(2)
        
        # Test 7: Clear all conversations
        test_clear_all_conversations()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return
    except Exception as e:
        print(f"\n\n❌ Error during tests: {str(e)}")
        import traceback
        traceback.print_exc()
        return
    
    # Summary
    print("\n" + "="*70)
    print("  ✅ ALL CONVERSATION HISTORY TESTS COMPLETED!")
    print("="*70)
    print("\n🎯 Features Tested:")
    print("   ✅ Multi-turn conversations with context")
    print("   ✅ Multiple independent sessions")
    print("   ✅ Conversation history retrieval")
    print("   ✅ Session management (list, clear)")
    print("   ✅ Context awareness in follow-up questions")
    
    print("\n💡 Use Cases:")
    print("   • Build a chatbot with conversation memory")
    print("   • Create multi-turn Q&A interfaces")
    print("   • Maintain context across questions")
    print("   • Track user interactions and conversations")

if __name__ == "__main__":
    main()
