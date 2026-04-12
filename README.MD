напиши мне это ПОЛНОСТЬЮ В ФОРМАТЕ МАРКДАУН

Ниже представлена инструкция по запуску приложения в формате Markdown. Вы можете сохранить её в файл README.md или в отдельный документ.

markdown
# Инструкция по запуску приложения "Классификатор ответов GigaChat"

## Требования

- Операционная система: Windows / macOS / Linux
- Установленный Python версии 3.10 или выше
- Установленный Git (для клонирования репозитория)
- Доступ в интернет (для скачивания моделей и работы с API)
- Аккаунты и API-ключи:
  - **GigaChat** – получить на [developers.sber.ru](https://developers.sber.ru)
  - **OpenRouter** – получить на [openrouter.ai/keys](https://openrouter.ai/keys) (бесплатный)
  - (опционально) **OpenAI** – для Moderation API (можно пропустить)

## 1. Клонирование репозитория

```bash
git clone https://github.com/letter-generator/AI_triage_GigaChat.git
cd AI_triage_GigaChat
2. Создание и активация виртуального окружения
Windows:

bash
python -m venv .venv
.venv\Scripts\activate
macOS / Linux:

bash
python3 -m venv .venv
source .venv/bin/activate
3. Установка зависимостей
bash
pip install --upgrade pip
pip install -r requirements.txt
Если файла requirements.txt нет в репозитории, создайте его со следующим содержимым:

text
streamlit>=1.56.0
requests>=2.33.1
pandas>=3.0.2
numpy>=2.4.4
sentence-transformers>=5.3.0
faiss-cpu>=1.13.2
torch>=2.11.0
torchvision>=0.26.0
transformers>=5.5.0
scikit-learn>=1.8.0
openai>=1.70.0
4. Подготовка данных и FAISS-индекса
Перед первым запуском необходимо построить FAISS-индекс и размеченный датасет.

Убедитесь, что файл classifier/data/train_dataset.csv существует (в репозитории есть пример).
Если файла нет, создайте его с колонками Goal и Target.

Запустите скрипт сборки индекса:

bash
python classifier/build_index.py
Скрипт создаст файлы:

classifier/data/labeled_data.csv

classifier/data/goal_index.faiss

Примечание: В текущей версии используется FAISS, а не USearch.

5. Настройка API-ключей
При запуске приложения ключи вводятся через веб-интерфейс (поля ввода).
Вы также можете предварительно сохранить их в переменные окружения (необязательно):

bash
export GIGACHAT_API_KEY="base64_client_id_client_secret"
export OPENROUTER_API_KEY="sk-or-v1-..."
6. Запуск приложения
bash
streamlit run app.py
После запуска в терминале появится ссылка: http://localhost:8501.
Откройте её в браузере.

7. Использование
В левой боковой панели создайте новый чат (кнопка «Новый чат»).

Введите API-ключи:

GigaChat API Key – строка в формате Base64 от client_id:client_secret

OpenRouter API Key – ваш ключ с OpenRouter

Введите сообщение в поле чата и нажмите Enter.

Дождитесь ответа GigaChat. Автоматически запустятся:

Оценка через OpenRouter (LLM-классификатор)

Анализ токсичности (локальная модель Tinkoff)

Результаты (метка «хороший/плохой», причина, уровень токсичности) появятся под ответом.

Все диалоги сохраняются в базе данных chat_history.db. Вы можете экспортировать историю любого чата в CSV (кнопка в боковой панели).
