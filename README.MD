# Инструкция по запуску приложения "Классификатор ответов GigaChat"

## Требования

- Операционная система: Windows / macOS / Linux  
- Установленный Python версии 3.10 или выше  
- Установленный Git (для клонирования репозитория)  
- Доступ в интернет (для скачивания моделей и работы с API)  

### Аккаунты и API-ключи:
- **GigaChat** – получить на https://developers.sber.ru  
- **OpenRouter** – получить на https://openrouter.ai/keys (бесплатный)  
- (опционально) **OpenAI** – для Moderation API (можно пропустить)  

---

## 1. Клонирование репозитория

```bash
git clone https://github.com/letter-generator/AI_triage_GigaChat.git
cd AI_triage_GigaChat

2. Создание и активация виртуального окружения
Windows:


python -m venv .venv
.venv\Scripts\activate
