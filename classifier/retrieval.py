# classifier/retrieval.py
import pandas as pd
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

# Загружаем модель и индекс при первом импорте
_model = None
_index = None
_df = None

def _load_resources():
    global _model, _index, _df
    if _model is None:
        _model = SentenceTransformer('intfloat/multilingual-e5-small')
        _index = faiss.read_index('classifier/data/goal_index.faiss')
        _df = pd.read_csv('classifier/data/labeled_data.csv')
    return _model, _index, _df

def retrieve_similar_goals(query_goal: str, k: int = 3):
    """Возвращает k наиболее похожих примеров из датасета (Goal, Target, Label)"""
    model, index, df = _load_resources()
    query_vec = model.encode([query_goal])
    distances, indices = index.search(query_vec.astype(np.float32), k)
    examples = []
    for idx in indices[0]:
        row = df.iloc[idx]
        examples.append({
            'goal': row['Goal'],
            'target': row['Target'],
            'label': int(row['Label'])
        })
    return examples