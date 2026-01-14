"""
Improved RAG Engine with Better Retrieval
Fixes common issues with document retrieval and context matching
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
    IMPROVED Local RAG System with better retrieval
    Key improvements:
    1. Smaller chunk size for more precise matching
    2. More overlap for context preservation
    3. Better retrieval settings (fetch more, rank better)
    4. Improved prompting for accuracy
    """
    
    def __init__(self, model_name: str = "llama2", documents_path: str = "./documents", 
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
        """
        Split documents into smaller chunks
        IMPROVED: Smaller chunks with more overlap for better precision
        """
        print("✂️  Splitting documents into chunks...")
        
        # IMPROVED SETTINGS:
        # - Smaller chunk_size (500 instead of 1000) = more precise matching
        # - More overlap (100 instead of 200) = better context preservation
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,  # Smaller chunks for better matching
            chunk_overlap=100,  # More overlap to preserve context
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]  # Better splitting
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
    
    def retrieve_relevant_docs(self, query: str, k: int = 5) -> List[Dict]:
        """
        Retrieve relevant documents for a query
        IMPROVED: Fetch more documents (k=5 instead of 3) for better coverage
        """
        if not self.vectorstore:
            return []
        
        # Perform similarity search - FETCH MORE RESULTS
        results = self.vectorstore.similarity_search_with_score(query, k=k)
        
        # Format results with relevance scores
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
        """
        Generate answer using retrieved context and conversation history
        IMPROVED: Better prompt engineering for accuracy
        """
        
        # Prepare context from retrieved documents
        context = "\n\n".join([
            f"[Document {doc['relevance_rank']} from {doc['metadata'].get('filename', 'unknown')}]:\n{doc['content']}"
            for doc in context_docs
        ])
        
        # Prepare conversation history if available
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            history_text = "\n\nPrevious conversation:\n"
            for turn in conversation_history[-3:]:  # Last 3 turns
                history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n"
        
        # IMPROVED PROMPT: More explicit instructions for accuracy
        prompt = f"""You are a helpful assistant answering questions based ONLY on the provided documents.

IMPORTANT INSTRUCTIONS:
1. Answer ONLY using information from the Context below
2. If the Context does not contain the answer, say "I don't have that information in the documents"
3. Do NOT make up information or use general knowledge
4. Cite which document you're using when relevant
5. Be specific and accurate

Context from documents:
{context}
{history_text}

User Question: {query}

Answer (use ONLY information from Context above):"""
        
        # Generate response using Ollama
        print("🤖 Generating answer...")
        answer = self.llm.generate(prompt)
        
        return answer
    
    def generate_answer_stream(self, query: str, context_docs: List[Dict], conversation_history: List[Dict] = None):
        """Generate answer with streaming - IMPROVED prompt"""
        
        # Prepare context from retrieved documents
        context = "\n\n".join([
            f"[Document {doc['relevance_rank']} from {doc['metadata'].get('filename', 'unknown')}]:\n{doc['content']}"
            for doc in context_docs
        ])
        
        # Prepare conversation history if available
        history_text = ""
        if conversation_history and len(conversation_history) > 0:
            history_text = "\n\nPrevious conversation:\n"
            for turn in conversation_history[-3:]:
                history_text += f"User: {turn['question']}\nAssistant: {turn['answer']}\n"
        
        # IMPROVED PROMPT
        prompt = f"""You are a helpful assistant answering questions based ONLY on the provided documents.

IMPORTANT INSTRUCTIONS:
1. Answer ONLY using information from the Context below
2. If the Context does not contain the answer, say "I don't have that information in the documents"
3. Do NOT make up information or use general knowledge
4. Cite which document you're using when relevant
5. Be specific and accurate

Context from documents:
{context}
{history_text}

User Question: {query}

Answer (use ONLY information from Context above):"""
        
        # Stream response using Ollama
        for chunk in self.llm.generate_stream(prompt):
            yield chunk
    
    def ask(self, query: str, conversation_history: List[Dict] = None) -> Dict:
        """Main method to ask a question with optional conversation history"""
        if not self.vectorstore:
            return {
                "error": "System not initialized. Please load documents first.",
                "answer": None
            }
        
        print(f"\n❓ Question: {query}")
        
        # IMPROVED: Retrieve more documents (5 instead of 3)
        print("🔍 Searching for relevant information...")
        relevant_docs = self.retrieve_relevant_docs(query, k=5)
        
        if not relevant_docs:
            return {
                "question": query,
                "answer": "I couldn't find any relevant information in the documents.",
                "sources": []
            }
        
        print(f"📚 Found {len(relevant_docs)} relevant chunks")
        
        # Show which files were retrieved (for debugging)
        files_found = set([doc['metadata'].get('filename', 'unknown') for doc in relevant_docs])
        print(f"📄 From files: {', '.join(files_found)}")
        
        # Generate answer with conversation history
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
        
        # IMPROVED: Retrieve more documents
        relevant_docs = self.retrieve_relevant_docs(query, k=5)
        
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
        
        # Send completion signal
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
