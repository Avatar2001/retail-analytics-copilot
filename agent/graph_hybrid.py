from typing import TypedDict, Annotated, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END
import dspy
import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from agent.dspy_signatures import Router, Planner, NLToSQL, SQLRepairer, Synthesizer
from rag.retrieval import TFIDFRetriever
from tools.sqlite_tool import SQLiteTool


class AgentState(TypedDict):
    """State for the agent graph."""
    question: str
    format_hint: str
    route: str
    rag_context: str
    rag_chunks: List[Dict[str, Any]]
    constraints: Dict[str, Any]
    sql_query: str
    sql_results: Any
    sql_columns: List[str]
    sql_error: str
    final_answer: Any
    explanation: str
    confidence: float
    citations: List[str]
    repair_count: int
    trace: List[Dict[str, Any]]


class HybridAgent:
    """Hybrid RAG + SQL agent using LangGraph."""
    
    def __init__(self, db_path: str, docs_dir: str, lm: dspy.LM):
        """Initialize the agent."""
        self.db_tool = SQLiteTool(db_path)
        self.retriever = TFIDFRetriever(docs_dir)
        self.lm = lm

        dspy.settings.configure(lm=lm)
        self.router = Router()
        self.planner = Planner()
        self.nl_to_sql = NLToSQL()
        self.sql_repairer = SQLRepairer()
        self.synthesizer = Synthesizer()

        self.schema = self.db_tool.get_schema()

        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        workflow = StateGraph(AgentState)

        workflow.add_node("router", self._route_question)
        workflow.add_node("retriever", self._retrieve_documents)
        workflow.add_node("planner", self._plan_extraction)
        workflow.add_node("sql_generator", self._generate_sql)
        workflow.add_node("executor", self._execute_sql)
        workflow.add_node("synthesizer", self._synthesize_answer)
        workflow.add_node("validator", self._validate_output)
        workflow.add_node("repairer", self._repair_sql)

        workflow.set_entry_point("router")

        workflow.add_conditional_edges(
            "router",
            self._route_decision,
            {
                "rag": "retriever",
                "sql": "planner",
                "hybrid": "retriever"
            }
        )
        
        workflow.add_edge("retriever", "planner")
        
        workflow.add_conditional_edges(
            "planner",
            self._needs_sql,
            {
                "yes": "sql_generator",
                "no": "synthesizer"
            }
        )
        
        workflow.add_edge("sql_generator", "executor")
        
        workflow.add_conditional_edges(
            "executor",
            self._check_sql_success,
            {
                "success": "synthesizer",
                "error": "repairer"
            }
        )
        
        workflow.add_conditional_edges(
            "repairer",
            self._check_repair_limit,
            {
                "retry": "executor",
                "give_up": "synthesizer"
            }
        )
        
        workflow.add_edge("synthesizer", "validator")
        
        workflow.add_conditional_edges(
            "validator",
            self._check_validation,
            {
                "valid": END,
                "invalid": "synthesizer"
            }
        )
        
        return workflow.compile()
    
    def _route_question(self, state: AgentState) -> AgentState:
        """Route the question to appropriate handler."""
        result = self.router(question=state["question"])
        route = result.route.lower().strip()

        if route not in ["rag", "sql", "hybrid"]:
            route = "hybrid" 
        
        state["route"] = route
        state["trace"].append({
            "node": "router",
            "route": route,
            "reasoning": result.reasoning
        })
        return state
    
    def _retrieve_documents(self, state: AgentState) -> AgentState:
        """Retrieve relevant documents."""
        chunks = self.retriever.retrieve(state["question"], top_k=3)
        
        state["rag_chunks"] = [
            {
                "chunk_id": c.chunk_id,
                "content": c.content,
                "score": c.score
            }
            for c in chunks
        ]
        
        state["rag_context"] = "\n\n".join([
            f"[{c.chunk_id}] {c.content}" for c in chunks
        ])
        
        state["trace"].append({
            "node": "retriever",
            "chunks_found": len(chunks),
            "chunk_ids": [c.chunk_id for c in chunks]
        })
        
        return state
    
    def _plan_extraction(self, state: AgentState) -> AgentState:
        """Extract constraints and plan."""
        context = state.get("rag_context", "")
        result = self.planner(question=state["question"], context=context)
        
        try:
            constraints = {
                "date_ranges": result.date_ranges,
                "entities": result.entities,
                "kpi_formulas": result.kpi_formulas,
                "constraints": result.constraints
            }
        except:
            constraints = {
                "date_ranges": "",
                "entities": "",
                "kpi_formulas": "",
                "constraints": ""
            }
        
        state["constraints"] = constraints
        state["trace"].append({
            "node": "planner",
            "constraints": constraints
        })
        
        return state
    
    def _generate_sql(self, state: AgentState) -> AgentState:
        """Generate SQL query."""
        constraints_str = json.dumps(state["constraints"], indent=2)
        
        result = self.nl_to_sql(
            question=state["question"],
            schema=self.schema,
            constraints=constraints_str
        )
        
        sql = result.sql_query.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()
        
        state["sql_query"] = sql
        state["trace"].append({
            "node": "sql_generator",
            "sql": sql,
            "explanation": result.explanation
        })
        
        return state
    
    def _execute_sql(self, state: AgentState) -> AgentState:
        """Execute SQL query."""
        success, data, columns, error = self.db_tool.execute_query(state["sql_query"])
        
        state["sql_results"] = data
        state["sql_columns"] = columns
        state["sql_error"] = error
        
        state["trace"].append({
            "node": "executor",
            "success": success,
            "rows": len(data) if data else 0,
            "error": error
        })
        
        return state
    
    def _repair_sql(self, state: AgentState) -> AgentState:
        """Repair failed SQL query."""
        result = self.sql_repairer(
            original_query=state["sql_query"],
            error_message=state["sql_error"],
            schema=self.schema,
            question=state["question"]
        )
        
        sql = result.repaired_query.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()
        
        state["sql_query"] = sql
        state["repair_count"] += 1
        
        state["trace"].append({
            "node": "repairer",
            "repaired_sql": sql,
            "changes": result.changes,
            "repair_attempt": state["repair_count"]
        })
        
        return state
    
    def _synthesize_answer(self, state: AgentState) -> AgentState:
        """Synthesize final answer."""
        sql_results_str = ""
        if state.get("sql_results"):
            sql_results_str = json.dumps({
                "columns": state["sql_columns"],
                "rows": state["sql_results"]
            }, indent=2)
        
        result = self.synthesizer(
            question=state["question"],
            format_hint=state["format_hint"],
            sql_results=sql_results_str,
            rag_context=state.get("rag_context", "")
        )

        final_answer = self._parse_answer(result.final_answer, state["format_hint"])
        
        state["final_answer"] = final_answer
        state["explanation"] = result.explanation
        
        try:
            state["confidence"] = float(result.confidence)
        except:
            state["confidence"] = 0.5

        citations = self._extract_citations(state)
        state["citations"] = citations
        
        state["trace"].append({
            "node": "synthesizer",
            "final_answer": final_answer,
            "explanation": result.explanation
        })
        
        return state
    
    def _validate_output(self, state: AgentState) -> AgentState:
        """Validate output format and citations."""
        is_valid = state["final_answer"] is not None
        
        state["trace"].append({
            "node": "validator",
            "valid": is_valid
        })
        
        return state
    
    def _parse_answer(self, answer: str, format_hint: str) -> Any:
        """Parse answer according to format hint."""
        try:

            if answer.startswith("```"):
                lines = answer.split("\n")
                answer = "\n".join(lines[1:-1]) if len(lines) > 2 else answer
            
            if format_hint == "int":
                import re
                match = re.search(r'-?\d+', answer)
                return int(match.group()) if match else 0
            
            elif format_hint == "float":
                import re
                match = re.search(r'-?\d+\.?\d*', answer)
                return round(float(match.group()), 2) if match else 0.0
            
            elif format_hint.startswith("{") or format_hint.startswith("list["):
                try:
                    return json.loads(answer)
                except:
                    import re
                    json_match = re.search(r'(\{.*\}|\[.*\])', answer, re.DOTALL)
                    if json_match:
                        return json.loads(json_match.group(1))
                    return answer
            
            return answer
        except Exception as e:
            print(f"Parse error: {e}")
            return answer
    
    def _extract_citations(self, state: AgentState) -> List[str]:
        """Extract citations from state."""
        citations = []

        for chunk in state.get("rag_chunks", []):
            citations.append(chunk["chunk_id"])
        
        if state.get("sql_query"):
            sql = state["sql_query"].upper()
            tables = self.db_tool.get_table_names()
            for table in tables:
                if table.upper() in sql or f'"{table.upper()}"' in sql:
                    citations.append(table)
        
        return list(set(citations))
    
    def _route_decision(self, state: AgentState) -> str:
        """Decide routing."""
        return state["route"]
    
    def _needs_sql(self, state: AgentState) -> str:
        """Check if SQL is needed."""
        route = state["route"]
        return "yes" if route in ["sql", "hybrid"] else "no"
    
    def _check_sql_success(self, state: AgentState) -> str:
        """Check if SQL execution succeeded."""
        return "success" if not state.get("sql_error") else "error"
    
    def _check_repair_limit(self, state: AgentState) -> str:
        """Check if we should retry or give up."""
        return "retry" if state["repair_count"] < 2 else "give_up"
    
    def _check_validation(self, state: AgentState) -> str:
        """Check validation result."""
        return "valid"  
    
    def run(self, question: str, format_hint: str) -> Dict[str, Any]:
        """Run the agent on a question."""
        initial_state = AgentState(
            question=question,
            format_hint=format_hint,
            route="",
            rag_context="",
            rag_chunks=[],
            constraints={},
            sql_query="",
            sql_results=None,
            sql_columns=[],
            sql_error="",
            final_answer=None,
            explanation="",
            confidence=0.0,
            citations=[],
            repair_count=0,
            trace=[]
        )
        
        final_state = self.graph.invoke(initial_state)
        
        return {
            "final_answer": final_state["final_answer"],
            "sql": final_state.get("sql_query", ""),
            "confidence": final_state.get("confidence", 0.0),
            "explanation": final_state.get("explanation", ""),
            "citations": final_state.get("citations", []),
            "trace": final_state.get("trace", [])
        }
