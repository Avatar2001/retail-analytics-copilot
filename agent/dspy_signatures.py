import dspy
from typing import List, Dict, Any, Literal


class RouterSignature(dspy.Signature):
    """Route question to appropriate handler: rag, sql, or hybrid."""
    question = dspy.InputField(desc="User's retail analytics question")
    route = dspy.OutputField(desc="Route type: 'rag', 'sql', or 'hybrid'")
    reasoning = dspy.OutputField(desc="Brief explanation of routing decision")


class PlannerSignature(dspy.Signature):
    """Extract constraints and requirements from question and context."""
    question = dspy.InputField(desc="User's question")
    context = dspy.InputField(desc="Retrieved document context")
    date_ranges = dspy.OutputField(desc="Extracted date ranges (JSON format)")
    entities = dspy.OutputField(desc="Relevant entities (categories, products, customers)")
    kpi_formulas = dspy.OutputField(desc="KPI formulas if mentioned")
    constraints = dspy.OutputField(desc="Other constraints or filters")


class NLToSQLSignature(dspy.Signature):
    """Generate SQLite query from natural language question."""
    question = dspy.InputField(desc="User's question")
    schema = dspy.InputField(desc="Database schema information")
    constraints = dspy.InputField(desc="Extracted constraints (dates, entities, etc.)")
    sql_query = dspy.OutputField(desc="Valid SQLite query")
    explanation = dspy.OutputField(desc="Brief explanation of the query logic")


class SQLRepairSignature(dspy.Signature):
    """Repair a failed SQL query."""
    original_query = dspy.InputField(desc="The SQL query that failed")
    error_message = dspy.InputField(desc="Error message from execution")
    schema = dspy.InputField(desc="Database schema")
    question = dspy.InputField(desc="Original question")
    repaired_query = dspy.OutputField(desc="Fixed SQL query")
    changes = dspy.OutputField(desc="What was changed and why")


class SynthesizerSignature(dspy.Signature):
    """Synthesize final answer from query results and context."""
    question = dspy.InputField(desc="Original question")
    format_hint = dspy.InputField(desc="Expected output format")
    sql_results = dspy.InputField(desc="SQL query results (if any)")
    rag_context = dspy.InputField(desc="Retrieved document context (if any)")
    final_answer = dspy.OutputField(desc="Answer in the exact format requested")
    explanation = dspy.OutputField(desc="Brief explanation (max 2 sentences)")
    confidence = dspy.OutputField(desc="Confidence score 0.0-1.0")


class Router(dspy.Module):
    """Router module to classify questions."""
    
    def __init__(self):
        super().__init__()
        self.predict = dspy.ChainOfThought(RouterSignature)
    
    def forward(self, question: str) -> dspy.Prediction:
        """Route the question."""
        return self.predict(question=question)


class Planner(dspy.Module):
    """Planner module to extract constraints."""
    
    def __init__(self):
        super().__init__()
        self.predict = dspy.ChainOfThought(PlannerSignature)
    
    def forward(self, question: str, context: str) -> dspy.Prediction:
        """Extract constraints from question and context."""
        return self.predict(question=question, context=context)


class NLToSQL(dspy.Module):
    """Natural language to SQL module."""
    
    def __init__(self):
        super().__init__()
        self.predict = dspy.ChainOfThought(NLToSQLSignature)
    
    def forward(self, question: str, schema: str, constraints: str) -> dspy.Prediction:
        """Generate SQL query."""
        return self.predict(
            question=question,
            schema=schema,
            constraints=constraints
        )


class SQLRepairer(dspy.Module):
    """SQL repair module."""
    
    def __init__(self):
        super().__init__()
        self.predict = dspy.ChainOfThought(SQLRepairSignature)
    
    def forward(self, original_query: str, error_message: str, 
                schema: str, question: str) -> dspy.Prediction:
        """Repair failed SQL query."""
        return self.predict(
            original_query=original_query,
            error_message=error_message,
            schema=schema,
            question=question
        )


class Synthesizer(dspy.Module):
    """Answer synthesis module."""
    
    def __init__(self):
        super().__init__()
        self.predict = dspy.ChainOfThought(SynthesizerSignature)
    
    def forward(self, question: str, format_hint: str, 
                sql_results: str, rag_context: str) -> dspy.Prediction:
        """Synthesize final answer."""
        return self.predict(
            question=question,
            format_hint=format_hint,
            sql_results=sql_results,
            rag_context=rag_context
        )


def router_accuracy(example, pred, trace=None):
    """Metric for router accuracy."""
    return example.route.lower() == pred.route.lower()


def sql_validity(example, pred, trace=None):
    """Metric for SQL validity (simplified)."""
    sql = pred.sql_query.strip()
    if not sql:
        return 0.0
    if not sql.upper().startswith('SELECT'):
        return 0.0
    if ';' in sql[:-1]:  
        return 0.0
    return 1.0


def format_adherence(example, pred, trace=None):
    """Metric for format adherence."""
    import json
    format_hint = example.format_hint
    answer = pred.final_answer
    
    try:
        if format_hint == "int":
            int(answer)
            return 1.0
        elif format_hint == "float":
            float(answer)
            return 1.0
        elif format_hint.startswith("{") or format_hint.startswith("list["):

            json.loads(answer if isinstance(answer, str) else json.dumps(answer))
            return 1.0
    except:
        return 0.0
    
    return 0.5
