"""CLI helper for querying stored website analyses.

A thin, working alternative to backend/main.py. Kept for compatibility with
older commands; it uses the same DatabaseChatbot as the web API.
"""
import os
import sys

# Running this file directly puts backend/ on sys.path, not the project root.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from detect_url.backend.db_chatbot import DatabaseChatbot


def main():
    print("=" * 55)
    print("   Web Intelligence Assistant - stored detections")
    print("=" * 55)

    db_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "db"))
    os.makedirs(db_dir, exist_ok=True)

    try:
        bot = DatabaseChatbot(db_directory=db_dir)
    except Exception as exc:
        print(f"Failed to initialise: {exc}")
        return

    session_id = input("Enter session ID (or press Enter for 'default'): ").strip() or "default"

    print(f"\nReady. Session: {session_id}")
    print("Paste a URL to analyse it, or ask a question. Type 'exit' to quit.")

    while True:
        try:
            query = input(f"\n[{session_id}] You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break
        if not query:
            continue
        if query.lower() == "exit":
            print("Goodbye!")
            break
        try:
            print(f"\nAI: {bot.chat(query, session_id)}")
        except Exception as exc:
            print(f"\nError: {exc}")


if __name__ == "__main__":
    main()
