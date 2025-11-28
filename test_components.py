import sys
from pathlib import Path

print("Testing components...")
print()

print("1. Testing SQLite tool...")
try:
    from tools.sqlite_tool import SQLiteTool
    db = SQLiteTool("data/northwind.sqlite")
    tables = db.get_table_names()
    print(f"   [OK] Found {len(tables)} tables")

    success, data, cols, err = db.execute_query("SELECT COUNT(*) FROM Orders")
    if success:
        print(f"   [OK] Query executed: {data[0][0]} orders")
    else:
        print(f"   [ERROR] Query failed: {err}")
except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()

print()

print("2. Testing TF-IDF retriever...")
try:
    from rag.retrieval import TFIDFRetriever
    retriever = TFIDFRetriever("docs")
    print(f"   [OK] Loaded {len(retriever.chunks)} chunks")

    results = retriever.retrieve("return policy for beverages", top_k=2)
    print(f"   [OK] Retrieved {len(results)} chunks")
    if results:
        print(f"   Top result: {results[0].chunk_id} (score: {results[0].score:.3f})")
except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()

print()

print("3. Testing DSPy signatures...")
try:
    from agent.dspy_signatures import RouterSignature, NLToSQLSignature
    print(f"   [OK] RouterSignature loaded")
    print(f"   [OK] NLToSQLSignature loaded")
except Exception as e:
    print(f"   [ERROR] {e}")
    import traceback
    traceback.print_exc()

print()

print("4. Checking evaluation file...")
try:
    import json
    with open("sample_questions_hybrid_eval.jsonl") as f:
        questions = [json.loads(line) for line in f]
    print(f"   [OK] Loaded {len(questions)} questions")
    for q in questions:
        print(f"      - {q['id']}")
except Exception as e:
    print(f"   [ERROR] {e}")

print()
print("=" * 60)
print("Component tests complete!")
print("=" * 60)
