import sqlite3
import os
import logging
from typing import List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Locate the database file at the root of the backend folder
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "company_memory.db"))

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Create tasks table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        task TEXT NOT NULL,
        owner TEXT DEFAULT "",
        deadline TEXT DEFAULT "",
        source_message TEXT DEFAULT "",
        channel_id TEXT DEFAULT "",
        slack_user_id TEXT DEFAULT "",
        timestamp TEXT DEFAULT "",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    # Create decisions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS decisions (
        id TEXT PRIMARY KEY,
        decision TEXT NOT NULL,
        context TEXT DEFAULT "",
        source_message TEXT DEFAULT "",
        channel_id TEXT DEFAULT "",
        slack_user_id TEXT DEFAULT "",
        timestamp TEXT DEFAULT "",
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    
    conn.commit()
    conn.close()
    logger.info(f"SQLite database initialized successfully at: {DB_PATH}")

def insert_task(task_data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO tasks (id, task, owner, deadline, source_message, channel_id, slack_user_id, timestamp)
        VALUES (:id, :task, :owner, :deadline, :source_message, :channel_id, :slack_user_id, :timestamp)
        """, task_data)
        conn.commit()
        logger.info(f"Saved task {task_data['id']} to database: '{task_data['task']}'")
    except Exception as e:
        logger.error(f"Failed to insert task: {e}")
        raise e
    finally:
        conn.close()

def insert_decision(decision_data: Dict[str, Any]):
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        INSERT INTO decisions (id, decision, context, source_message, channel_id, slack_user_id, timestamp)
        VALUES (:id, :decision, :context, :source_message, :channel_id, :slack_user_id, :timestamp)
        """, decision_data)
        conn.commit()
        logger.info(f"Saved decision {decision_data['id']} to database: '{decision_data['decision']}'")
    except Exception as e:
        logger.error(f"Failed to insert decision: {e}")
        raise e
    finally:
        conn.close()

def fetch_all_tasks() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def fetch_all_decisions() -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM decisions ORDER BY created_at DESC")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def search_tasks(query: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    sql_query = """
    SELECT * FROM tasks 
    WHERE task LIKE ? OR owner LIKE ? OR deadline LIKE ?
    ORDER BY created_at DESC
    """
    search_term = f"%{query}%"
    cursor.execute(sql_query, (search_term, search_term, search_term))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def search_decisions(query: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    cursor = conn.cursor()
    sql_query = """
    SELECT * FROM decisions 
    WHERE decision LIKE ? OR context LIKE ?
    ORDER BY created_at DESC
    """
    search_term = f"%{query}%"
    cursor.execute(sql_query, (search_term, search_term))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def fetch_recent_items(days: int = 7) -> dict:
    """Fetch tasks and decisions from the last N days"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate the date threshold
    date_threshold = datetime.now() - timedelta(days=days)
    date_threshold_str = date_threshold.strftime("%Y-%m-%d %H:%M:%S")
    
    # Fetch recent tasks
    cursor.execute("""
        SELECT * FROM tasks 
        WHERE datetime(created_at) >= datetime(?)
        ORDER BY created_at DESC
    """, (date_threshold_str,))
    tasks = [dict(row) for row in cursor.fetchall()]
    
    # Fetch recent decisions
    cursor.execute("""
        SELECT * FROM decisions 
        WHERE datetime(created_at) >= datetime(?)
        ORDER BY created_at DESC
    """, (date_threshold_str,))
    decisions = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return {"tasks": tasks, "decisions": decisions}

def fetch_upcoming_deadlines() -> List[Dict[str, Any]]:
    """Fetch tasks with upcoming deadlines"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Fetch tasks with non-empty deadlines
    cursor.execute("""
        SELECT * FROM tasks 
        WHERE deadline != ''
        ORDER BY created_at DESC
    """)
    tasks = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return tasks
