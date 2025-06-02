import os
from dotenv import load_dotenv

# Carrega automaticamente o .env
load_dotenv()

API_KEY = os.getenv("API_KEY")
PHONE = os.getenv("PHONE")
FIREBASE_BASE_URL = os.getenv("FIREBASE_BASE_URL")
FIREBASE_CREDENTIAL_PATH = os.getenv("FIREBASE_CREDENTIAL_PATH")
TG_API_ID = os.getenv("TG_API_ID")
TG_API_HASH = os.getenv("TG_API_HASH")
TG_CHANNEL = os.getenv("TG_CHANNEL")