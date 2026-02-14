"""
Database migration script to add new columns.
Run this once to update existing database schema.
"""
import sqlite3
from config import Config

def migrate():
    """Add new columns to existing database."""
    conn = sqlite3.connect(Config.DATABASE_PATH)
    cursor = conn.cursor()
    
    print("Running database migration...")
    
    # Check if columns exist
    cursor.execute("PRAGMA table_info(analyses)")
    columns = [row[1] for row in cursor.fetchall()]
    
    changes_made = False
    
    # Add ref_image_url if missing
    if 'ref_image_url' not in columns:
        print("  Adding column: ref_image_url")
        cursor.execute("ALTER TABLE analyses ADD COLUMN ref_image_url VARCHAR(512)")
        changes_made = True
    else:
        print("  Column ref_image_url already exists")
    
    # Add new_image_url if missing
    if 'new_image_url' not in columns:
        print("  Adding column: new_image_url")
        cursor.execute("ALTER TABLE analyses ADD COLUMN new_image_url VARCHAR(512)")
        changes_made = True
    else:
        print("  Column new_image_url already exists")
    
    if changes_made:
        conn.commit()
        print("Migration complete!")
    else:
        print("Database already up to date!")
    
    conn.close()

if __name__ == '__main__':
    migrate()
