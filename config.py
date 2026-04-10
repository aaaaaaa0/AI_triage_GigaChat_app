from pathlib import Path

BASE_DIR = Path(__file__).parent

DATA_DIR = BASE_DIR / "classifier" / "data"
DATASET_PATH = DATA_DIR / "train_dataset.csv"
LABELED_PATH = DATA_DIR / "labeled_data.csv"
FAISS_INDEX_PATH = DATA_DIR / "goal_index.faiss"

DB_PATH = BASE_DIR / "chat_history.db"