# import typer
# from typing import Optional,List
# from phi.assistant import Assistant
# from phi.storage.assistant.postgres import PgAssistantStorage
# from phi.knowledge.pdf import PDFUrlKnowledgeBase
# from phi.vectordb.pgvector import PgVector2

# import os
# from dotenv import load_dotenv
# load_dotenv()

# os.environ["GROQ_API_KEY"]=os.getenv("GROQ_API_KEY")
# db_url = "postgresql+psycopg://ai:ai@localhost:5532/ai"

# knowledge_base=PDFUrlKnowledgeBase(
#     urls=["https://phi-public.s3.amazonaws.com/recipes/ThaiRecipes.pdf"],
#     vector_db=PgVector2(collection="recipes",db_url=db_url)
# )


# # ye load krna pdega tbhi phir knowledge base load hoga aur assistant usko search kr payega. Agar load nhi krte to assistant ke pass knowledge base to hoga but wo empty hoga isliye assistant usme search nhi kr payega.
# knowledge_base.load()



# # ye storag is previous conversation context
# storage=PgAssistantStorage(table_name="pdf_assistant",db_url=db_url)

# # storage me jo pdf_name i.e table_name wahi function name hona chahiye

# def pdf_assistant(new: bool = False, user: str = "user"):
#     run_id: Optional[str] = None

#     if not new:
#         existing_run_ids: List[str] = storage.get_all_run_ids(user)
#         if len(existing_run_ids) > 0:
#             run_id = existing_run_ids[0]

# # this run_id will be assigned when we run the program 
# # hamne system prompt nhi diya..ye phidata ka framework hi handle kr rha hai ye sab 
#     assistant = Assistant(
#         run_id=run_id,
#         user_id=user,
#         knowledge_base=knowledge_base,

#         # jab v chat krega to ye storage me save krega ye 
#         storage=storage,
#         # Show tool calls in the response
#         show_tool_calls=True,
#         # Enable the assistant to search the knowledge base
#         search_knowledge=True,
#         # Enable the assistant to read the chat history
#         read_chat_history=True,
#     )

#     # agr suru me  chala rha hoga to no_run id hoga to assistant run_id generate karega aur usko print karega. agr new run karna hoga to new flag true krna hoga jisse ki existing run id nhi milegi aur assistant new run id generate karega. agr new flag false rhega to existing run id milegi aur assistant usi run id ke sath continue karega.
#     if run_id is None:
#         run_id = assistant.run_id
#         print(f"Started Run: {run_id}\n")
#     else:
#         print(f"Continuing Run: {run_id}\n")

#     assistant.cli_app(markdown=True)

# if __name__=="__main__":
#     typer.run(pdf_assistant)

# filepath: c:\Users\I769395\Downloads\pdf_assistant\pdf_assistant.py
import os
import re
import uuid
import json
from typing import Optional, List, Dict, Any
from contextlib import contextmanager
from dotenv import load_dotenv
from custom_pdf_reader import load_pdf_with_pages
from phi.assistant import Assistant
from phi.storage.assistant.postgres import PgAssistantStorage
from phi.knowledge.pdf import PDFUrlKnowledgeBase
from phi.vectordb.pgvector import PgVector2
from phi.llm.openai import OpenAIChat

from llm_client import get_llm_client, MODEL_NAME
from custom_embedder import SAPAICoreEmbedder

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import pool

load_dotenv()

# Database URL from environment
db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai")

# SINGLE collection for ALL PDFs - Production ready!
VECTOR_COLLECTION = os.getenv("VECTOR_COLLECTION", "pdf_embeddings")

# Connection pool for better performance
_connection_pool = None


def _get_connection_string() -> str:
    """Convert SQLAlchemy URL to psycopg2 format."""
    return db_url.replace("postgresql+psycopg://", "postgresql://")


def get_connection_pool():
    """Get or create connection pool."""
    global _connection_pool
    if _connection_pool is None:
        _connection_pool = pool.ThreadedConnectionPool(
            minconn=1,
            maxconn=10,
            dsn=_get_connection_string()
        )
    return _connection_pool


