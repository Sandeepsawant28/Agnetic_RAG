import os
from dotenv import load_dotenv

load_dotenv()

LLM_BASE_URL = os.getenv("LLM_BASE_URL")
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_MODEL = os.getenv("LLM_MODEL")

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
CHROMA_DIR = "data/chroma"
WORKSPACE_DIR = "data/repos"