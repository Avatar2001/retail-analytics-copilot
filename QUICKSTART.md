# Quick Start Guide

## Prerequisites Check

Before running the agent, ensure you have:

- [ ] Python 3.10 or higher installed
- [ ] Ollama installed (https://ollama.com)
- [ ] At least 8GB RAM available
- [ ] ~5GB disk space for model

## Installation Steps

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- dspy-ai (DSPy framework)
- langgraph (Graph workflow)
- scikit-learn (TF-IDF)
- pandas, numpy (Data processing)
- click, rich (CLI interface)

### 2. Install and Setup Ollama

**Windows:**
1. Download from https://ollama.com/download
2. Run installer
3. Ollama will start automatically

**Verify installation:**
```bash
ollama --version
```

### 3. Pull the Language Model

```bash
ollama pull phi3.5:3.8b-mini-instruct-q4_K_M
```

This downloads ~2.2GB. Wait for completion.

**Verify model:**
```bash
ollama list
```

You should see `phi3.5:3.8b-mini-instruct-q4_K_M` in the list.

### 4. Verify Setup

Run the setup script:
```bash
python setup.py
```

Expected output:
```
[OK] Found 14 tables
[OK] Created view: orders
[OK] Created view: order_items
[OK] Created view: products
[OK] Created view: customers
[OK] Evaluation file: 6 questions
[OK] Setup complete!
```

### 5. Test Components (Optional)

```bash
python test_components.py
```

This verifies:
- Database connection
- Document retrieval
- DSPy signatures
- Evaluation file

## Running the Agent

### Basic Usage

```bash
python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl
```

### What Happens

1. **Initialization** (~5s)
   - Loads database schema
   - Indexes documents with TF-IDF
   - Configures DSPy modules

2. **Processing** (~8s per question)
   - Routes question (rag/sql/hybrid)
   - Retrieves relevant documents
   - Generates SQL queries
   - Executes and repairs if needed
   - Synthesizes typed answer

3. **Output**
   - Creates `outputs_hybrid.jsonl`
   - Each line = one answer with citations

### Expected Runtime

- Total: ~60-90 seconds for 6 questions
- Per question: 8-12 seconds
- CPU usage: 50-80%

## Viewing Results

```bash
# View all results
cat outputs_hybrid.jsonl

# Pretty print with Python
python -c "import json; [print(json.dumps(json.loads(line), indent=2)) for line in open('outputs_hybrid.jsonl')]"
```

## Example Output

```json
{
  "id": "rag_policy_beverages_return_days",
  "final_answer": 14,
  "sql": "",
  "confidence": 0.92,
  "explanation": "According to product policy, unopened beverages have a 14-day return window.",
  "citations": [
    "product_policy::chunk0"
  ]
}
```

## Optimization (Optional)

To improve SQL generation accuracy:

```bash
python optimize_dspy.py
```

This:
- Trains NL→SQL module with 10 examples
- Evaluates on 2 validation examples
- Shows before/after metrics
- Saves optimized module

**Note:** Requires Ollama to be running. Takes ~5-10 minutes.

## Troubleshooting

### "Ollama not found" or connection error

**Check if Ollama is running:**
```bash
# Windows
Get-Process ollama

# If not running, start it
ollama serve
```

### "Model not found"

```bash
ollama pull phi3.5:3.8b-mini-instruct-q4_K_M
```

### Import errors

```bash
pip install --upgrade -r requirements.txt
```

### Database errors

```bash
python setup.py
```

### Slow performance

- Close other applications
- Ensure at least 4GB RAM free
- Check CPU isn't throttling

### Wrong answers

1. Check trace output in console
2. Run optimizer: `python optimize_dspy.py`
3. Verify documents are correct: `ls docs/`
4. Test database: `python test_components.py`

## Advanced Usage

### Custom Questions

Create your own JSONL file:

```json
{"id":"my_question_1","question":"What is the total revenue?","format_hint":"float"}
{"id":"my_question_2","question":"List top 5 customers","format_hint":"list[{customer:str, revenue:float}]"}
```

Run:
```bash
python run_agent_hybrid.py --batch my_questions.jsonl --out my_outputs.jsonl
```

### Different Model

```bash
# Pull different model
ollama pull llama3.2

# Run with custom model
python run_agent_hybrid.py --batch sample_questions_hybrid_eval.jsonl --out outputs_hybrid.jsonl --model llama3.2
```

### Custom Database

```bash
python run_agent_hybrid.py --batch questions.jsonl --out outputs.jsonl --db path/to/your.db --docs path/to/docs
```

## Performance Tuning

### Faster Retrieval
- Reduce `top_k` in retrieval (edit `graph_hybrid.py`)
- Use smaller chunk size (edit `retrieval.py`)

### Better Accuracy
- Run optimizer with more examples
- Increase temperature for more creative SQL
- Add more training examples to `optimize_dspy.py`

### Lower Memory
- Use smaller Ollama model (e.g., `phi3:mini`)
- Reduce max_tokens in LM config

## Project Structure

```
sherif/
├── agent/           # LangGraph workflow + DSPy modules
├── rag/             # Document retrieval
├── tools/           # Database access
├── data/            # Northwind database
├── docs/            # RAG corpus
├── run_agent_hybrid.py  # Main entry point ← START HERE
├── setup.py         # Verification script
└── requirements.txt # Dependencies
```

## Next Steps

After successful run:

1. **Review outputs**: Check `outputs_hybrid.jsonl`
2. **Examine traces**: Look at console output for debugging
3. **Optimize**: Run `python optimize_dspy.py` for better SQL
4. **Customize**: Add your own questions and documents
5. **Deploy**: Package for production use

## Getting Help

- Check README.md for architecture details
- Review PROJECT_STRUCTURE.md for file organization
- Examine trace output for debugging
- Test components individually with test_components.py

## Success Criteria

Your setup is working if:
- ✅ All 6 questions complete without errors
- ✅ Outputs have correct format (int, float, dict, list)
- ✅ Citations include both DB tables and doc chunks
- ✅ Confidence scores are reasonable (0.5-1.0)
- ✅ SQL queries are valid and execute successfully

## Estimated Time

- Setup: 10-15 minutes
- First run: 2-3 minutes
- Optimization: 5-10 minutes (optional)
- Total: ~20-30 minutes

Good luck! 🚀