@contextmanager
def get_db_connection():
    """Get a database connection from pool with automatic cleanup."""
    conn = None
    try:
        conn = get_connection_pool().getconn()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            get_connection_pool().putconn(conn)


def get_table_columns(table_name: str) -> List[str]:
    """Dynamically get all columns for a table."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            return [row[0] for row in cur.fetchall()]


def table_exists(table_name: str) -> bool:
    """Check if a table exists."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = %s
                )
            """, (table_name,))
            return cur.fetchone()[0]


def column_exists(table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.columns 
                    WHERE table_name = %s AND column_name = %s
                )
            """, (table_name, column_name))
            return cur.fetchone()[0]


def safe_add_column(table_name: str, column_name: str, column_type: str, default: str = None):
    """Safely add a column if it doesn't exist."""
    if not column_exists(table_name, column_name):
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                default_clause = f" DEFAULT {default}" if default else ""
                cur.execute(f"""
                    ALTER TABLE {table_name} 
                    ADD COLUMN {column_name} {column_type}{default_clause}
                """)
                conn.commit()
                print(f"✅ Added column '{column_name}' to '{table_name}'")


def init_pdf_tables():
    """Create and migrate tables to store PDF session data."""
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # Create table if not exists
            cur.execute("""
                CREATE TABLE IF NOT EXISTS session_pdfs (
                    id SERIAL PRIMARY KEY,
                    run_id VARCHAR(255) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    pdf_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(run_id, pdf_url)
                )
            """)
            conn.commit()
    
    # Dynamically add missing columns (migration-safe)
    required_columns = {
        "pdf_id": ("VARCHAR(255)", None),
        "pdf_name": ("VARCHAR(500)", None),
        "user_id": ("VARCHAR(255)", "'unknown'"),
    }
    
    for col_name, (col_type, default) in required_columns.items():
        safe_add_column("session_pdfs", col_name, col_type, default)
    
    # Create indexes safely
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            indexes = [
                ("idx_session_pdfs_run_id", "run_id"),
                ("idx_session_pdfs_user_id", "user_id"),
                ("idx_session_pdfs_pdf_id", "pdf_id"),
            ]
            for idx_name, col_name in indexes:
                try:
                    cur.execute(f"""
                        CREATE INDEX IF NOT EXISTS {idx_name} 
                        ON session_pdfs({col_name})
                    """)
                except Exception:
                    pass  # Index might already exist or column missing
            conn.commit()


# Initialize tables on module load
try:
    init_pdf_tables()
except Exception as e:
    print(f"Warning: Could not initialize PDF tables: {e}")

# Storage for chat history
storage = PgAssistantStorage(table_name="pdf_assistant", db_url=db_url)

# Create custom embedder
sap_embedder = SAPAICoreEmbedder()

# Single vector DB for all PDFs
_vector_db = None


def get_vector_db() -> PgVector2:
    """Get the shared vector database for all PDFs."""
    global _vector_db
    if _vector_db is None:
        _vector_db = PgVector2(
            collection=VECTOR_COLLECTION,
            db_url=db_url,
            embedder=sap_embedder
        )
        try:
            _vector_db.create()
        except Exception as e:
            print(f"Vector DB might already exist: {e}")
    return _vector_db


def generate_pdf_id(pdf_url: str) -> str:
    """Generate a unique ID for a PDF based on URL."""
    # Use consistent hashing
    import hashlib
    url_hash = hashlib.sha256(pdf_url.encode()).hexdigest()[:12]
    return f"pdf_{url_hash}"


def extract_pdf_url(text: str) -> Optional[str]:
    """Extract PDF URL from user message if present."""
    if not text:
        return None
    
    # Direct PDF links
    url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+\.pdf(?:\?[^\s]*)?'
    matches = re.findall(url_pattern, text, re.IGNORECASE)
    if matches:
        return matches[0]
    
    # General URLs that might be PDFs
    general_url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
    pdf_hosts = ['arxiv', 'researchgate', 'academia', 'ieee', 'springer', 'sciencedirect']
    
    for match in re.findall(general_url_pattern, text):
        if 'pdf' in match.lower() or any(host in match.lower() for host in pdf_hosts):
            return match
    
    return None


