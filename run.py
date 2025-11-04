#!/usr/bin/env python3
"""
Run the URL Shortener application.

Usage:
    python run.py              # Development mode with auto-reload
    python run.py --prod       # Production mode
"""

import sys
import uvicorn


def main():
    """Run the application."""
    is_prod = "--prod" in sys.argv

    if is_prod:
        print("Starting in PRODUCTION mode...")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            workers=4,
            log_level="info"
        )
    else:
        print("Starting in DEVELOPMENT mode...")
        uvicorn.run(
            "app.main:app",
            host="0.0.0.0",
            port=8000,
            reload=True,
            log_level="debug"
        )


if __name__ == "__main__":
    main()
