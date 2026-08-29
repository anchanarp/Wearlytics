"""Configuration settings for the Wearlytics application."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base application configuration.

    All sensitive values are loaded exclusively from environment variables.
    Copy .env.example to .env and fill in your own values before running.
    """

    SECRET_KEY: str = os.environ["SECRET_KEY"]

    SQLALCHEMY_DATABASE_URI: str = os.environ["DATABASE_URL"]

    SQLALCHEMY_TRACK_MODIFICATIONS = False
