# Script to create Supabase tables for user_data and guest_data
# Why: Ensures the required tables exist in Supabase before the application runs
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")

if not supabase_url or not supabase_key:
    logger.error('SUPABASE_URL or SUPABASE_ANON_KEY not set')
    exit(1)

supabase: Client = create_client(supabase_url, supabase_key)

def create_tables():
    """Create the required tables in Supabase"""
    
    # Create user_data table for Google-authenticated users
    user_data_sql = """
    CREATE TABLE IF NOT EXISTS user_data (
        id SERIAL PRIMARY KEY,
        google_id TEXT UNIQUE NOT NULL,
        email TEXT NOT NULL,
        first_name TEXT,
        last_name TEXT,
        avatar_url TEXT,
        patient_name TEXT,
        patient_age INTEGER,
        patient_gender TEXT,
        patient_language TEXT,
        patient_phone TEXT,
        chat_history JSONB DEFAULT '[]'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    # Create guest_data table for guest users
    guest_data_sql = """
    CREATE TABLE IF NOT EXISTS guest_data (
        id SERIAL PRIMARY KEY,
        session_id TEXT UNIQUE NOT NULL,
        patient_name TEXT,
        patient_age INTEGER,
        patient_gender TEXT,
        patient_language TEXT,
        patient_phone TEXT,
        chat_history JSONB DEFAULT '[]'::jsonb,
        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    """
    
    try:
        # Execute SQL to create tables
        logger.info("Creating user_data table...")
        supabase.rpc('exec_sql', {'sql': user_data_sql}).execute()
        logger.info("user_data table created successfully")
        
        logger.info("Creating guest_data table...")
        supabase.rpc('exec_sql', {'sql': guest_data_sql}).execute()
        logger.info("guest_data table created successfully")
        
        logger.info("All tables created successfully!")
        
    except Exception as e:
        logger.error(f"Error creating tables: {e}")
        logger.info("Tables might already exist or you might need to create them manually in Supabase dashboard")

if __name__ == "__main__":
    create_tables()

