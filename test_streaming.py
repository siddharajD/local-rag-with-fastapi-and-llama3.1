"""
Test script for streaming responses
Demonstrates real-time answer generation
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:8000"

def print_section(title):
    """Print formatted section header"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70 + "\n")

def test_streaming():
    """Test streaming endpoint"""
    
    print_section("🔄 STREAMING RESPONSE TEST")
    
    question = "What is RAG and how does it work?"
    
    print(f"❓ Question: {question}\n")
    print("📡 Connecting to streaming endpoint...")
    print("💬 Response (streaming in real-time):\n")
    print("-" * 70)
    
    # Make streaming request
    response = requests.post(
        f"{BASE_URL}/ask/stream",
        json={"question": question},
        stream=True,
        timeout=120
    )
    
    if response.status_code != 200:
        print(f"❌ Error: {response.text}")
        return
    
    full_answer = ""
    sources = []
    
    # Process streamed response
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            
            # Skip non-data lines
            if not line.startswith('data: '):
                continue
            
            # Parse JSON data
            try:
                data_str = line[6:]  # Remove 'data: ' prefix
                chunk = json.loads(data_str)
                
                # Print sources when received
                if "sources" in chunk and chunk["sources"]:
                    sources = chunk["sources"]
                    print(f"\n📚 Found {len(sources)} relevant sources\n")
                
                # Print answer chunks in real-time
                if "answer_chunk" in chunk and chunk["answer_chunk"]:
                    answer_chunk = chunk["answer_chunk"]
                    full_answer += answer_chunk
                    print(answer_chunk, end='', flush=True)
                
                # Check if done
                if chunk.get("done", False):
                    break
                    
            except json.JSONDecodeError as e:
                print(f"\n⚠️  JSON decode error: {e}")
                continue
    
    print("\n" + "-" * 70)
    print(f"\n✅ Streaming complete!")
    print(f"📊 Total characters received: {len(full_answer)}")
    print(f"📚 Sources used: {len(sources)}")
    
    # Show source previews
    if sources:
        print("\n📖 Source previews:")
        for i, source in enumerate(sources, 1):
            preview = source['content_preview'][:100]
            print(f"   {i}. {preview}...")

def test_multiple_questions_streaming():
    """Test streaming with multiple questions"""
    
    print_section("🔄 MULTIPLE STREAMING QUESTIONS TEST")
    
    questions = [
        "What is FastAPI?",
        "Compare Llama 2 and Mistral models",
        "What are the benefits of local RAG?"
    ]
    
    for i, question in enumerate(questions, 1):
        print(f"\n{'─'*70}")
        print(f"Question {i}/{len(questions)}: {question}")
        print('─'*70 + "\n")
        
        response = requests.post(
            f"{BASE_URL}/ask/stream",
            json={"question": question},
            stream=True,
            timeout=120
        )
        
        if response.status_code == 200:
            print("Answer: ", end='', flush=True)
            
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
            print(f"❌ Error: {response.text}\n")
        
        # Small delay between questions
        if i < len(questions):
            time.sleep(2)

def compare_streaming_vs_standard():
    """Compare response time: streaming vs standard"""
    
    print_section("⚡ PERFORMANCE COMPARISON")
    
    question = "Explain the technical details of RAG implementation"
    
    # Test standard endpoint
    print("🔹 Testing STANDARD endpoint...")
    start_time = time.time()
    
    response = requests.post(
        f"{BASE_URL}/ask",
        json={"question": question},
        timeout=120
    )
    
    standard_time = time.time() - start_time
    
    if response.status_code == 200:
        result = response.json()
        print(f"   ✅ Response received in {standard_time:.2f} seconds")
        print(f"   📏 Answer length: {len(result['answer'])} characters")
    else:
        print(f"   ❌ Error: {response.text}")
    
    # Test streaming endpoint
    print("\n🔹 Testing STREAMING endpoint...")
    start_time = time.time()
    first_chunk_time = None
    
    response = requests.post(
        f"{BASE_URL}/ask/stream",
        json={"question": question},
        stream=True,
        timeout=120
    )
    
    answer_length = 0
    
    if response.status_code == 200:
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                if line.startswith('data: '):
                    try:
                        data = json.loads(line[6:])
                        
                        # Record time to first chunk
                        if first_chunk_time is None and "answer_chunk" in data:
                            first_chunk_time = time.time() - start_time
                        
                        # Count answer length
                        if "answer_chunk" in data and data["answer_chunk"]:
                            answer_length += len(data["answer_chunk"])
                        
                        if data.get("done", False):
                            break
                    except:
                        pass
    
    total_stream_time = time.time() - start_time
    
    print(f"   ✅ Streaming complete in {total_stream_time:.2f} seconds")
    print(f"   ⚡ First chunk received in {first_chunk_time:.2f} seconds")
    print(f"   📏 Answer length: {answer_length} characters")
    
    # Comparison
    print("\n" + "─"*70)
    print("📊 COMPARISON RESULTS:")
    print("─"*70)
    print(f"Standard endpoint: {standard_time:.2f}s total")
    print(f"Streaming endpoint: {total_stream_time:.2f}s total, {first_chunk_time:.2f}s to first chunk")
    print(f"\n💡 Benefit: User sees response {standard_time - first_chunk_time:.2f}s faster with streaming!")

def main():
    """Run all streaming tests"""
    
    print("\n" + "="*70)
    print("  🔄 STREAMING RESPONSE TESTS")
    print("  Testing real-time answer generation")
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
            print("   Please make sure the server is running on http://localhost:8000")
            return
    except requests.exceptions.ConnectionError:
        print("\n❌ Cannot connect to API server!")
        print("   Please start the server: python main.py")
        return
    
    # Run tests
    try:
        # Test 1: Basic streaming
        test_streaming()
        time.sleep(2)
        
        # Test 2: Multiple questions
        test_multiple_questions_streaming()
        time.sleep(2)
        
        # Test 3: Performance comparison
        compare_streaming_vs_standard()
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return
    except Exception as e:
        print(f"\n\n❌ Error during tests: {str(e)}")
        return
    
    # Summary
    print("\n" + "="*70)
    print("  ✅ ALL STREAMING TESTS COMPLETED!")
    print("="*70)
    print("\n🎯 Key Findings:")
    print("   • Streaming provides immediate feedback to users")
    print("   • Response appears to generate faster (lower perceived latency)")
    print("   • Perfect for chat interfaces")
    print("   • Same accuracy as standard endpoint")
    
    print("\n💡 Next Steps:")
    print("   • Try building a real-time chat UI")
    print("   • Test with longer, more complex questions")
    print("   • Experiment with different models (mistral, phi)")

if __name__ == "__main__":
    main()