def get_pdf_name_from_url(url: str) -> str:
    """Extract a friendly name from PDF URL."""
    if not url:
        return "Document"
    
    try:
        path = url.split('?')[0]
        filename = path.split('/')[-1]
        
        if filename.endswith('.pdf'):
            filename = filename[:-4]
        
        # Clean up common URL encodings and separators
        name = filename
        for char in ['_', '-', '%20', '%2520', '+']:
            name = name.replace(char, ' ')
        
        # Remove multiple spaces and trim
        name = ' '.join(name.split())
        
        return name.title() if name else "Document"
    except Exception:
        return "Document"



def save_pdf_to_db(run_id: str, user_id: str, pdf_url: str, pdf_id: str, pdf_name: str) -> bool:
    """Save PDF info to database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Get available columns dynamically
                available_cols = get_table_columns("session_pdfs")
                
                # Build dynamic insert
                cols = ["run_id", "pdf_url"]
                vals = [run_id, pdf_url]
                placeholders = ["%s", "%s"]
                
                if "user_id" in available_cols:
                    cols.append("user_id")
                    vals.append(user_id)
                    placeholders.append("%s")
                
                if "pdf_id" in available_cols:
                    cols.append("pdf_id")
                    vals.append(pdf_id)
                    placeholders.append("%s")
                
                if "pdf_name" in available_cols:
                    cols.append("pdf_name")
                    vals.append(pdf_name)
                    placeholders.append("%s")
                
                # Build dynamic ON CONFLICT update clause
                update_parts = []
                if "pdf_id" in available_cols:
                    update_parts.append("pdf_id = EXCLUDED.pdf_id")
                if "pdf_name" in available_cols:
                    update_parts.append("pdf_name = EXCLUDED.pdf_name")
                if "user_id" in available_cols:
                    update_parts.append("user_id = EXCLUDED.user_id")
                
                # Fallback to no-op update if no columns to update
                update_clause = ", ".join(update_parts) if update_parts else "run_id = EXCLUDED.run_id"
                
                query = f"""
                    INSERT INTO session_pdfs ({', '.join(cols)})
                    VALUES ({', '.join(placeholders)})
                    ON CONFLICT (run_id, pdf_url) DO UPDATE SET
                    {update_clause}
                """
                
                cur.execute(query, vals)
                conn.commit()
                return True
    except Exception as e:
        print(f"⚠️ Error saving PDF to DB: {e}")
        return False



def get_pdfs_from_db(run_id: str) -> List[Dict]:
    """Get all PDFs for a session from database."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Get available columns dynamically
                available_cols = get_table_columns("session_pdfs")
                
                # Build select with available columns
                select_cols = ["pdf_url"]
                if "pdf_id" in available_cols:
                    select_cols.append("pdf_id")
                if "pdf_name" in available_cols:
                    select_cols.append("pdf_name")
                if "created_at" in available_cols:
                    select_cols.append("created_at")
                
                order_by = "created_at ASC" if "created_at" in available_cols else "id ASC"
                
                cur.execute(f"""
                    SELECT {', '.join(select_cols)}
                    FROM session_pdfs
                    WHERE run_id = %s
                    ORDER BY {order_by}
                """, (run_id,))
                
                rows = cur.fetchall()
                result = []
                for row in rows:
                    pdf_url = row.get("pdf_url", "")
                    result.append({
                        "url": pdf_url,
                        "pdf_id": row.get("pdf_id") or generate_pdf_id(pdf_url),
                        "name": row.get("pdf_name") or get_pdf_name_from_url(pdf_url)
                    })
                return result
    except Exception as e:
        print(f"⚠️ Error getting PDFs from DB: {e}")
        return []


