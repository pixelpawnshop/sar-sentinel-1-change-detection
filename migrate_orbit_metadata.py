"""
Database migration script: Add orbit metadata columns to AOI table.

This migration adds three columns to support orbit-consistent change detection:
- orbit_direction: ASCENDING or DESCENDING
- relative_orbit_number: Sentinel-1 relative orbit (1-175)
- platform_number: Satellite identifier (A or C)

Run this script to update your existing database schema.
"""

import sqlite3
from pathlib import Path
from config import Config


def migrate_database():
    """Add orbit metadata columns to AOI table."""
    # Extract database path from SQLAlchemy URI
    db_path = Config.SQLALCHEMY_DATABASE_URI.replace('sqlite:///', '')
    
    if not Path(db_path).exists():
        print(f"Database not found: {db_path}")
        return False
    
    print(f"Migrating database: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check existing columns
        cursor.execute("PRAGMA table_info(aois)")
        existing_columns = [row[1] for row in cursor.fetchall()]
        print(f"   Existing AOI columns: {', '.join(existing_columns)}")
        
        # Add orbit_direction column if missing
        if 'orbit_direction' not in existing_columns:
            print("   Adding column: orbit_direction")
            cursor.execute("""
                ALTER TABLE aois 
                ADD COLUMN orbit_direction VARCHAR(20)
            """)
        else:
            print("   Column already exists: orbit_direction")
        
        # Add relative_orbit_number column if missing
        if 'relative_orbit_number' not in existing_columns:
            print("   Adding column: relative_orbit_number")
            cursor.execute("""
                ALTER TABLE aois 
                ADD COLUMN relative_orbit_number INTEGER
            """)
        else:
            print("   Column already exists: relative_orbit_number")
        
        # Add platform_number column if missing
        if 'platform_number' not in existing_columns:
            print("   Adding column: platform_number")
            cursor.execute("""
                ALTER TABLE aois 
                ADD COLUMN platform_number VARCHAR(10)
            """)
        else:
            print("   Column already exists: platform_number")
        
        conn.commit()
        
        # Verify changes
        cursor.execute("PRAGMA table_info(aois)")
        new_columns = [row[1] for row in cursor.fetchall()]
        
        print("\nMigration complete!")
        print(f"   Total AOI columns: {len(new_columns)}")
        print(f"   New columns added: orbit_direction, relative_orbit_number, platform_number")
        
        # Show AOI count
        cursor.execute("SELECT COUNT(*) FROM aois")
        aoi_count = cursor.fetchone()[0]
        print(f"\nFound {aoi_count} AOI(s) in database")
        
        if aoi_count > 0:
            print("\nNote: Existing AOIs have NULL orbit values.")
            print("   They will continue to work but won't use orbit filtering.")
            print("   Create new AOIs to enable orbit-consistent change detection.")
        
        return True
        
    except sqlite3.Error as e:
        print(f"\nMigration failed: {e}")
        conn.rollback()
        return False
        
    finally:
        conn.close()


if __name__ == '__main__':
    print("=" * 60)
    print("Orbit Metadata Migration")
    print("=" * 60)
    print()
    
    success = migrate_database()
    
    if success:
        print("\nDatabase migration successful!")
        print("   Restart your Flask app to use the updated schema.")
    else:
        print("\nMigration failed. Please check the error messages above.")
