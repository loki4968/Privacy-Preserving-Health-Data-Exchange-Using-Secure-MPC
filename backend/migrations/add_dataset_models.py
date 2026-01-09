"""
Database migration script to add DatasetDescriptor and VariableColumnMapping tables.
Run this script to update your database schema.
"""

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from config import DATABASE_URL, DATABASE_CONNECT_ARGS
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migration():
    """Add new tables for dataset descriptors and variable column mappings."""
    engine = create_engine(DATABASE_URL, connect_args=DATABASE_CONNECT_ARGS)
    
    with engine.connect() as conn:
        # Create dataset_descriptors table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS dataset_descriptors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                org_id INTEGER NOT NULL,
                name VARCHAR(255) NOT NULL,
                description VARCHAR(1000),
                file_path VARCHAR(500),
                schema TEXT NOT NULL,
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN NOT NULL DEFAULT 1,
                FOREIGN KEY (org_id) REFERENCES organizations(id)
            )
        """))
        
        # Create variable_column_mappings table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS variable_column_mappings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                computation_id VARCHAR NOT NULL,
                org_id INTEGER NOT NULL,
                dataset_id INTEGER,
                variable_id VARCHAR NOT NULL,
                column_name VARCHAR(255) NOT NULL,
                confidence_score REAL,
                mapping_method VARCHAR(50),
                created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                confirmed BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY (computation_id) REFERENCES secure_computations(computation_id),
                FOREIGN KEY (org_id) REFERENCES organizations(id),
                FOREIGN KEY (dataset_id) REFERENCES dataset_descriptors(id)
            )
        """))
        
        # Create indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_dataset_org ON dataset_descriptors(org_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mapping_computation ON variable_column_mappings(computation_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_mapping_org ON variable_column_mappings(org_id)"))
        
        conn.commit()
        logger.info("Migration completed successfully!")


if __name__ == "__main__":
    run_migration()