def get_all_sessions_from_db(user_id: str) -> List[Dict]:
    """Get all chat sessions with their PDFs for a user."""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                available_cols = get_table_columns("session_pdfs")
                
                # Check if user_id column exists
                if "user_id" not in available_cols:
                    return []
                
                name_col = "pdf_name" if "pdf_name" in available_cols else "pdf_url"
                time_col = "created_at" if "created_at" in available_cols else "id"
                
                cur.execute(f"""
                    SELECT run_id, 
                           array_agg({name_col} ORDER BY {time_col}) as pdf_names,
                           MIN({time_col}) as first_created,
                           MAX({time_col}) as last_updated
                    FROM session_pdfs
                    WHERE user_id = %s
                    GROUP BY run_id
                    ORDER BY last_updated DESC
                """, (user_id,))
                
                return [dict(row) for row in cur.fetchall()]
    except Exception as e:
        print(f"⚠️ Error getting sessions: {e}")
        return []


def check_pdf_embeddings_exist(pdf_id: str) -> bool:
    """Check if embeddings already exist for this PDF."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Try different schema combinations
                for schema in ['ai', 'public', '']:
                    table_ref = f'{schema}."{VECTOR_COLLECTION}"' if schema else f'"{VECTOR_COLLECTION}"'
                    try:
                        cur.execute(f"""
                            SELECT COUNT(*) FROM {table_ref}
                            WHERE meta_data->>'pdf_id' = %s
                            LIMIT 1
                        """, (pdf_id,))
                        count = cur.fetchone()[0]
                        if count > 0:
                            return True
                    except Exception:
                        continue
                return False
    except Exception as e:
        print(f"⚠️ Error checking embeddings: {e}")
        return False


def load_pdf_embeddings(pdf_url: str, pdf_id: str) -> bool:
    """Load PDF embeddings into the shared vector database."""
    
    # Check if already loaded
    if check_pdf_embeddings_exist(pdf_id):
        print(f"📄 Using existing embeddings for: {get_pdf_name_from_url(pdf_url)}")
        return True
    
    print(f"📄 Loading with page tracking: {get_pdf_name_from_url(pdf_url)}")
    
    try:
        # Load documents with page numbers
        documents = load_pdf_with_pages(pdf_url)
        
        if not documents:
            print(f"⚠️ No content extracted from PDF")
            return False
        
        print(f"📝 Extracted {len(documents)} chunks from PDF")
        
        # Add metadata to each document
        pdf_name = get_pdf_name_from_url(pdf_url)
        for doc in documents:
            doc.meta_data = doc.meta_data or {}
            doc.meta_data["pdf_id"] = pdf_id
            doc.meta_data["pdf_url"] = pdf_url
            doc.meta_data["pdf_name"] = pdf_name
        
        # Get shared vector DB and insert
        vector_db = get_vector_db()
        
        try:
            vector_db.insert(documents)
            print(f"✅ Loaded: {pdf_name}")
        except Exception as e:
            error_str = str(e).lower()
            if "duplicate" in error_str or "unique" in error_str:
                print(f"⚠️ Some chunks already exist, continuing...")
            else:
                raise
        
        return True
        
    except Exception as e:
        print(f"❌ Error loading PDF: {e}")
        raise


def load_pdf_to_session(run_id: str, user_id: str, pdf_url: str) -> Dict[str, str]:
    """Load a PDF into the session."""
    # Check if already in this session
    existing_pdfs = get_pdfs_from_db(run_id)
    for pdf_info in existing_pdfs:
        if pdf_info["url"] == pdf_url:
            # Ensure embeddings are loaded
            load_pdf_embeddings(pdf_url, pdf_info["pdf_id"])
            return pdf_info
    
    # Generate PDF ID and name
    pdf_id = generate_pdf_id(pdf_url)
    pdf_name = get_pdf_name_from_url(pdf_url)
    
    # Load embeddings first
    load_pdf_embeddings(pdf_url, pdf_id)
    
    # Save to session
    save_pdf_to_db(run_id, user_id, pdf_url, pdf_id, pdf_name)
    
    return {
        "url": pdf_url,
        "pdf_id": pdf_id,
        "name": pdf_name
    }


def ensure_session_pdfs_loaded(run_id: str):
    """Ensure all PDFs for a session are loaded."""
    pdfs = get_pdfs_from_db(run_id)
    for pdf_info in pdfs:
        try:
            load_pdf_embeddings(pdf_info["url"], pdf_info["pdf_id"])
        except Exception as e:
            print(f"⚠️ Could not load PDF {pdf_info['name']}: {e}")


def search_session_pdfs(run_id: str, query: str, num_documents: int = 5) -> List:
    """Search across all PDFs in a session."""
    pdfs = get_pdfs_from_db(run_id)
    if not pdfs:
        return []
    
    pdf_ids = {p["pdf_id"] for p in pdfs}
    vector_db = get_vector_db()
    
    try:
        all_results = vector_db.search(query, limit=num_documents * 3)
        
        filtered = []
        for doc in all_results:
            if doc.meta_data and doc.meta_data.get("pdf_id") in pdf_ids:
                filtered.append(doc)
                if len(filtered) >= num_documents:
                    break
        
        return filtered
    except Exception as e:
        print(f"Error searching: {e}")
        return []


def get_session_context(run_id: str) -> str:
    """Get context about loaded PDFs for the assistant."""
    pdfs = get_pdfs_from_db(run_id)
    if not pdfs:
        return "No PDFs loaded yet. User can share a PDF link to analyze."
    
    context = f"Currently loaded PDFs ({len(pdfs)}):\n"
    for i, pdf in enumerate(pdfs, 1):
        context += f"{i}. {pdf['name']}\n"
    return context


def get_assistant(user_id: str, run_id: str) -> Assistant:
    """Get or create an assistant for the given user and run_id."""
    sap_client = get_llm_client()
    
    llm = OpenAIChat(
        model=MODEL_NAME,
        api_key="not-needed",
        openai_client=sap_client
    )
    
    vector_db = get_vector_db()
    pdfs = get_pdfs_from_db(run_id)
    
    knowledge_base = None
    if pdfs:
        knowledge_base = PDFUrlKnowledgeBase(
            urls=[p["url"] for p in pdfs],
            vector_db=vector_db
        )
    
    session_context = get_session_context(run_id)
    
    assistant = Assistant(
        run_id=run_id,
        user_id=user_id,
        llm=llm,
        knowledge_base=knowledge_base,
        storage=storage,
        show_tool_calls=True,
        search_knowledge=bool(knowledge_base),
        read_chat_history=True,
        description="You are a helpful PDF assistant. Users can share PDF links directly in chat, and you'll help them understand the content.",
        instructions=[
            "When user shares a PDF link, acknowledge it and offer to help with questions",
            f"Current session info: {session_context}",
            "When answering, mention which PDF the information comes from (check 'pdf_name' in metadata)",
            "IMPORTANT: Each chunk has 'page_number' in metadata. Always mention the page number when referencing content (e.g., 'On page 5, it says...')",
            "If user asks about content but no PDF is loaded, ask them to share a PDF link",
            "Always be helpful and provide detailed answers based on the PDF content",
        ]
    )
    
    return assistant


def chat_with_assistant(user_id: str, run_id: str, user_message: str) -> str:
    """Process user message - detect PDF links, load them, and respond."""
    if not user_message or not user_message.strip():
        return "Please enter a message."
    
    pdf_url = extract_pdf_url(user_message)
    
    if pdf_url:
        try:
            pdf_info = load_pdf_to_session(run_id, user_id, pdf_url)
            load_message = f"📚 **Loaded: {pdf_info['name']}**\n\n"
            
            question_part = user_message.replace(pdf_url, "").strip()
            
            if question_part and len(question_part) > 10:
                assistant = get_assistant(user_id, run_id)
                response = assistant.run(question_part, stream=False)
                return load_message + str(response)
            else:
                loaded_pdfs = get_pdfs_from_db(run_id)
                if len(loaded_pdfs) > 1:
                    return load_message + f"Got it! I now have {len(loaded_pdfs)} PDFs loaded. Ask me anything about them!"
                return load_message + "PDF loaded successfully! What would you like to know about it?"
                
        except Exception as e:
            return f"❌ Failed to load PDF: {str(e)}\n\nPlease check the URL and try again."
    
    pdfs = get_pdfs_from_db(run_id)
    if not pdfs:
        return "📎 Please share a PDF link first, and I'll help you analyze it!\n\nJust paste the URL (e.g., `https://example.com/document.pdf`)"
    
    assistant = get_assistant(user_id, run_id)
    response = assistant.run(user_message, stream=False)
    return str(response)


def get_all_chats_for_user(user_id: str) -> List[Dict]:
    """Get all chat sessions for a user from database."""
    sessions = get_all_sessions_from_db(user_id)
    chats = []
    
    for session in sessions:
        pdf_names = session.get("pdf_names") or []
        if pdf_names:
            display = ", ".join(str(n) for n in pdf_names[:2])
            if len(pdf_names) > 2:
                display += f" +{len(pdf_names)-2} more"
        else:
            display = "No PDFs"
        
        chats.append({
            "run_id": session["run_id"],
            "display_name": display,
            "pdf_count": len(pdf_names),
            "last_updated": session.get("last_updated")
        })
    
    return chats


def create_new_chat(user_id: str) -> str:
    """Create a new chat session."""
    return str(uuid.uuid4())


def get_loaded_pdfs(run_id: str) -> List[Dict]:
    """Get list of PDFs loaded in a session."""
    return get_pdfs_from_db(run_id)


def get_chat_history(user_id: str, run_id: str) -> List[Dict]:
    """Get chat history for a specific run_id."""
    try:
        ensure_session_pdfs_loaded(run_id)
    except Exception as e:
        print(f"⚠️ Could not ensure PDFs loaded: {e}")
    
    messages = []
    
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT memory FROM pdf_assistant 
                    WHERE run_id = %s
                    LIMIT 1
                """, (run_id,))
                
                row = cur.fetchone()
                
                if row and row.get('memory'):
                    memory_data = row['memory']
                    
                    if isinstance(memory_data, str):
                        memory_data = json.loads(memory_data)
                    
                    chat_history = memory_data.get("chat_history", [])
                    
                    for msg in chat_history:
                        if isinstance(msg, dict):
                            role = msg.get("role", "user")
                            content = msg.get("content", "")
                            
                            if content and role in ["user", "assistant"]:
                                messages.append({
                                    "role": role,
                                    "content": content
                                })
    except Exception as e:
        print(f"Error loading chat history: {e}")
    
    return messages


