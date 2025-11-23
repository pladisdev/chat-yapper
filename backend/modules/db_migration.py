"""
Database Migration System for Chat Yapper

This module handles database schema migrations when the application is updated.
It safely adds new columns to existing tables without losing data.
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any

from modules import logger

def get_table_columns(conn: sqlite3.Connection, table_name: str) -> List[str]:
    """Get list of column names for a table"""
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return columns


def column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table"""
    columns = get_table_columns(conn, table_name)
    return column_name in columns


def add_column_if_missing(conn: sqlite3.Connection, table_name: str, column_name: str, 
                          column_type: str, default_value: Any = None) -> bool:
    """
    Add a column to a table if it doesn't exist.
    Returns True if column was added, False if it already existed.
    """
    if column_exists(conn, table_name, column_name):
        logger.info(f"Column '{column_name}' already exists in table '{table_name}'")
        return False
    
    # Build ALTER TABLE statement
    alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
    
    # Add DEFAULT clause if provided
    if default_value is not None:
        if isinstance(default_value, str):
            alter_sql += f" DEFAULT '{default_value}'"
        elif isinstance(default_value, bool):
            alter_sql += f" DEFAULT {1 if default_value else 0}"
        else:
            alter_sql += f" DEFAULT {default_value}"
    
    try:
        conn.execute(alter_sql)
        conn.commit()
        logger.info(f"Added column '{column_name}' to table '{table_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to add column '{column_name}' to table '{table_name}': {e}")
        conn.rollback()
        return False


def migrate_voice_table(conn: sqlite3.Connection) -> None:
    """Migrate the Voice table to add any missing columns"""
    logger.info("Checking Voice table schema...")
    
    migrations = [
        # Column: (name, type, default_value)
        ("avatar_default", "TEXT", None),
        ("avatar_speaking", "TEXT", None),
        ("avatar_mode", "TEXT", "single"),
        ("created_at", "TEXT", None),
    ]
    
    changes_made = False
    for col_name, col_type, default in migrations:
        if add_column_if_missing(conn, "voice", col_name, col_type, default):
            changes_made = True
    
    if not changes_made:
        logger.info("Voice table schema is up to date")


def migrate_avatarimage_table(conn: sqlite3.Connection) -> None:
    """Migrate the AvatarImage table to add any missing columns"""
    logger.info("Checking AvatarImage table schema...")
    
    migrations = [
        # Column: (name, type, default_value)
        ("upload_date", "TEXT", None),
        ("file_size", "INTEGER", None),
        ("avatar_type", "TEXT", "default"),
        ("avatar_group_id", "TEXT", None),
        ("voice_id", "INTEGER", None),
        ("spawn_position", "INTEGER", None),
        ("disabled", "INTEGER", 0),  # Boolean field (SQLite uses INTEGER for bool, default False)
    ]
    
    changes_made = False
    for col_name, col_type, default in migrations:
        if add_column_if_missing(conn, "avatarimage", col_name, col_type, default):
            changes_made = True
    
    if not changes_made:
        logger.info("AvatarImage table schema is up to date")


def migrate_avatarslot_table(conn: sqlite3.Connection) -> None:
    """Add new columns to AvatarSlot table if they don't exist"""
    logger.info("Checking AvatarSlot table schema...")
    
    # List of migrations: (column_name, column_type, default_value)
    migrations = [
        ("voice_id", "INTEGER", None),  # Voice assignment for this slot (None = random)
    ]
    
    changes_made = False
    for col_name, col_type, default in migrations:
        if add_column_if_missing(conn, "avatarslot", col_name, col_type, default):
            changes_made = True
    
    if not changes_made:
        logger.info("AvatarSlot table schema is up to date")


def run_all_migrations(db_path: str) -> None:
    """
    Run all database migrations.
    This should be called before SQLModel.metadata.create_all()
    """
    logger.info(f"Starting database migration check for: {db_path}")
    
    # Check if database exists
    if not Path(db_path).exists():
        logger.info("Database doesn't exist yet - will be created fresh")
        return
    
    try:
        # Connect directly with sqlite3 for migrations
        conn = sqlite3.connect(db_path)
        
        # Check if tables exist
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Existing tables: {existing_tables}")
        
        # Run migrations for each table
        if "voice" in existing_tables:
            migrate_voice_table(conn)
        else:
            logger.info("Voice table doesn't exist yet - will be created")
        
        if "avatarimage" in existing_tables:
            migrate_avatarimage_table(conn)
        else:
            logger.info("AvatarImage table doesn't exist yet - will be created")
        
        if "avatarslot" in existing_tables:
            migrate_avatarslot_table(conn)
        else:
            logger.info("AvatarSlot table doesn't exist yet - will be created")
        
        conn.close()
        logger.info("Database migration check completed successfully")
        
    except Exception as e:
        logger.error(f"Error during database migration: {e}")
        raise


def get_database_info(db_path: str) -> Dict[str, Any]:
    """Get information about the database for debugging"""
    if not Path(db_path).exists():
        return {"exists": False}
    
    conn = sqlite3.connect(db_path)
    
    # Get all tables
    cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = [row[0] for row in cursor.fetchall()]
    
    # Get column info for each table
    table_info = {}
    for table in tables:
        columns = get_table_columns(conn, table)
        cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]
        table_info[table] = {
            "columns": columns,
            "row_count": row_count
        }
    
    conn.close()
    
    return {
        "exists": True,
        "path": db_path,
        "tables": table_info
    }
