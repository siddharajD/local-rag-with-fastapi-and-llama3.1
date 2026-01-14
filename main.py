"""
FastAPI application for Local RAG System
Provides REST API endpoints for document management and question answering
Includes: Streaming responses, conversation history, document management
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware  # ← THIS IS THE NEW LINE
from pydantic import BaseModel
from typing import Optional, List, Dict
import os
import shutil
from datetime import datetime
import json
import uuid

from rag_engine import LocalRAGSystem

# Initialize FastAPI app
app = FastAPI(
    title="Local RAG API",
    description="🚀 Retrieval-Augmented Generation API using Ollama (100% Local & Free!)",
    version="1.0.0",
    docs_url="/docs",  # Swagger UI at /docs
    redoc_url="/redoc"  # ReDoc at /redoc
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize RAG system (global variable)
rag_system = LocalRAGSystem(model_name="llama3.1")
system_ready = False

# Conversation history storage (in-memory)
# Format: {session_id: [{"question": "", "answer": "", "timestamp": "", "sources": []}]}
conversation_store: Dict[str, List[Dict]] = {}

# Pydantic models for request/response
class QuestionRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What is FastAPI?",
                "session_id": "optional-session-id"
            }
        }

class AnswerResponse(BaseModel):
    question: str
    answer: str
    sources: list
    session_id: Optional[str] = None
    
class StatusResponse(BaseModel):
    status: str
    system_ready: bool
    documents_count: int
    timestamp: str

class ConversationHistoryResponse(BaseModel):
    session_id: str
    conversation_count: int
    conversations: List[Dict]


# ==================== API ENDPOINTS ====================

@app.get("/", tags=["General"])
def root():
    """
    🏠 Welcome endpoint - Shows available API routes
    """
    return {
        "message": "🚀 Welcome to Local RAG API!",
        "description": "Powered by Ollama - 100% Local & Free",
        "version": "2.0.0 - Advanced Features",
        "new_features": [
            "🔄 Streaming responses",
            "💬 Conversation history",
            "📚 Enhanced document management"
        ],
        "documentation": {
            "swagger_ui": "/docs",
            "redoc": "/redoc"
        },
        "endpoints": {
            "GET /": "This welcome message",
            "GET /health": "Check system health",
            "GET /supported-formats": "List supported file types",
            "POST /upload": "Upload a document",
            "GET /documents": "List all documents",
            "DELETE /documents/{filename}": "Delete a document",
            "POST /initialize": "Process documents and prepare system",
            "POST /ask": "Ask a question (standard response)",
            "POST /ask/stream": "Ask a question (streaming response)",
            "GET /conversations/{session_id}": "Get conversation history",
            "DELETE /conversations/{session_id}": "Clear conversation history",
            "DELETE /reset": "Clear all documents and reset system"
        },
        "workflow": [
            "1. Upload documents using POST /upload",
            "2. Initialize system using POST /initialize",
            "3. Ask questions using POST /ask or POST /ask/stream",
            "4. View conversation history using GET /conversations/{session_id}"
        ]
    }


@app.get("/health", response_model=StatusResponse, tags=["General"])
def health_check():
    """
    🏥 Check system health and status
    """
    docs_folder = "./documents"
    doc_count = len(os.listdir(docs_folder)) if os.path.exists(docs_folder) else 0
    
    return StatusResponse(
        status="ready" if system_ready else "not_initialized",
        system_ready=system_ready,
        documents_count=doc_count,
        timestamp=datetime.now().isoformat()
    )


@app.get("/supported-formats", tags=["General"])
def get_supported_formats():
    """
    📋 List all supported file formats
    """
    return {
        "supported_formats": {
            "documents": {
                "PDF": ".pdf",
                "Word": ".docx",
                "Text": ".txt",
                "Markdown": ".md",
                "HTML": ".html"
            },
            "spreadsheets": {
                "Excel": ".xlsx, .xls",
                "CSV": ".csv"
            },
            "presentations": {
                "PowerPoint": ".pptx, .ppt"
            }
        },
        "total_formats": 9,
        "note": "Upload any of these file types using POST /upload"
    }


@app.get("/documents", tags=["Document Management"])
def list_documents():
    """
    📚 List all uploaded documents with details
    """
    docs_folder = "./documents"
    
    if not os.path.exists(docs_folder):
        return {"documents": [], "count": 0}
    
    files = []
    for filename in os.listdir(docs_folder):
        file_path = os.path.join(docs_folder, filename)
        
        if os.path.isfile(file_path) and not filename.startswith('.'):
            file_ext = os.path.splitext(filename)[1].lower()
            file_size = os.path.getsize(file_path)
            
            files.append({
                "name": filename,
                "type": file_ext,
                "size_kb": round(file_size / 1024, 2),
                "size_mb": round(file_size / (1024 * 1024), 2),
                "modified": datetime.fromtimestamp(
                    os.path.getmtime(file_path)
                ).isoformat()
            })
    
    # Sort by modified time (newest first)
    files.sort(key=lambda x: x['modified'], reverse=True)
    
    return {
        "documents": files,
        "count": len(files),
        "total_size_mb": round(sum(f['size_mb'] for f in files), 2)
    }


@app.delete("/documents/{filename}", tags=["Document Management"])
def delete_document(filename: str):
    """
    🗑️ Delete a specific document
    
    - **filename**: Name of the file to delete
    
    ⚠️ Warning: After deleting documents, you need to reinitialize the system.
    """
    file_path = os.path.join("./documents", filename)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document '{filename}' not found")
    
    try:
        os.remove(file_path)
        return {
            "message": f"✅ Document '{filename}' deleted successfully",
            "note": "Remember to call POST /initialize to update the system"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting document: {str(e)}"
        )


@app.post("/upload", tags=["Document Management"])
async def upload_document(file: UploadFile = File(...)):
    """
    📤 Upload a document (multiple formats supported)
    
    - **file**: Document file to upload
    
    Supported formats:
    - PDF (.pdf)
    - Text (.txt)
    - Word (.docx)
    - Excel (.xlsx, .xls)
    - CSV (.csv)
    - Markdown (.md)
    - HTML (.html)
    - PowerPoint (.pptx, .ppt)
    
    The file will be saved to the documents folder for processing.
    """
    
    # Validate file type
    allowed_extensions = ['.pdf', '.txt', '.docx', '.xlsx', '.xls', '.csv', '.md', '.html', '.pptx', '.ppt']
    file_ext = os.path.splitext(file.filename)[1].lower()
    
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not supported. Allowed types: {', '.join(allowed_extensions)}"
        )
    
    # Create documents folder if it doesn't exist
    os.makedirs("./documents", exist_ok=True)
    
    # Save file
    file_path = os.path.join("./documents", file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        file_size = os.path.getsize(file_path)
        
        return {
            "message": "✅ File uploaded successfully!",
            "filename": file.filename,
            "size_bytes": file_size,
            "size_kb": round(file_size / 1024, 2),
            "file_type": file_ext,
            "path": file_path,
            "next_step": "Call POST /initialize to process this document"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error uploading file: {str(e)}"
        )


@app.post("/initialize", tags=["System Management"])
async def initialize_system(background_tasks: BackgroundTasks):
    """
    🔄 Initialize RAG system with uploaded documents
    
    This endpoint:
    1. Loads all documents from the documents folder
    2. Splits them into chunks
    3. Creates embeddings using Ollama
    4. Stores them in Chroma vector database
    
    ⏱️ This may take 2-5 minutes depending on document size.
    """
    global system_ready
    
    # Check if documents exist
    docs_folder = "./documents"
    if not os.path.exists(docs_folder) or not os.listdir(docs_folder):
        raise HTTPException(
            status_code=400,
            detail="No documents found. Please upload documents first using POST /upload"
        )
    
    try:
        print("\n" + "="*50)
        print("🚀 Starting system initialization...")
        print("="*50 + "\n")
        
        # Initialize the RAG system
        success = rag_system.initialize_from_documents(docs_folder)
        
        if success:
            system_ready = True
            doc_count = len(os.listdir(docs_folder))
            
            print("\n" + "="*50)
            print("✅ System initialization complete!")
            print("="*50 + "\n")
            
            return {
                "message": "✅ System initialized successfully!",
                "status": "ready",
                "documents_processed": doc_count,
                "next_step": "You can now ask questions using POST /ask"
            }
        else:
            raise HTTPException(
                status_code=500,
                detail="Failed to initialize system. Check server logs for details."
            )
            
    except Exception as e:
        system_ready = False
        raise HTTPException(
            status_code=500,
            detail=f"Error during initialization: {str(e)}"
        )


@app.post("/ask", response_model=AnswerResponse, tags=["Question Answering"])
async def ask_question(request: QuestionRequest):
    """
    💬 Ask a question about your documents (standard response)
    
    - **question**: Your question in natural language
    - **session_id**: Optional session ID for conversation history
    
    The system will:
    1. Retrieve conversation history if session_id provided
    2. Search for relevant information in your documents
    3. Use Ollama LLM to generate an answer
    4. Return the answer with source citations
    5. Store in conversation history if session_id provided
    """
    
    if not system_ready:
        raise HTTPException(
            status_code=400,
            detail="System not initialized. Please call POST /initialize first."
        )
    
    try:
        # Generate or use provided session ID
        session_id = request.session_id or str(uuid.uuid4())
        
        # Get conversation history if exists
        history = conversation_store.get(session_id, [])
        
        # Ask the question with conversation context
        result = rag_system.ask(request.question, conversation_history=history)
        
        if "error" in result:
            raise HTTPException(status_code=400, detail=result["error"])
        
        # Store in conversation history
        conversation_entry = {
            "question": result["question"],
            "answer": result["answer"],
            "sources": result["sources"],
            "timestamp": datetime.now().isoformat()
        }
        
        if session_id not in conversation_store:
            conversation_store[session_id] = []
        conversation_store[session_id].append(conversation_entry)
        
        # Add session_id to response
        result["session_id"] = session_id
        
        return AnswerResponse(**result)
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error processing question: {str(e)}"
        )


@app.post("/ask/stream", tags=["Question Answering"])
async def ask_question_stream(request: QuestionRequest):
    """
    🔄 Ask a question with streaming response (real-time)
    
    - **question**: Your question in natural language
    - **session_id**: Optional session ID for conversation history
    
    Returns a stream of JSON chunks as the answer is generated.
    Perfect for showing real-time responses in a chat interface!
    
    Response format (streamed):
    ```
    {"question": "...", "sources": [...], "answer_chunk": "", "done": false}
    {"answer_chunk": "First", "done": false}
    {"answer_chunk": " few", "done": false}
    {"answer_chunk": " words", "done": false}
    ...
    {"done": true}
    ```
    """
    
    if not system_ready:
        raise HTTPException(
            status_code=400,
            detail="System not initialized. Please call POST /initialize first."
        )
    
    # Generate or use provided session ID
    session_id = request.session_id or str(uuid.uuid4())
    
    # Get conversation history if exists
    history = conversation_store.get(session_id, [])
    
    async def generate():
        """Generator function for streaming response"""
        full_answer = ""
        sources = []
        
        try:
            for chunk_json in rag_system.ask_stream(request.question, conversation_history=history):
                chunk_data = json.loads(chunk_json)
                
                # Store sources when we get them
                if "sources" in chunk_data:
                    sources = chunk_data["sources"]
                
                # Accumulate answer chunks
                if "answer_chunk" in chunk_data and chunk_data["answer_chunk"]:
                    full_answer += chunk_data["answer_chunk"]
                
                # Yield the chunk
                yield f"data: {chunk_json}\n\n"
                
                # If done, store in conversation history
                if chunk_data.get("done", False):
                    if full_answer and session_id:
                        conversation_entry = {
                            "question": request.question,
                            "answer": full_answer,
                            "sources": sources,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        if session_id not in conversation_store:
                            conversation_store[session_id] = []
                        conversation_store[session_id].append(conversation_entry)
                    break
                    
        except Exception as e:
            error_json = json.dumps({"error": str(e), "done": True})
            yield f"data: {error_json}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Session-ID": session_id
        }
    )


@app.get("/conversations", tags=["Conversation History"])
def list_all_sessions():
    """
    📜 List all conversation sessions
    
    Returns a list of all active session IDs with metadata.
    """
    sessions = []
    
    for session_id, history in conversation_store.items():
        if history:
            sessions.append({
                "session_id": session_id,
                "conversation_count": len(history),
                "last_updated": history[-1]["timestamp"],
                "first_question": history[0]["question"][:50] + "..."
            })
    
    return {
        "active_sessions": len(sessions),
        "sessions": sessions
    }


@app.get("/conversations/{session_id}", response_model=ConversationHistoryResponse, tags=["Conversation History"])
def get_conversation_history(session_id: str):
    """
    📖 Get conversation history for a session
    
    - **session_id**: The session ID to retrieve history for
    
    Returns all questions and answers for this conversation.
    """
    
    if session_id not in conversation_store:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found"
        )
    
    history = conversation_store[session_id]
    
    return ConversationHistoryResponse(
        session_id=session_id,
        conversation_count=len(history),
        conversations=history
    )


@app.delete("/conversations/{session_id}", tags=["Conversation History"])
def clear_conversation_history(session_id: str):
    """
    🗑️ Clear conversation history for a session
    
    - **session_id**: The session ID to clear
    
    Deletes all conversation history for this session.
    """
    
    if session_id not in conversation_store:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found"
        )
    
    del conversation_store[session_id]
    
    return {
        "message": f"✅ Conversation history for session '{session_id}' cleared",
        "session_id": session_id
    }


@app.delete("/conversations", tags=["Conversation History"])
def clear_all_conversations():
    """
    🗑️ Clear all conversation histories
    
    ⚠️ Warning: This will delete all conversation histories for all sessions.
    """
    
    count = len(conversation_store)
    conversation_store.clear()
    
    return {
        "message": f"✅ Cleared {count} conversation session(s)",
        "sessions_cleared": count
    }


@app.delete("/reset", tags=["System Management"])
async def reset_system():
    """
    🗑️ Reset system and clear all documents
    
    ⚠️ Warning: This will delete all uploaded documents and reset the system.
    """
    global system_ready
    
    try:
        # Delete documents folder
        if os.path.exists("./documents"):
            shutil.rmtree("./documents")
            os.makedirs("./documents")
        
        # Delete vector database
        if os.path.exists("./chroma_db"):
            shutil.rmtree("./chroma_db")
        
        # Reset system
        system_ready = False
        
        return {
            "message": "✅ System reset successfully!",
            "status": "reset",
            "note": "You can now upload new documents"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error resetting system: {str(e)}"
        )


# Run the application
if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*60)
    print("🚀 Starting Local RAG API Server")
    print("="*60)
    print("\n📍 Server will be available at:")
    print("   • API: http://localhost:8000")
    print("   • Swagger UI: http://localhost:8000/docs")
    print("   • ReDoc: http://localhost:8000/redoc")
    print("\n💡 Tip: Use Swagger UI for interactive testing!")
    print("="*60 + "\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
