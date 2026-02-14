"""Quick verification of orbit metadata migration."""
from models import AOI
from config import Config
from sqlalchemy import create_engine, inspect

engine = create_engine(Config.SQLALCHEMY_DATABASE_URI)
inspector = inspect(engine)
columns = inspector.get_columns('aois')

print("AOI Table Columns:")
for col in columns:
    print(f"  - {col['name']}: {col['type']}")

print("\nOrbit columns present:" if any(col['name'] == 'orbit_direction' for col in columns) else "\nOrbit columns missing!")
