"""Debug script to check memory structure."""
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
from dotenv import load_dotenv

load_dotenv()

db_url = os.getenv("DATABASE_URL", "postgresql+psycopg://ai:ai@localhost:5532/ai")
conn_str = db_url.replace("postgresql+psycopg://", "postgresql://")

conn = psycopg2.connect(conn_str)

with conn.cursor(cursor_factory=RealDictCursor) as cur:
    cur.execute("SELECT run_id, user_id, memory FROM pdf_assistant LIMIT 1")
    row = cur.fetchone()
    
    if row:
        print(f"run_id: {row['run_id']}")
        print(f"user_id: {row['user_id']}")
        print("\n" + "=" * 50)
        print("MEMORY STRUCTURE:")
        print("=" * 50)
        
        memory = row['memory']
        if memory:
            print(f"\nKeys in memory: {list(memory.keys())}")
            
            for key, value in memory.items():
                print(f"\n--- {key} ---")
                if isinstance(value, list):
                    print(f"  Type: list with {len(value)} items")
                    if len(value) > 0:
                        print(f"  First item type: {type(value[0])}")
                        print(f"  First item: {json.dumps(value[0], indent=2)[:500]}...")
                elif isinstance(value, dict):
                    print(f"  Type: dict with keys: {list(value.keys())}")
                else:
                    print(f"  Type: {type(value)}")
                    print(f"  Value: {str(value)[:200]}")

conn.close()
print("\n✅ Done!")