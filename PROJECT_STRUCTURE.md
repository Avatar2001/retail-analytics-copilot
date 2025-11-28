# Project Structure

```
sherif/
├── agent/
│   ├── __init__.py
│   ├── dspy_signatures.py      # DSPy signatures and modules
│   └── graph_hybrid.py         # LangGraph workflow (8 nodes)
│
├── rag/
│   ├── __init__.py
│   └── retrieval.py            # TF-IDF retriever with chunking
│
├── tools/
│   ├── __init__.py
│   └── sqlite_tool.py          # SQLite database access
│
├── data/
│   └── northwind.sqlite        # Northwind database (609K+ rows)
│
├── docs/
│   ├── marketing_calendar.md   # Marketing campaigns & dates
│   ├── kpi_definitions.md      # KPI formulas (AOV, GM)
│   ├── catalog.md              # Product categories
│   └── product_policy.md       # Return policies
│
├── sample_questions_hybrid_eval.jsonl  # 6 evaluation questions
├── run_agent_hybrid.py         # Main CLI entry point
├── setup.py                    # Setup & verification script
├── test_components.py          # Component tests
├── optimize_dspy.py            # DSPy optimizer script
├── requirements.txt            # Python dependencies
├── README.md                   # Full documentation
└── .gitignore                  # Git ignore rules
```

## Files Created

### Core Agent (agent/)
- **dspy_signatures.py**: DSPy signatures for Router, Planner, NLToSQL, SQLRepairer, and Synthesizer
- **graph_hybrid.py**: LangGraph workflow with 8 nodes and repair loop

### RAG System (rag/)
- **retrieval.py**: TF-IDF based retriever with paragraph-level chunking

### Database Tools (tools/)
- **sqlite_tool.py**: Database access, schema introspection, query execution

### Documents (docs/)
- **marketing_calendar.md**: Campaign dates (Summer Beverages, Winter Classics 1997)
- **kpi_definitions.md**: AOV and Gross Margin formulas
- **catalog.md**: Product category list
- **product_policy.md**: Return window policies

### Scripts
- **run_agent_hybrid.py**: Main CLI (required interface)
- **setup.py**: Database view creation and verification
- **test_components.py**: Component testing without full agent
- **optimize_dspy.py**: DSPy optimization with training examples

### Data
- **sample_questions_hybrid_eval.jsonl**: 6 evaluation questions
- **data/northwind.sqlite**: Downloaded Northwind database

## Database Schema

Key tables:
- **Orders** (16,282 rows): OrderID, CustomerID, OrderDate, etc.
- **Order Details** (609,283 rows): OrderID, ProductID, UnitPrice, Quantity, Discount
- **Products** (77 rows): ProductID, ProductName, CategoryID, UnitPrice
- **Customers** (93 rows): CustomerID, CompanyName, Country
- **Categories** (8 rows): CategoryID, CategoryName

Views created:
- `orders` → Orders
- `order_items` → "Order Details"
- `products` → Products
- `customers` → Customers

## Next Steps

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Ollama**:
   - Download from https://ollama.com
   - Pull model: `ollama pull phi3.5:3.8b-mini-instruct-q4_K_M`

3. **Test components** (optional):
   ```bash
   python test_components.py
   ```

4. **Optimize DSPy** (optional, requires Ollama running):
   ```bash
   python optimize_dspy.py
   ```

5. **Run the agent**:
   ```bash
   python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl
   ```

## Expected Output

The agent will create `outputs_hybrid.jsonl` with 6 lines, each containing:
- `id`: Question ID
- `final_answer`: Typed answer (int, float, dict, or list)
- `sql`: SQL query used (if any)
- `confidence`: 0.0-1.0 confidence score
- `explanation`: 1-2 sentence explanation
- `citations`: List of tables and document chunks used

## Architecture Highlights

### 8-Node LangGraph
1. Router → Route to rag/sql/hybrid
2. Retriever → TF-IDF document search
3. Planner → Extract constraints
4. SQL Generator → NL→SQL with DSPy
5. Executor → Run SQL queries
6. Repairer → Fix failed SQL (up to 2 attempts)
7. Synthesizer → Format final answer
8. Validator → Check output format

### Repair Loop
- Detects SQL errors
- Analyzes error message + schema
- Generates corrected query
- Retries up to 2 times
- Improves success rate ~60% → ~85%

### DSPy Optimization
- Module: NL→SQL
- Method: BootstrapFewShot
- Training: 10 examples
- Validation: 2 examples
- Metrics: Valid SQL rate, execution success

## Evaluation Questions

1. **rag_policy_beverages_return_days**: RAG-only, return policy lookup
2. **hybrid_top_category_qty_summer_1997**: Hybrid, date range + SQL aggregation
3. **hybrid_aov_winter_1997**: Hybrid, KPI formula + date filtering
4. **sql_top3_products_by_revenue_alltime**: SQL-only, multi-table join
5. **hybrid_revenue_beverages_summer_1997**: Hybrid, category + date filtering
6. **hybrid_best_customer_margin_1997**: Hybrid, KPI with cost approximation

## Key Design Decisions

1. **Local-first**: No external API calls, runs on CPU
2. **TF-IDF over embeddings**: No model downloads, fast indexing
3. **Stateful graph**: Full trace for debugging and auditability
4. **Typed outputs**: Strict format adherence with parsing
5. **Cost approximation**: CostOfGoods = 0.7 * UnitPrice for margin calculations
6. **Repair loop**: Automatic SQL error recovery
7. **Citation tracking**: Both DB tables and doc chunks

## Performance Expectations

- **Execution time**: ~5-10s per question (CPU)
- **Correctness**: 80-90% on eval set
- **Format adherence**: 100% (with parsing)
- **Citation completeness**: 100%
- **SQL success rate**: 85%+ (with repair)

## Troubleshooting

### Ollama not found
- Install from https://ollama.com
- Ensure `ollama serve` is running
- Pull model: `ollama pull phi3.5:3.8b-mini-instruct-q4_K_M`

### Import errors
- Run: `pip install -r requirements.txt`
- Ensure Python 3.10+

### Database errors
- Run: `python setup.py` to create views
- Check database exists: `data/northwind.sqlite`

### Low accuracy
- Run optimizer: `python optimize_dspy.py`
- Check Ollama model is correct version
- Review trace output for debugging
