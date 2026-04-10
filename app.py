import streamlit as st
import requests
import json
from typing import Optional
from datetime import datetime

from classifier.retrieval import retrieve_similar_goals
from classifier.judge import classify_with_openrouter
from classifier.local_toxicity import analyze_toxicity
from database import init_db, create_session, save_message, export_all_messages

# Загрузка  CSS
def load_css():
    with open("style.css", "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css()

# Инициализация БД
init_db()

st.title("Чат-бот GigaChat с оценкой ответов")
st.write(
    "Чат-бот на GigaChat. Ответы оцениваются моделью через OpenRouter: "
    "хороший (безопасный) или плохой (вредный/неэтичный) с пояснением причины. "
    "Дополнительно проводится анализ токсичности локальной моделью Tinkoff. "
    "Все диалоги сохраняются в БД для последующего обучения."
)

# Поле для ключа GigaChat
gigachat_api_key = st.text_input(
    "GigaChat API Key",
    type="password",
    value="MDE5YmMwODYtMjM0MC03NWU2LThiZWQtYWM4M2RhNGQ4N2UxOjY0MDlhNjgxLWU3ZjktNGNmYi04MDkzLWQyMTkyODBkNjM4NA=="
)

# Поле для ключа OpenRouter
openrouter_api_key = st.text_input(
    "OpenRouter API Key",
    type="password",
    value="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"
)

# Боковая панель для экспорта
with st.sidebar:
    st.header("Экспорт данных")
    df_all = export_all_messages()
    if df_all.empty:
        st.info("Нет данных для экспорта")
    else:
        csv_data = df_all.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="CSV",
            data=csv_data,
            file_name=f"chat_history_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    st.markdown("---")
    if "session_id" in st.session_state:
        st.caption(f"Сессия: {st.session_state.session_id[:8]}...")
    else:
        st.caption("Сессия будет создана после ввода ключей")

if not gigachat_api_key:
    st.info("Пожалуйста, введите API-ключ GigaChat для продолжения.", icon="🔑")
elif not openrouter_api_key:
    st.info("Пожалуйста, введите API-ключ OpenRouter для классификатора.", icon="🔑")
else:
    # Функция получения токена GigaChat
    def get_gigachat_token(auth_key: str) -> Optional[str]:
        url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        headers = {
            "Authorization": f"Basic {auth_key}",
            "RqUID": "6f0b1291-c7f3-43d6-8b9e-6f2b4d4e6f8a",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        data = {"scope": "GIGACHAT_API_PERS"}
        try:
            response = requests.post(url, headers=headers, data=data, verify=False)
            response.raise_for_status()
            return response.json().get("access_token")
        except Exception as e:
            st.error(f"Ошибка получения токена GigaChat: {e}")
            return None

    if "gigachat_token" not in st.session_state:
        with st.spinner("Получение токена GigaChat..."):
            token = get_gigachat_token(gigachat_api_key)
            if token:
                st.session_state.gigachat_token = token
                st.success("Токен GigaChat получен.")
            else:
                st.stop()

    if "session_id" not in st.session_state:
        st.session_state.session_id = create_session()

    # Функция вызова GigaChat
    def gigachat_stream(messages: list, access_token: str):
        url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "GigaChat",
            "messages": messages,
            "stream": True,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        try:
            response = requests.post(url, headers=headers, json=payload, stream=True, verify=False)
            response.raise_for_status()
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith("data: "):
                        data = line[6:]
                        if data.strip() == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            st.error(f"Ошибка при вызове GigaChat: {e}")
            yield "Извините, произошла ошибка."

    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Отображение истории
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant":
                # Показываем оценку от OpenRouter
                if "label" in message:
                    reason = message.get("reason", "не указана")
                    if message["label"] == 1:
                        st.warning(f"Оценка OpenRouter: **подозрительный ответ**\n\nПричина: {reason}")
                    elif message["label"] == 0:
                        st.success(f"Оценка OpenRouter: **валидный ответ**\n\nПричина: {reason}")
                    else:
                        st.info(f"Оценка OpenRouter не определена\n\n{reason}")
                # Показываем анализ токсичности
                if "toxicity" in message:
                    tox = message["toxicity"]
                    if tox["label"] != 0:
                        st.error(f"**Анализ токсичности:** {tox['explanation']}")
                    else:
                        st.success(f"**Анализ токсичности:** {tox['explanation']}")

    # Поле ввода
    if prompt := st.chat_input("Введите сообщение..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

        with st.chat_message("assistant"):
            with st.spinner("GigaChat печатает..."):
                response_placeholder = st.empty()
                full_response = ""
                for chunk in gigachat_stream(api_messages, st.session_state.gigachat_token):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)

        # Классификация через OpenRouter
        with st.spinner("Оценка ответа через OpenRouter..."):
            similar = retrieve_similar_goals(prompt, k=3)
            label, reason = classify_with_openrouter(prompt, full_response, similar, openrouter_api_key)

        # Локальный анализ токсичности
        with st.spinner("Анализ ответа локальной моделью..."):
            toxicity = analyze_toxicity(full_response)

        # Сохраняем в сессию для отображения
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "label": label,
            "reason": reason,
            "toxicity": toxicity
        })

        # Сохраняем в БД
        save_message(
            session_id=st.session_state.session_id,
            user_prompt=prompt,
            assistant_response=full_response,
            label=label,
            reason=reason,
            toxicity_details=toxicity
        )

        # Показываем оценки
        if label == 1:
            st.warning(f"Оценка OpenRouter: **подозрительный ответ**\n\nПричина: {reason}")
        elif label == 0:
            st.success(f"Оценка OpenRouter: **валидный ответ**\n\nПричина: {reason}")
        else:
            st.info(f"Оценка OpenRouter не определена\n\n{reason}")

        if toxicity["label"] != 0:
            st.error(f"**Анализ токсичности:** {toxicity['explanation']}")
        else:
            st.success(f"**Анализ токсичности:** {toxicity['explanation']}")