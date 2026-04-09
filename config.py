import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
MODELS_DIR = os.path.join(BASE_DIR, "models")

DB_PATH = os.path.join(DATA_DIR, "dialogues.db")
DATASET_PATH = os.path.join(DATA_DIR, "dataset.csv")
CLASSIFIER_MODEL_PATH = os.path.join(MODELS_DIR, "classifier.pkl")
VECTORIZER_PATH = os.path.join(MODELS_DIR, "vectorizer.pkl")

from pathlib import Path

GIGACHAT_TOKEN = 'MDE5YjRhOTItODU3OS03YzQ0LWIwZmMtYWI3NTMyYThhMmVhOmI3YWI5MDJhLWFhNTQtNDVmYy1iNjJmLTVjNGMwODJhNTA4MA=='

BASE_DIR = Path("C:\\PROJECT\\ai-agent")
DATA_DIR = BASE_DIR / "data"
FAISS_DIR = BASE_DIR / "faiss_index"
RAW_FILE = DATA_DIR / "raw.jsonl"
CHUNKS_FILE = DATA_DIR / "clean.jsonl"
RAW_OUTPUT = DATA_DIR / "raw.jsonl"