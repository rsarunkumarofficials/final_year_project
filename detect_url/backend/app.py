import os
import sys

# Windows consoles default to cp1252; force UTF-8 so symbols in log/output
# cannot crash startup before the app is even created.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from detect_url.backend.db_chatbot import DatabaseChatbot
from detect_url.ml import inference as ml

load_dotenv()

if not os.environ.get("GEMINI_API_KEY"):
    raise RuntimeError("GEMINI_API_KEY must be set before starting the app")

app = FastAPI()

# Initialize Chatbot
db_dir = os.path.join(os.path.dirname(__file__), "db")
os.makedirs(db_dir, exist_ok=True)
bot = DatabaseChatbot(db_directory=db_dir)

class ChatRequest(BaseModel):
    url_or_prompt: str
    session_id: str = "default"

# 1. ML classifier verdict + scraper/LLM explanation for the frontend
@app.post("/api/predict")
def predict_url(request: ChatRequest):
    try:
        ml_result = ml.predict(request.url_or_prompt)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": f"Model inference failed: {e}"},
        )

    # Scraper + LangGraph/Claude add context and explanation. If the LLM step
    # is unavailable, the ML verdict is still returned (it is authoritative).
    try:
        response = bot.chat(request.url_or_prompt, request.session_id)
    except Exception as e:
        response = f"Scrape/LLM explanation unavailable: {e}"

    return {
        "status": "success",
        "response": response,
        "ml": ml_result,
        "model": ml.model_info(),
    }


# Model card / honest performance numbers, useful for verification
@app.get("/api/model")
def model_status():
    return ml.model_info()

# Serve the Frontend Files (One Service Architecture)
website_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../website"))

# Serve the main index.html and all static assets automatically at the root level
app.mount("/", StaticFiles(directory=website_dir, html=True), name="website")
