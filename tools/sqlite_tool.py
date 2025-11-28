import sqlite3
from typing import Dict, List, Any
import re


class SQLiteTool:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.schema_cache = None
    
    def get_schema(self) -> str:
        """Get database schema information"""
        if self.schema_cache:
            return self.schema_cache
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name NOT LIKE 'sqlite_%'
            ORDER BY name
        """)
        tables = cursor.fetchall()
        
        schema_parts = []
        for (table_name,) in tables:
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()
            
            col_defs = []
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                col_defs.append(f"{col_name} {col_type}")
            
            schema_parts.append(f"{table_name}({', '.join(col_defs)})")
        
        conn.close()
        
        self.schema_cache = "\n".join(schema_parts)
        return self.schema_cache
    
    def execute(self, query: str) -> Dict[str, Any]:
        """Execute SQL query and return results"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description] if cursor.description else []

            rows = cursor.fetchall()
            tables_used = self._extract_tables(query)
            
            return {
                "columns": columns,
                "rows": rows,
                "tables_used": tables_used,
                "success": True
            }
        
        except Exception as e:
            raise Exception(f"SQL execution error: {str(e)}")
        
        finally:
            conn.close()
    
    def _extract_tables(self, query: str) -> List[str]:
        """Extract table names used in query"""
        tables = set()
        known_tables = [
            "Orders", "Order Details", "Products", "Customers", 
            "Categories", "Suppliers", "Employees"
        ]
        
        query_upper = query.upper()
        for table in known_tables:
            if table.upper() in query_upper:
                tables.add(table)
        
        return sorted(list(tables))