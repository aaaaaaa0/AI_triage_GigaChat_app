import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification
from typing import Dict, Any

_model = None
_tokenizer = None

def load_toxicity_model():
    """Загружает модель и токенизатор (кэширует)"""
    global _model, _tokenizer
    if _model is None:
        model_id = 'tinkoff-ai/response-toxicity-classifier-base'
        _tokenizer = AutoTokenizer.from_pretrained(model_id)
        _model = AutoModelForSequenceClassification.from_pretrained(model_id)
        _model.eval()
        if torch.cuda.is_available():
            _model.cuda()
    return _model, _tokenizer

def analyze_toxicity(text: str) -> Dict[str, Any]:
    """Анализирует текст и возвращает результат с пояснением"""
    model, tokenizer = load_toxicity_model()
    
    inputs = tokenizer(
        text,
        max_length=128,
        truncation=True,
        padding=True,
        return_tensors='pt'
    )
    if torch.cuda.is_available():
        inputs = {k: v.cuda() for k, v in inputs.items()}
    
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()[0]
    
    # Индексы: 0 - OK, 1 - Toxic, 2 - Severe toxic, 3 - Risks
    labels = {
        0: "OK - безопасно",
        1: "TOXIC - оскорбительно",
        2: "SEVERE TOXIC - сильно оскорбительно",
        3: "RISKS - чувствительные темы"
    }
    pred_id = probs.argmax()
    pred_label = labels[pred_id]
    confidence = probs[pred_id]
    
    explanation = f"Модель токсичности: {pred_label}. Уверенность: {confidence:.2%}."
    
    return {
        "label": pred_id,
        "label_name": pred_label,
        "confidence": float(confidence),
        "explanation": explanation,
        "all_probabilities": {labels[i]: float(p) for i, p in enumerate(probs)}
    }