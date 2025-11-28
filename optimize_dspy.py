"""DSPy optimizer for NL→SQL module."""
import dspy
from agent.dspy_signatures import NLToSQL, sql_validity
from tools.sqlite_tool import SQLiteTool
import json


# Training examples for NL→SQL
TRAINING_EXAMPLES = [
    {
        "question": "How many orders are there?",
        "sql": "SELECT COUNT(*) FROM Orders;",
        "constraints": "{}"
    },
    {
        "question": "What are the top 3 products by revenue?",
        "sql": """SELECT p.ProductName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as revenue
FROM Products p
JOIN \"Order Details\" od ON p.ProductID = od.ProductID
GROUP BY p.ProductName
ORDER BY revenue DESC
LIMIT 3;""",
        "constraints": "{}"
    },
    {
        "question": "Total revenue in June 1997",
        "sql": """SELECT SUM(UnitPrice * Quantity * (1 - Discount)) as revenue
FROM \"Order Details\" od
JOIN Orders o ON od.OrderID = o.OrderID
WHERE DATE(o.OrderDate) BETWEEN '1997-06-01' AND '1997-06-30';""",
        "constraints": "{\"date_ranges\": \"1997-06-01 to 1997-06-30\"}"
    },
    {
        "question": "Which category had the most sales in December 1997?",
        "sql": """SELECT c.CategoryName, SUM(od.Quantity) as total_qty
FROM Categories c
JOIN Products p ON c.CategoryID = p.CategoryID
JOIN \"Order Details\" od ON p.ProductID = od.ProductID
JOIN Orders o ON od.OrderID = o.OrderID
WHERE DATE(o.OrderDate) BETWEEN '1997-12-01' AND '1997-12-31'
GROUP BY c.CategoryName
ORDER BY total_qty DESC
LIMIT 1;""",
        "constraints": "{\"date_ranges\": \"1997-12-01 to 1997-12-31\"}"
    },
    {
        "question": "Average order value for all orders",
        "sql": """SELECT SUM(UnitPrice * Quantity * (1 - Discount)) / COUNT(DISTINCT od.OrderID) as aov
FROM \"Order Details\" od;""",
        "constraints": "{\"kpi_formulas\": \"AOV = SUM(UnitPrice * Quantity * (1 - Discount)) / COUNT(DISTINCT OrderID)\"}"
    },
    {
        "question": "Top customer by revenue in 1997",
        "sql": """SELECT c.CompanyName, SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as revenue
FROM Customers c
JOIN Orders o ON c.CustomerID = o.CustomerID
JOIN \"Order Details\" od ON o.OrderID = od.OrderID
WHERE strftime('%Y', o.OrderDate) = '1997'
GROUP BY c.CompanyName
ORDER BY revenue DESC
LIMIT 1;""",
        "constraints": "{\"date_ranges\": \"1997\"}"
    },
    {
        "question": "Revenue from Beverages category",
        "sql": """SELECT SUM(od.UnitPrice * od.Quantity * (1 - od.Discount)) as revenue
FROM \"Order Details\" od
JOIN Products p ON od.ProductID = p.ProductID
JOIN Categories c ON p.CategoryID = c.CategoryID
WHERE c.CategoryName = 'Beverages';""",
        "constraints": "{\"entities\": \"Beverages\"}"
    },
    {
        "question": "How many products in each category?",
        "sql": """SELECT c.CategoryName, COUNT(p.ProductID) as product_count
FROM Categories c
LEFT JOIN Products p ON c.CategoryID = p.CategoryID
GROUP BY c.CategoryName;""",
        "constraints": "{}"
    },
    {
        "question": "Total quantity sold per category",
        "sql": """SELECT c.CategoryName, SUM(od.Quantity) as total_qty
FROM Categories c
JOIN Products p ON c.CategoryID = p.CategoryID
JOIN \"Order Details\" od ON p.ProductID = od.ProductID
GROUP BY c.CategoryName
ORDER BY total_qty DESC;""",
        "constraints": "{}"
    },
    {
        "question": "Orders in summer 1997 (June)",
        "sql": """SELECT COUNT(*) as order_count
FROM Orders
WHERE DATE(OrderDate) BETWEEN '1997-06-01' AND '1997-06-30';""",
        "constraints": "{\"date_ranges\": \"1997-06-01 to 1997-06-30\"}"
    }
]


