import os
import pathlib

class Settings:
    SECRET_KEY = os.environ.get("URLSHORTNER_SECRET_KEY")
    DB_FILE = pathlib.Path("urls.yaml")
    DOMAIN = os.environ.get("URLSHORTNER_URL", "https://short.flatos")

    FLASK_DEBUG = os.environ.get("FLASK_DEBUG", False)

settings = Settings()