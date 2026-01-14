"""
Complete Working RAG Engine - Compatible with main.py
Fixed to include initialize_from_documents method
"""

import os
import json
from typing import List, Dict
import requests

# LangChain imports
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader, 
    TextLoader,
    Docx2txtLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    UnstructuredMarkdownLoader,
    UnstructuredHTMLLoader,
    UnstructuredPowerPointLoader
)
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document

class OllamaLLM:
    """Custom wrapper for Ollama LLM with streaming support"""
    
    def __init__(self, model_name: str = "llama2"):
        self.model_name = model_name
        self.base_url = "http://localhost:11434"
    
    def generate(self, prompt: str) -> str:
        """Generate text using Ollama (non-streaming)"""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            response = requests.post(url, json=payload, timeout=120)
            response.raise_for_status()
            return response.json()["response"]
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def generate_stream(self, prompt: str):
        """Generate text using Ollama with streaming"""
        url = f"{self.base_url}/api/generate"
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": True
        }
        
        try:
            response = requests.post(url, json=payload, stream=True, timeout=120)
            response.raise_for_status()
            
            for line in response.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                        if "response" in chunk:
                            yield chunk["response"]
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
                        
        except Exception as e:
            yield f"Error generating response: {str(e)}"


class LocalRAGSystem:
    """
    Local RAG System with improved retrieval
    Compatible with main.py API
    """
    
    def __init__(self, model_name: str = "llama3.1", documents_path: str = "./documents", 
                 db_path: str = "./chroma_db"):
        self.model_name = model_name
        self.documents_path = documents_path
        self.db_path = db_path
        self.llm = OllamaLLM(model_name)
        self.embeddings = OllamaEmbeddings(model=model_name)
        self.vectorstore = None
        self.documents = []
        
        # Ensure directories exist
        os.makedirs(documents_path, exist_ok=True)
        os.makedirs(db_path, exist_ok=True)
        
        print(f"🤖 RAG System initialized with model: {model_name}")
    
    def load_documents(self) -> List[Document]:
        """Load all documents from the documents directory"""
        documents = []
        
        print(f"📂 Loading documents from {self.documents_path}...")
        
        # Get all files in documents directory
        for filename in os.listdir(self.documents_path):
            if filename.startswith('.'):
                continue
                
            filepath = os.path.join(self.documents_path, filename)
            
            if not os.path.isfile(filepath):
                continue
            
            try:
                # Determine loader based on file extension
                ext = os.path.splitext(filename)[1].lower()
                
                if ext == '.pdf':
                    loader = PyPDFLoader(filepath)
                    docs = loader.load()
                    print(f"  ✅ PDF: {filename} ({len(docs)} pages)")
                    
                elif ext == '.txt':
                    loader = TextLoader(filepath)
                    docs = loader.load()
                    print(f"  ✅ Text: {filename}")
                    
                elif ext == '.docx':
                    loader = Docx2txtLoader(filepath)
                    docs = loader.load()
                    print(f"  ✅ Word: {filename}")
                    
                elif ext in ['.xlsx', '.xls']:
                    try:
                        loader = UnstructuredExcelLoader(filepath)
                        docs = loader.load()
                        print(f"  ✅ Excel: {filename}")
                    except Exception as e:
                        # Fallback to pandas
                        import pandas as pd
                        df = pd.read_excel(filepath)
                        content = df.to_string()
                        docs = [Document(page_content=content, metadata={"source": filename})]
                        print(f"  ✅ Excel (pandas): {filename}")
                    
                elif ext == '.csv':
                    loader = CSVLoader(filepath)
                    docs = loader.load()
                    print(f"  ✅ CSV: {filename}")
                    
                elif ext == '.md':
                    loader = UnstructuredMarkdownLoader(filepath)
                    docs = loader.load()
                    print(f"  ✅ Markdown: {filename}")
                    
                elif ext in ['.html', '.htm']:
                    loader = UnstructuredHTMLLoader(filepath)
                    docs = loader.load()
                    print(f"  ✅ HTML: {filename}")
                    
                elif ext in ['.pptx', '.ppt']:
                    loader = UnstructuredPowerPointLoader(filepath)
                    docs = loader.load()
                    print(f"  ✅ PowerPoint: {filename}")
                    
                else:
                    print(f"  ⚠️  Unsupported: {filename}")
                    continue
                
                # Add filename to metadata
                for doc in docs:
                    doc.metadata['filename'] = filename
                
                documents.extend(docs)
                
            except Exception as e:
                print(f"  ❌ Error loading {filename}: {str(e)}")
                continue
        
        self.documents = documents
        print(f"\n✅ Loaded {len(documents)} document chunks from {len(set([d.metadata.get('filename', 'unknown') for d in documents]))} files")
        return documents
    
    def split_documents(self, documents: List[Document]) -> List[Document]:
        """Split documents into smaller chunks - IMPROVED for better retrieval"""
        print("✂️  Splitting documents into chunks...")
        
        # IMPROVED: Smaller chunks with good overlap
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,      # Smaller for better precision
            chunk_overlap=100,   # Good overlap for context
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_documents(documents)
        
        print(f"✅ Created {len(chunks)} chunks")
        return chunks
    
    def create_vectorstore(self, chunks: List[Document]):
        """Create vector database from document chunks"""
        print("🔢 Creating vector database (this may take a few minutes)...")
        
        # Create Chroma vectorstore with persistence
        self.vectorstore = Chroma.from_documents(
            documents=chunks,
            embedding=self.embeddings,
            persist_directory=self.db_path
        )
        
        print(f"✅ Vector database created with {len(chunks)} embeddings!")
        print(f"💾 Database saved to {self.db_path}")
    
    def initialize_from_documents(self, documents_path: str = None):
        """
        MAIN INITIALIZATION METHOD - Called by main.py
        Complete pipeline: load → split → embed → store
        
        Args:
            documents_path: Optional path override for documents folder
        """
        # Use provided path or default
        if documents_path:
            self.documents_path = documents_path
        
        print("\n" + "="*60)
        print("🚀 Initializing Local RAG System...")
        print("="*60 + "\n")
        
        # Step 1: Load documents
        documents = self.load_documents()
        
        if not documents:
            raise ValueError("No documents found to process! Please upload documents first.")
        
        # Step 2: Split into chunks
        chunks = self.split_documents(documents)
        
        # Step 3: Create vector database
        self.create_vectorstore(chunks)
        
        print("\n" + "="*60)
        print("🎉 RAG System ready to answer questions!")
        print("="*60 + "\n")
        
        return {
            "documents_loaded": len(set([d.metadata.get('filename', 'unknown') for d in documents])),
            "total_chunks": len(chunks),
            "status": "ready"
        }
    
    def retrieve_relevant_docs(self, query: str, k: int = 5) -> List[Dict]:
        """Retrieve relevant documents - IMPROVED to fetch more results"""
        if not self.vectorstore:
            return []
        
        # IMPROVED: Fetch more documents for better coverage
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        # Format results with scores
        relevant_docs = []
        for i, (doc, score) in enumerate(results):
            relevant_docs.append({
                "content": doc.page_content,
                "metadata": doc.metadata,
                "relevance_score": float(score),
                "relevance_rank": i + 1
            })
        
        return relevant_docs
    
    def generate_answer(self, query: str, context_docs: List[Dict], conversation_history: List[Dict] = None) -> str:
        """Generate answer - IMPROVED with stricter prompting"""
        
        # Prepare context
        context = "\n\n".join([
            f"[Document {doc['relevance_rank']} from {doc['metadata'].get('filename', 'unknown')}]:\n{doc['content']}"
            for doc in context_docs
        ])
        
        # Prepare history
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            history_text = "\n\nPrevious conversation:\n"
            for turn in conversation_history[-3:]:
                history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n"
        
        # IMPROVED PROMPT: Strict instructions
        prompt = f"""You are a helpful assistant. Answer the question using ONLY the information provided in the Context below.

CRITICAL RULES:
1. Use ONLY information from the Context documents below
2. If the answer is not in the Context, say "I don't have that information in the provided documents"
3. Do NOT use your general knowledge
4. Do NOT make up information
5. Cite the document source when possible

Context from uploaded documents:
{context}
{history_text}

Question: {query}

Answer (based ONLY on Context above):"""
        
        # Generate response
        print("🤖 Generating answer...")
        answer = self.llm.generate(prompt)
        
        return answer
    
    def generate_answer_stream(self, query: str, context_docs: List[Dict], conversation_history: List[Dict] = None):
        """Generate answer with streaming - IMPROVED prompt"""
        
        # Prepare context
        context = "\n\n".join([
            f"[Document {doc['relevance_rank']} from {doc['metadata'].get('filename', 'unknown')}]:\n{doc['content']}"
            for doc in context_docs
        ])
        
        # Prepare history
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            history_text = "\n\nPrevious conversation:\n"
            for turn in conversation_history[-3:]:
                history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n"
        
        # IMPROVED PROMPT
        prompt = f"""You are a helpful assistant. Answer the question using ONLY the information provided in the Context below.

CRITICAL RULES:
1. Use ONLY information from the Context documents below
2. If the answer is not in the Context, say "I don't have that information in the provided documents"
3. Do NOT use your general knowledge
4. Do NOT make up information
5. Cite the document source when possible

Context from uploaded documents:
{context}
{history_text}

Question: {query}

Answer (based ONLY on Context above):"""
        
        # Stream response
        for chunk in self.llm.generate_stream(prompt):
            yield chunk
    
    def ask(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """Main method to ask a question"""
        if not self.vectorstore:
            return {
                "error": "System not initialized. Please load documents first.",
                "answer": None
            }
        
        print(f"\n❓ Question: {query}")
        
        # IMPROVED: Retrieve more documents
        print("🔍 Searching for relevant information...")
        relevant_docs = self.retrieve_relevant_docs(query, k=10)
        
        if not relevant_docs:
            return {
                "question": query,
                "answer": "I couldn't find any relevant information in the documents.",
                "sources": []
            }
        
        print(f"📚 Found {len(relevant_docs)} relevant chunks")
        
        # Show which files (for debugging)
        files_found = set([doc['metadata'].get('filename', 'unknown') for doc in relevant_docs])
        print(f"📄 From files: {', '.join(files_found)}")
        
        # Generate answer
        answer = self.generate_answer(query, relevant_docs, conversation_history)
        
        # Format sources
        sources = [
            {
                "content_preview": doc["content"][:200] + "...",
                "metadata": doc["metadata"],
                "relevance_score": doc["relevance_score"]
            }
            for doc in relevant_docs
        ]
        
        result = {
            "question": query,
            "answer": answer.strip(),
            "sources": sources
        }
        
        print("✅ Answer generated!\n")
        return result
    
    def ask_stream(self, query: str, conversation_history: List[Dict] = None):
        """Ask a question and stream the response"""
        if not self.vectorstore:
            yield json.dumps({"error": "System not initialized"})
            return
        
        # Retrieve documents
        relevant_docs = self.retrieve_relevant_docs(query, k=10)
        
        if not relevant_docs:
            yield json.dumps({
                "question": query,
                "answer": "I couldn't find any relevant information.",
                "sources": [],
                "done": True
            })
            return
        
        # Send sources first
        sources = [
            {
                "content_preview": doc["content"][:200] + "...",
                "metadata": doc["metadata"],
                "relevance_score": doc["relevance_score"]
            }
            for doc in relevant_docs
        ]
        
        yield json.dumps({
            "question": query,
            "sources": sources,
            "answer_chunk": "",
            "done": False
        })
        
        # Stream the answer
        for chunk in self.generate_answer_stream(query, relevant_docs, conversation_history):
            yield json.dumps({
                "answer_chunk": chunk,
                "done": False
            })
        
        # Send completion
        yield json.dumps({"done": True})
    
    def load_existing_db(self):
        """Load existing vector database if it exists"""
        if os.path.exists(self.db_path) and os.listdir(self.db_path):
            print("📂 Loading existing vector database...")
            self.vectorstore = Chroma(
                persist_directory=self.db_path,
                embedding_function=self.embeddings
            )
            print("✅ Existing database loaded!")
            return True
        return False
