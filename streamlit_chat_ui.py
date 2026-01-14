"""
Streamlit Chat UI for RAG API
Beautiful, easy-to-use chat interface with streaming support
"""

import streamlit as st
import requests
import json
import time
from datetime import datetime

# Configuration
API_BASE = "http://localhost:8000"

# Page config
st.set_page_config(
    page_title="RAG Chat Assistant",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 10px;
        margin-bottom: 1rem;
        display: flex;
        flex-direction: column;
    }
    .user-message {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        margin-left: 20%;
    }
    .assistant-message {
        background: white;
        color: #2d3748;
        margin-right: 20%;
        box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    }
    .message-meta {
        font-size: 0.8rem;
        opacity: 0.7;
        margin-top: 0.5rem;
    }
    .sources-box {
        background: #f7f9fc;
        padding: 1rem;
        border-radius: 8px;
        margin-top: 1rem;
        font-size: 0.9rem;
    }
    .status-connected {
        color: #48bb78;
    }
    .status-error {
        color: #f56565;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "session_id" not in st.session_state:
    st.session_state.session_id = None
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = []

# Sidebar
with st.sidebar:
    st.markdown("## 🤖 RAG Chat Assistant")
    st.markdown("---")
    
    # Status check
    try:
        response = requests.get(f"{API_BASE}/health", timeout=2)
        if response.status_code == 200:
            health = response.json()
            st.markdown("### Status")
            st.markdown(f"<span class='status-connected'>🟢 Connected</span>", unsafe_allow_html=True)
            st.info(f"📚 Documents: {health['documents_count']}")
            
            if st.session_state.session_id:
                st.success(f"Session: {st.session_state.session_id[:8]}...")
        else:
            st.markdown("<span class='status-error'>🔴 Server Error</span>", unsafe_allow_html=True)
    except:
        st.markdown("<span class='status-error'>🔴 Disconnected</span>", unsafe_allow_html=True)
        st.error("Cannot connect to server at http://localhost:8000")
    
    st.markdown("---")
    
    # Settings
    st.markdown("### ⚙️ Settings")
    use_streaming = st.checkbox("Enable Streaming", value=True, help="Show responses in real-time")
    show_sources = st.checkbox("Show Sources", value=True, help="Display document sources")
    
    st.markdown("---")
    
    # Actions
    st.markdown("### 🎯 Actions")
    
    if st.button("🆕 New Conversation", use_container_width=True):
        st.session_state.messages = []
        st.session_state.session_id = None
        st.session_state.conversation_history = []
        st.rerun()
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        if st.session_state.messages:
            st.session_state.messages = []
            st.rerun()
    
    if st.button("📜 View History", use_container_width=True):
        if st.session_state.session_id:
            try:
                response = requests.get(f"{API_BASE}/conversations/{st.session_state.session_id}")
                if response.status_code == 200:
                    history = response.json()
                    st.session_state.conversation_history = history['conversations']
                    st.success(f"Loaded {len(st.session_state.conversation_history)} conversations")
            except Exception as e:
                st.error(f"Error loading history: {str(e)}")
    
    if st.button("💾 Export Chat", use_container_width=True):
        if st.session_state.messages:
            transcript = "RAG Chat Transcript\n"
            transcript += "=" * 50 + "\n\n"
            
            for msg in st.session_state.messages:
                role = "User" if msg["role"] == "user" else "Assistant"
                transcript += f"{role}: {msg['content']}\n\n"
            
            st.download_button(
                label="Download Transcript",
                data=transcript,
                file_name=f"chat-{datetime.now().strftime('%Y%m%d-%H%M%S')}.txt",
                mime="text/plain"
            )
    
    st.markdown("---")
    st.markdown("""
    ### 💡 Features
    - 🔄 Real-time streaming
    - 💬 Conversation history
    - 📚 Document sources
    - 🔒 100% Local & Private
    - 🚀 Powered by Ollama
    """)

# Main chat area
st.markdown("""
<div class='main-header'>
    <h1>🤖 RAG Chat Assistant</h1>
    <p>Ask me anything about your documents!</p>
</div>
""", unsafe_allow_html=True)

# Display chat messages
for message in st.session_state.messages:
    role_class = "user-message" if message["role"] == "user" else "assistant-message"
    avatar = "👤" if message["role"] == "user" else "🤖"
    
    st.markdown(f"""
    <div class='chat-message {role_class}'>
        <div><strong>{avatar} {message['role'].title()}</strong></div>
        <div style='margin-top: 0.5rem;'>{message['content']}</div>
        {f"<div class='sources-box'>📚 Sources: {message.get('sources', 'N/A')}</div>" if show_sources and 'sources' in message else ""}
    </div>
    """, unsafe_allow_html=True)

# Chat input
question = st.chat_input("Type your question here...")

if question:
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": question
    })
    
    # Create placeholder for assistant response
    with st.spinner("Thinking..."):
        try:
            if use_streaming:
                # Streaming response
                response = requests.post(
                    f"{API_BASE}/ask/stream",
                    json={
                        "question": question,
                        "session_id": st.session_state.session_id
                    },
                    stream=True,
                    timeout=120
                )
                
                if response.status_code == 200:
                    # Get session ID
                    if not st.session_state.session_id and 'X-Session-ID' in response.headers:
                        st.session_state.session_id = response.headers['X-Session-ID']
                    
                    full_answer = ""
                    sources = []
                    
                    # Create a placeholder for streaming
                    message_placeholder = st.empty()
                    
                    for line in response.iter_lines():
                        if line:
                            line = line.decode('utf-8')
                            if line.startswith('data: '):
                                try:
                                    data = json.loads(line[6:])
                                    
                                    if 'sources' in data and data['sources']:
                                        sources = data['sources']
                                    
                                    if 'answer_chunk' in data and data['answer_chunk']:
                                        full_answer += data['answer_chunk']
                                        
                                        # Update placeholder with current answer
                                        message_placeholder.markdown(f"""
                                        <div class='chat-message assistant-message'>
                                            <div><strong>🤖 Assistant</strong></div>
                                            <div style='margin-top: 0.5rem;'>{full_answer}▌</div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                    
                                    if data.get('done', False):
                                        break
                                except:
                                    pass
                    
                    # Add final message
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": full_answer,
                        "sources": len(sources)
                    })
                    
                    message_placeholder.empty()
                else:
                    st.error(f"Error: {response.status_code}")
            
            else:
                # Standard response (non-streaming)
                response = requests.post(
                    f"{API_BASE}/ask",
                    json={
                        "question": question,
                        "session_id": st.session_state.session_id
                    },
                    timeout=120
                )
                
                if response.status_code == 200:
                    result = response.json()
                    
                    # Store session ID
                    if not st.session_state.session_id:
                        st.session_state.session_id = result.get('session_id')
                    
                    # Add assistant message
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": result['answer'],
                        "sources": len(result.get('sources', []))
                    })
                else:
                    st.error(f"Error: {response.status_code} - {response.text}")
        
        except Exception as e:
            st.error(f"Error: {str(e)}")
            st.info("Make sure the server is running on http://localhost:8000")
    
    # Rerun to show new messages
    st.rerun()

# Welcome message if no messages
if not st.session_state.messages:
    st.markdown("""
    <div class='chat-message assistant-message'>
        <div><strong>🤖 Assistant</strong></div>
        <div style='margin-top: 0.5rem;'>
            Hello! I'm your local RAG assistant. I can answer questions about your documents 
            using AI that runs entirely on your computer.
            <br><br>
            <strong>Try asking:</strong>
            <ul>
                <li>What is RAG and how does it work?</li>
                <li>Compare the available AI models</li>
                <li>What are the benefits of local AI?</li>
            </ul>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: white; padding: 1rem;'>
    💡 Powered by Ollama • 100% Local • No data leaves your computer
</div>
""", unsafe_allow_html=True)
