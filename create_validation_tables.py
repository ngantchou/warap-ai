#!/usr/bin/env python3
"""
Create validation tables for the validation and improvement system
"""
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.validation_models import Base
from app.database import get_database_url

def create_validation_tables():
    """Create validation tables in the database"""
    
    # Get database URL
    database_url = get_database_url()
    
    # Create engine
    engine = create_engine(database_url)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    try:
        print("🔄 Creating validation tables...")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        
        # Verify tables were created
        with engine.connect() as conn:
            # Check validation_logs table
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%validation%' OR table_name LIKE '%error%' OR table_name LIKE '%improvement%'"))
            tables = [row[0] for row in result.fetchall()]
            
            print(f"✅ Created {len(tables)} validation tables:")
            for table in sorted(tables):
                print(f"   - {table}")
        
        print("\n🎉 Validation tables created successfully!")
        
    except Exception as e:
        print(f"❌ Error creating validation tables: {e}")
        raise
    
    finally:
        engine.dispose()

if __name__ == "__main__":
    create_validation_tables()