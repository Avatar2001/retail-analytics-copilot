"""SQLite tool for database access and schema introspection."""
import sqlite3
from typing import Dict, List, Any, Tuple
from pathlib import Path


class SQLiteTool:
    """Tool for interacting with SQLite database."""
    
    def __init__(self, db_path: str):
        """Initialize with database path."""
        self.db_path = Path(db_path)
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found: {db_path}")
    
    def get_schema(self) -> str:
        """Get database schema information."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all tables
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        
        schema_info = []
        for table in tables:
            # Get table schema
            cursor.execute(f"PRAGMA table_info({table});")
            columns = cursor.fetchall()
            
            col_info = []
            for col in columns:
                col_name = col[1]
                col_type = col[2]
                col_info.append(f"  {col_name} {col_type}")
            
            schema_info.append(f"Table: {table}\n" + "\n".join(col_info))
        
        conn.close()
        return "\n\n".join(schema_info)
    
    def get_table_names(self) -> List[str]:
        """Get list of all table names."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()
        return tables
    
    def execute_query(self, query: str) -> Tuple[bool, Any, List[str], str]:
        """
        Execute SQL query and return results.
        
        Returns:
            Tuple of (success, data, columns, error_message)
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query)
            
            # Get column names
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            
            # Fetch results
            results = cursor.fetchall()
            conn.close()
            
            return True, results, columns, ""
        except Exception as e:
            return False, None, [], str(e)
    
    def get_sample_data(self, table: str, limit: int = 3) -> List[Dict[str, Any]]:
        """Get sample data from a table."""
        success, data, columns, error = self.execute_query(
            f"SELECT * FROM {table} LIMIT {limit};"
        )
        
        if not success:
            return []
        
        return [dict(zip(columns, row)) for row in data]
    
    def create_views(self):
        """Create lowercase compatibility views."""
        conn = sqlite3.connect(self.db_path)
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
            except Exception as e:
                print(f"Warning creating view: {e}")
        
        conn.commit()
        conn.close()