if __name__ == "__main__":
    import typer
    
    def cli_chat(user: str = "user", new: bool = False):
        """CLI interface for testing."""
        if new:
            run_id = create_new_chat(user)
            print(f"🆕 Started new chat: {run_id}")
        else:
            chats = get_all_chats_for_user(user)
            if chats:
                run_id = chats[0]["run_id"]
                print(f"📂 Continuing chat: {run_id}")
                pdfs = get_loaded_pdfs(run_id)
                if pdfs:
                    print(f"📚 PDFs in this chat: {', '.join(p['name'] for p in pdfs)}")
            else:
                run_id = create_new_chat(user)
                print(f"🆕 Started new chat: {run_id}")
        
        print("\n📎 Paste any PDF link to get started!")
        print("💡 Commands: 'pdfs' (list PDFs), 'new' (new chat), 'quit' (exit)\n")
        print("-" * 50)
        
        while True:
            try:
                user_input = input("\n👤 You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() in ['exit', 'quit', 'q']:
                    print("👋 Goodbye!")
                    break
                if user_input.lower() == 'new':
                    run_id = create_new_chat(user)
                    print(f"🆕 Started new chat: {run_id}")
                    continue
                if user_input.lower() == 'pdfs':
                    pdfs = get_loaded_pdfs(run_id)
                    if pdfs:
                        print("\n📚 Loaded PDFs:")
                        for i, p in enumerate(pdfs, 1):
                            print(f"  {i}. {p['name']}")
                    else:
                        print("\n📭 No PDFs loaded yet")
                    continue
                
                response = chat_with_assistant(user, run_id, user_input)
                print(f"\n🤖 Assistant: {response}")
                
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                break
    
    typer.run(cli_chat)