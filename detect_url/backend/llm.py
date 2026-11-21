import os

from langchain_google_genai import ChatGoogleGenerativeAI


def get_llm(model: str = "gemini-3.8-flash", **kwargs):
    """Return a Gemini chat model for the LangGraph assistant."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Copy .env.example to .env and add your key, "
            "or set the environment variable before starting."
        )

    return ChatGoogleGenerativeAI(
        model=model,
        api_key=api_key,
        temperature=0,
        retries=1,
        request_timeout=30,
    )
