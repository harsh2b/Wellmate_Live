# Updated: Removed Google login functionality, focusing on guest users.
# Why: User requested to remove Google login and keep only guest feature.
from langchain_community.chat_message_histories import ChatMessageHistory
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import os
from chatbot import generate_response
from starlette.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.middleware.sessions import SessionMiddleware
from supabase_client import (
    create_guest_data, get_guest_data_by_session_id, update_guest_data
)
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()
logger.info("Environment variables loaded in main.py")

# Initialize FastAPI app
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key=os.getenv("SECRET_KEY", "your-secret-key"))

# Configure CORS - Updated to include the sandbox domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000", "http://127.0.0.1:8000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORS middleware configured")

# Mount static files
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "../static")
logger.info(f"Static directory: {STATIC_DIR}")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Pydantic models for request validation
class PatientInfo(BaseModel):
    name: str
    age: int
    gender: str
    language: str
    phone: str

class ChatRequest(BaseModel):
    session_id: str
    message: str

# Test endpoint to verify server is running
@app.get("/test")
def test_endpoint():
    return {"status": "Server is running", "message": "Test endpoint reached"}

# Serve login page as root
@app.get("/")
def read_root():
    logger.info("Serving root: /static/login_classic.html")
    return FileResponse(os.path.join(STATIC_DIR, "login_classic.html"))

# Update patient info endpoint
@app.post("/update-patient")
async def update_patient_info(request: Request):
    data = await request.json()
    logger.info(f"Received /update-patient request: {data}")
    session_id = data.get("session_id")
    patient_info = data.get("patient_info")
    
    if not session_id:
        logger.error("Error: Session ID is missing")
        raise HTTPException(status_code=400, detail="Session ID is required")

    if not patient_info or not isinstance(patient_info, dict):
        logger.error("Error: Invalid patient info")
        raise HTTPException(status_code=400, detail="Invalid patient info")
    
    required_fields = {"name": "Unknown", "age": 0, "gender": "Unknown", "language": "English", "phone": ""}
    updated_info = {key: patient_info.get(key, default) for key, default in required_fields.items()}
    updated_info["age"] = int(updated_info["age"]) if isinstance(updated_info["age"], (str, int)) else 0

    # Guest user logic - Store in Supabase
    guest_data = get_guest_data_by_session_id(session_id)
    if not guest_data:
        # Create new guest data in Supabase
        new_guest_data = {
            "session_id": session_id,
            "patient_name": updated_info["name"],
            "patient_age": updated_info["age"],
            "patient_gender": updated_info["gender"],
            "patient_language": updated_info["language"],
            "patient_phone": updated_info["phone"],
            "chat_history": []
        }
        guest_data = create_guest_data(new_guest_data)
        logger.info(f"Created new guest data for session: {session_id}")
    else:
        # Update existing guest data
        guest_data["patient_name"] = updated_info["name"]
        guest_data["patient_age"] = updated_info["age"]
        guest_data["patient_gender"] = updated_info["gender"]
        guest_data["patient_language"] = updated_info["language"]
        guest_data["patient_phone"] = updated_info["phone"]
        update_guest_data(session_id, guest_data)
        logger.info(f"Updated patient info for guest session: {session_id}, {updated_info}")

    return {"status": "success"}

# Chat endpoint
@app.post("/chat")
async def chat(chat_request: ChatRequest, request: Request):
    logger.info(f"Received /chat request: {chat_request.dict()}")
    session_id = chat_request.session_id
    user_message = chat_request.message

    patient_info = {}
    chat_history = ChatMessageHistory()

    # Guest user logic - Use Supabase
    guest_data = get_guest_data_by_session_id(session_id)
    if guest_data:
        patient_info = {
            "name": guest_data.get("patient_name", "Guest"),
            "age": guest_data.get("patient_age", 0),
            "gender": guest_data.get("patient_gender", "Unknown"),
            "language": guest_data.get("patient_language", "English"),
            "phone": guest_data.get("patient_phone", "")
        }
        # Reconstruct ChatMessageHistory from stored chat_history
        for msg in guest_data.get("chat_history", []):
            if msg["type"] == "human":
                chat_history.add_user_message(msg["content"])
            elif msg["type"] == "ai":
                chat_history.add_ai_message(msg["content"])
    else:
        logger.error(f"Error: Guest session not found for ID: {session_id}")
        raise HTTPException(status_code=404, detail="Session not found")

    logger.info(f"Session data for chat: Patient Info: {patient_info}, Chat History Length: {len(chat_history.messages)}")

    default_info = {"name": "Unknown", "age": 0, "gender": "Unknown", "language": "English", "phone": ""}
    for key, default in default_info.items():
        if key not in patient_info:
            patient_info[key] = default
    patient_info["age"] = int(patient_info["age"]) if isinstance(patient_info["age"], (str, int)) else 0

    system_prompt = (
        "You are a female physician with 30 years of experience in general practice; your name is Dr. Black. "
        f"IMPORTANT PATIENT INFO: The patient\'s name is {patient_info['name']}, age {patient_info['age']}, gender {patient_info['gender']}. "
        f"You MUST always respond in the patient\'s preferred language ({patient_info['language']}) using simple, clear sentences. "
        f"Always consider the patient\'s age ({patient_info['age']}) and gender ({patient_info['gender']}) in your responses. "
        "Act as a doctor: ask clarifying questions to understand symptoms before diagnosing or prescribing. "
        "NEVER use apologetic sentences like \"Sorry to hear that...\". "
        "You MUST use retrieved documents if they exist; otherwise, say \"I don\'t know\". "
        "DO NOT suggest visiting your clinic, but DO NOT forget to prescribe medicine if needed after a full consultation. "
        "When prescribing medicine, ALWAYS include how to use it (e.g., dosage and timing) and how many days to take it. "
        "Use positive vibes and emojis (e.g., 😊) appropriately. "
        "During prescribe must use context : {context}"
    )

    logger.info(f"Calling generate_response with user_message: {user_message}")
    try:
        bot_response = generate_response(system_prompt, chat_history, user_message)
        logger.info(f"Bot response: {bot_response}")

        # Guest user - update guest_data
        guest_data["chat_history"].append({"type": "human", "content": user_message})
        guest_data["chat_history"].append({"type": "ai", "content": bot_response})
        update_guest_data(session_id, {"session_id": session_id, "chat_history": guest_data["chat_history"]})
        logger.info(f"Chat history updated for guest user {session_id}.")

        return {"response": bot_response}
    except Exception as e:
        logger.error(f"Error in /chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {e}")

@app.post("/logout")
async def logout(request: Request):
    session_id = request.session.get("session_id")
    if session_id:
        # Clear session data
        request.session.clear()
        logger.info(f"User {session_id} logged out.")
    return RedirectResponse(url="/")



