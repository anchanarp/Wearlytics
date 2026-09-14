"""Configuration settings for the Wearlytics application."""

import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base application configuration.

    All sensitive values are loaded exclusively from environment variables.
    Copy .env.example to .env and fill in your own values before running.
    """

    # Load and sanitize the database URL
    _raw_db_url: str = os.getenv("DATABASE_URL")
    if _raw_db_url is None:
        # Fallback to a local SQLite database for testing / development when no DB URL is provided.
        SQLALCHEMY_DATABASE_URI: str = "sqlite:///wearlytics_dev.db"
    else:
        # Prefer TCP, but fall back to Unix socket if needed (common on macOS)
        if "localhost" in _raw_db_url:
            socket_path = "/tmp/mysql.sock"
            if os.path.exists(socket_path):
                # Construct URL using Unix socket, preserving credentials and database name
                creds_part = _raw_db_url.split('://', 1)[1].split('@')[0]
                db_name = _raw_db_url.rsplit('/', 1)[-1]
                SQLALCHEMY_DATABASE_URI: str = f"mysql+pymysql://{creds_part}@/{db_name}?unix_socket={socket_path}"
            else:
                # Fallback to TCP with 127.0.0.1
                SQLALCHEMY_DATABASE_URI: str = _raw_db_url.replace("localhost", "127.0.0.1")
        else:
            SQLALCHEMY_DATABASE_URI: str = _raw_db_url

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key")

    SQLALCHEMY_TRACK_MODIFICATIONS = False
