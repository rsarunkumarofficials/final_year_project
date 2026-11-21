import logging
import os
import queue
import sys
import threading

# Windows consoles default to cp1252; force UTF-8 so symbols in log/output
# cannot crash startup before the app is even created.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from detect_url.backend.db_chatbot import DatabaseChatbot
from detect_url.ml import inference as ml

load_dotenv()
logger = logging.getLogger("url_checker")

app = FastAPI(title="URL CHECKER API")


# --------------------------------------------------------------------------- #
# JSON-only error responses (no HTML error pages for API callers)
# --------------------------------------------------------------------------- #
def _json_error(status_code: int, message: str, detail: str | None = None) -> JSONResponse:
    content = {"status": "error", "message": message}
    if detail:
        content["detail"] = detail
    return JSONResponse(status_code=status_code, content=content)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException):
    return _json_error(exc.status_code, str(exc.detail))


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return _json_error(422, "Invalid request payload.", str(exc.errors())[:500])


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception):
    logger.exception("Unhandled API error: %s", exc)
    # Never leak internal exception text / file paths to the browser.
    return _json_error(500, "The server could not complete the request. Please try again.")


# --------------------------------------------------------------------------- #
# Optional supporting-context agent (ML verdict never depends on it)
# --------------------------------------------------------------------------- #
bot = None
if os.environ.get("GEMINI_API_KEY"):
    try:
        db_dir = os.path.join(os.path.dirname(__file__), "db")
        os.makedirs(db_dir, exist_ok=True)
        bot = DatabaseChatbot(db_directory=db_dir)
    except Exception:
        logger.exception("Could not initialise the supporting-context agent")
else:
    logger.warning("GEMINI_API_KEY is not set; supporting context will be unavailable.")


class ChatRequest(BaseModel):
    url_or_prompt: str
    session_id: str = "default"


def _chat_with_timeout(prompt: str, session_id: str, timeout: float = 25.0) -> str:
    """Run the optional LLM step in a daemon thread so it cannot hang a scan."""
    if bot is None:
        return "Supporting context unavailable: GEMINI_API_KEY is not configured."

    result: queue.Queue = queue.Queue(maxsize=1)

    def worker():
        try:
            result.put((True, bot.chat(prompt, session_id)))
        except Exception as exc:  # noqa: BLE001 - reported to the user as context
            result.put((False, str(exc)))

    threading.Thread(target=worker, daemon=True, name="gemini-context").start()
    try:
        ok, value = result.get(timeout=timeout)
    except queue.Empty:
        return "Supporting context unavailable: the analysis timed out."

    if ok:
        return value
    logger.warning("Supporting-context agent failed: %s", value)
    return "Supporting context unavailable: the analysis service returned an error."


# --------------------------------------------------------------------------- #
# API routes
# --------------------------------------------------------------------------- #
@app.get("/api/health")
def health():
    return {"status": "ok", "supporting_context": bot is not None}


@app.post("/api/predict")
def predict_url(request: ChatRequest):
    if not request.url_or_prompt or not request.url_or_prompt.strip():
        return _json_error(400, "Enter a URL or a question before scanning.")

    # 1. ML verdict — authoritative. Always JSON, even on failure.
    try:
        ml_result = ml.predict(request.url_or_prompt.strip())
    except Exception as exc:
        logger.exception("Model inference failed")
        return _json_error(
            500,
            "The classifier could not analyse this URL. Please try again.",
            f"{type(exc).__name__}",
        )

    # 2. Model card.
    try:
        model_card = ml.model_info()
    except Exception:
        logger.exception("Could not load model metrics")
        model_card = {"model": "weighted_ensemble", "accuracy": None}

    # 3. Optional scraper / Gemini context. Failure is never fatal.
    supporting_context = _chat_with_timeout(
        request.url_or_prompt.strip(), request.session_id
    )

    return {
        "status": "success",
        "response": supporting_context,
        "ml": ml_result,
        "model": model_card,
    }


@app.get("/api/model")
def model_status():
    try:
        return ml.model_info()
    except Exception as exc:
        logger.exception("Could not load model metrics")
        return _json_error(500, "Model information is unavailable.", f"{type(exc).__name__}")


@app.api_route("/api/{path:path}", methods=["GET", "POST", "PUT", "PATCH", "DELETE"])
def unknown_api_route(path: str):
    return _json_error(404, f"Unknown API endpoint: /api/{path}")


# Serve the Frontend Files (One Service Architecture)
website_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../website"))

# Serve the main index.html and all static assets automatically at the root level
app.mount("/", StaticFiles(directory=website_dir, html=True), name="website")
