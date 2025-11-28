import sqlite3
from pathlib import Path
import sys


def create_views(db_path: str):
    """Create lowercase compatibility views."""
    print(f"Creating views in {db_path}...")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    views = [
        "CREATE VIEW IF NOT EXISTS orders AS SELECT * FROM Orders;",
        "CREATE VIEW IF NOT EXISTS order_items AS SELECT * FROM \"Order Details\";",
        "CREATE VIEW IF NOT EXISTS products AS SELECT * FROM Products;",
        "CREATE VIEW IF NOT EXISTS customers AS SELECT * FROM Customers;",
    ]
    
    for view_sql in views:
        try:
            cursor.execute(view_sql)
            print(f"  [OK] Created view: {view_sql.split()[5]}")
        except Exception as e:
            print(f"  [ERROR] {e}")
    
    conn.commit()
    conn.close()
    print("Done!\n")


def verify_database(db_path: str):
    """Verify database structure."""
    print(f"Verifying database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cursor.fetchall()]
    
    print(f"  Found {len(tables)} tables:")
    for table in tables:
        cursor.execute(f"SELECT COUNT(*) FROM {table if table != 'Order Details' else '\"Order Details\"'};")
        count = cursor.fetchone()[0]
        print(f"    - {table}: {count} rows")
    
    conn.close()
    print()


def verify_docs(docs_dir: str):
    """Verify document corpus."""
    print(f"Verifying documents in {docs_dir}...")
    
    docs_path = Path(docs_dir)
    if not docs_path.exists():
        print(f"  [ERROR] Directory not found: {docs_dir}")
        return False
    
    required_docs = [
        "marketing_calendar.md",
        "kpi_definitions.md",
        "catalog.md",
        "product_policy.md"
    ]
    
    all_found = True
    for doc in required_docs:
        doc_path = docs_path / doc
        if doc_path.exists():
            size = doc_path.stat().st_size
            print(f"  [OK] {doc} ({size} bytes)")
        else:
            print(f"  [ERROR] {doc} NOT FOUND")
            all_found = False
    
    print()
    return all_found


def main():
    """Main setup function."""
    print("=" * 60)
    print("Retail Analytics Copilot - Setup & Verification")
    print("=" * 60)
    print()

    db_path = "data/northwind.sqlite"
    if not Path(db_path).exists():
        print(f"[ERROR] Database not found: {db_path}")
        print("Please download it first:")
        print('  Invoke-WebRequest -Uri "https://raw.githubusercontent.com/jpwhite3/northwind-SQLite3/main/dist/northwind.db" -OutFile "data/northwind.sqlite"')
        sys.exit(1)
    
    verify_database(db_path)
    create_views(db_path)

    if not verify_docs("docs"):
        print("[ERROR] Some documents are missing!")
        sys.exit(1)

    eval_file = "sample_questions_hybrid_eval.jsonl"
    if Path(eval_file).exists():
        import json
        with open(eval_file) as f:
            questions = [json.loads(line) for line in f]
        print(f"[OK] Evaluation file: {len(questions)} questions\n")
    else:
        print(f"[ERROR] Evaluation file not found: {eval_file}\n")
        sys.exit(1)
    
    print("=" * 60)
    print("[OK] Setup complete! Ready to run the agent.")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Install dependencies: pip install -r requirements.txt")
    print("2. Install Ollama: https://ollama.com")
    print("3. Pull model: ollama pull phi3.5:3.8b-mini-instruct-q4_K_M")
    print("4. Run agent: python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl")


if __name__ == "__main__":
    main()