def create_examples(schema: str):
    """Create DSPy examples from training data."""
    examples = []
    for ex in TRAINING_EXAMPLES:
        example = dspy.Example(
            question=ex["question"],
            schema=schema,
            constraints=ex["constraints"],
            sql_query=ex["sql"]
        ).with_inputs("question", "schema", "constraints")
        examples.append(example)
    return examples


def evaluate_sql(db_tool: SQLiteTool):
    """Create evaluation function."""
    def metric(example, pred, trace=None):
        # Check if SQL is valid
        sql = pred.sql_query.strip()
        
        # Clean up SQL
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()
        
        # Try to execute
        success, data, cols, err = db_tool.execute_query(sql)
        
        return 1.0 if success else 0.0
    
    return metric


def optimize_nl_to_sql(lm: dspy.LM):
    """Optimize the NL→SQL module."""
    print("Setting up DSPy optimizer for NL→SQL...")
    
    # Configure DSPy
    dspy.settings.configure(lm=lm)
    
    # Get schema
    db_tool = SQLiteTool("data/northwind.sqlite")
    schema = db_tool.get_schema()
    
    # Create examples
    examples = create_examples(schema)
    print(f"Created {len(examples)} training examples")
    
    # Split train/val
    train_examples = examples[:8]
    val_examples = examples[8:]
    
    # Create module
    nl_to_sql = NLToSQL()
    
    # Create metric
    metric = evaluate_sql(db_tool)
    
    # Evaluate before optimization
    print("\nEvaluating before optimization...")
    correct = 0
    for ex in val_examples:
        pred = nl_to_sql(
            question=ex.question,
            schema=ex.schema,
            constraints=ex.constraints
        )
        score = metric(ex, pred)
        correct += score
        print(f"  {ex.question[:50]:50s} {'[OK]' if score > 0 else '[FAIL]'}")
    
    before_accuracy = correct / len(val_examples)
    print(f"\nBefore: {before_accuracy:.1%} ({int(correct)}/{len(val_examples)})")
    
    # Optimize with BootstrapFewShot
    print("\nOptimizing with BootstrapFewShot...")
    try:
        from dspy.teleprompt import BootstrapFewShot
        
        optimizer = BootstrapFewShot(
            metric=metric,
            max_bootstrapped_demos=3,
            max_labeled_demos=3
        )
        
        optimized_nl_to_sql = optimizer.compile(
            nl_to_sql,
            trainset=train_examples
        )
        
        # Evaluate after optimization
        print("\nEvaluating after optimization...")
        correct = 0
        for ex in val_examples:
            pred = optimized_nl_to_sql(
                question=ex.question,
                schema=ex.schema,
                constraints=ex.constraints
            )
            score = metric(ex, pred)
            correct += score
            print(f"  {ex.question[:50]:50s} {'[OK]' if score > 0 else '[FAIL]'}")
        
        after_accuracy = correct / len(val_examples)
        print(f"\nAfter: {after_accuracy:.1%} ({int(correct)}/{len(val_examples)})")
        print(f"Improvement: {(after_accuracy - before_accuracy):.1%}")
        
        # Save optimized module
        optimized_nl_to_sql.save("optimized_nl_to_sql.json")
        print("\nSaved optimized module to optimized_nl_to_sql.json")
        
    except Exception as e:
        print(f"Optimization failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("DSPy NL→SQL Optimizer")
    print("=" * 60)
    
    # Setup LM
    try:
        lm = dspy.OllamaLocal(
            model="phi3.5:3.8b-mini-instruct-q4_K_M",
            max_tokens=500,
            temperature=0.1
        )
        print("Language model configured")
    except Exception as e:
        print(f"Error setting up LM: {e}")
        print("Make sure Ollama is running and the model is pulled")
        exit(1)
    
    optimize_nl_to_sql(lm)
