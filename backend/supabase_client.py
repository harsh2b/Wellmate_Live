# Updated: Removed Google login related classes and functions.
# Why: User requested to remove Google login and keep only guest feature.
from supabase import create_client, Client
from dotenv import load_dotenv
import os
from pydantic import BaseModel
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load .env from root directory
load_dotenv()
logger.info("Environment variables loaded")

supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_ANON_KEY")
if not supabase_url or not supabase_key:
    logger.error("SUPABASE_URL or SUPABASE_ANON_KEY not set")
    raise ValueError("SUPABASE_URL or SUPABASE_ANON_KEY not set in .env")

supabase: Client = create_client(supabase_url, supabase_key)
logger.info("Supabase client initialized")

class GuestData(BaseModel):
    session_id: str
    patient_name: str | None = None
    patient_age: int | None = None
    patient_gender: str | None = None
    patient_language: str | None = None
    patient_phone: str | None = None
    chat_history: list = []

def create_guest_data(guest_data: dict):
    """Create guest data for guest users"""
    logger.info("Creating guest data: %s", guest_data)
    data = GuestData(**guest_data).dict(exclude_unset=True)
    try:
        response = supabase.table("guest_data").insert(data).execute()
        logger.info("Guest data created: %s", response.data)
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error creating guest data: %s", e)
        return None

def get_guest_data_by_session_id(session_id: str):
    """Get guest data by session ID"""
    logger.info("Fetching guest data for session_id: %s", session_id)
    try:
        response = supabase.table("guest_data").select("*").eq("session_id", session_id).execute()
        logger.info("Guest data retrieved: %s", response.data)
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error getting guest data: %s", e)
        return None

def update_guest_data(session_id: str, guest_data: dict):
    """Update guest data by session ID"""
    logger.info("Updating guest data for session_id: %s, data: %s", session_id, guest_data)
    data = GuestData(**guest_data).dict(exclude_unset=True)

    if 'session_id' in guest_data:
        del guest_data['session_id']  # Remove session_id from update data
    try:
        response = supabase.table("guest_data").update(data).eq("session_id", session_id).execute()
        logger.info("Guest data updated: %s", response.data)
        return response.data[0] if response.data else None
    except Exception as e:
        logger.error("Error updating guest data: %s", e)
        return None

