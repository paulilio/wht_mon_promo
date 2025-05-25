import os
from dotenv import load_dotenv

# Carrega automaticamente o .env
load_dotenv()

API_KEY = os.getenv("API_KEY")
PHONE = os.getenv("PHONE")