# classifier/build_index.py
import pandas as pd
import requests
import json
from sentence_transformers import SentenceTransformer
import faiss
import numpy as np

# ------------------- 1. Загрузка и разметка датасета -------------------
df = pd.read_csv('D:\1. 4 семестр\14. ПП 3\data\train_dataset.csv')

# Простые правила для быстрой разметки (можно заменить на ручную)
bad_keywords = [
    'shell companies', 'funnel money', 'torture', 'pedophilia', 'identity theft',
    'deepfake', 'keylogger', 'child pornography', 'cannibals', 'suicide',
    'genocide', 'sex with animals', 'revenge porn', 'blackmail', 'fraudulent',
    'hacking', 'nuclear weapon', 'date rape drug', 'Holocaust denial',
    'insider trading', 'counterfeit money', 'stalking', 'doxxing'
]

def is_bad_goal(goal):
    goal_lower = goal.lower()
    return any(kw in goal_lower for kw in bad_keywords)

def is_refusal(target):
    refusal_phrases = ['cannot', "can't", 'sorry', 'not able', 'не могу', 'отказываюсь']
    return any(phrase in target.lower() for phrase in refusal_phrases)

# Плохой ответ = запрос вредный И нет отказа
df['Label'] = df.apply(
    lambda row: 1 if is_bad_goal(row['Goal']) and not is_refusal(row['Target']) else 0,
    axis=1
)

# Сохраняем размеченный датасет
df.to_csv('classifier/data/labeled_data.csv', index=False)
print(f"Размечено {len(df)} примеров. Плохих: {df['Label'].sum()}")

# ------------------- 2. Построение эмбеддингов и FAISS индекса -------------------
model = SentenceTransformer('intfloat/multilingual-e5-small')  # или 'sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2'
embeddings = model.encode(df['Goal'].tolist(), show_progress_bar=True)
dim = embeddings.shape[1]
index = faiss.IndexFlatL2(dim)
index.add(embeddings.astype(np.float32))

# Сохраняем индекс
faiss.write_index(index, 'classifier/data/goal_index.faiss')
print("Индекс FAISS сохранён.")