import streamlit as st
import requests
import json
from typing import Optional

# Импортируем наши модули классификатора
from classifier.retrieval import retrieve_similar_goals
from classifier.judge import classify_with_gigachat

st.title("💬 Чат-бот GigaChat с оценкой ответов")
st.write(
    "Простой чат-бот, использующий модель GigaChat. "
    "После ответа бота автоматически оценивается, является ли ответ 'плохим' (вредным) или 'хорошим', "
    "с пояснением причины."
)

# Поле для ввода ключа
api_key = st.text_input(
    "GigaChat API Key (Base64 от client_id:client_secret)",
    type="password",
    value="MDE5YmMwODYtMjM0MC03NWU2LThiZWQtYWM4M2RhNGQ4N2UxOjY0MDlhNjgxLWU3ZjktNGNmYi04MDkzLWQyMTkyODBkNjM4NA=="
)

if not api_key:
    st.info("Пожалуйста, введите API-ключ для продолжения.", icon="🔑")
else:
    # Функция получения access token
    def get_access_token(auth_key: str) -> Optional[str]:
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
            st.error(f"Ошибка получения токена: {e}")
            return None

    if "gigachat_token" not in st.session_state:
        with st.spinner("Получение токена доступа..."):
            token = get_access_token(api_key)
            if token:
                st.session_state.gigachat_token = token
                st.success("Токен получен!")
            else:
                st.stop()

    # Функция для вызова GigaChat API с потоковой передачей
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

    # Инициализация истории сообщений
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Отображение истории
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message["role"] == "assistant" and "label" in message:
                reason = message.get("reason", "не указана")
                if message["label"] == 1:
                    st.warning(f"⚠️ Оценка: **плохой ответ**\n\n📝 Причина: {reason}")
                elif message["label"] == 0:
                    st.success(f"✅ Оценка: **хороший ответ**\n\n📝 Причина: {reason}")
                else:
                    st.info(f"❓ Оценка не определена\n\n{reason}")

    # Поле ввода
    if prompt := st.chat_input("Введите сообщение..."):
        # Добавление сообщения пользователя
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Формирование сообщений для API
        api_messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

        # Генерация ответа с потоковой передачей
        with st.chat_message("assistant"):
            with st.spinner("GigaChat печатает..."):
                response_placeholder = st.empty()
                full_response = ""
                for chunk in gigachat_stream(api_messages, st.session_state.gigachat_token):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)

        # ---- Классификация ответа с получением причины ----
        with st.spinner("Оцениваем ответ..."):
            similar = retrieve_similar_goals(prompt, k=3)
            label, reason = classify_with_gigachat(prompt, full_response, similar, st.session_state.gigachat_token)

        # Сохраняем ответ с меткой и причиной
        st.session_state.messages.append({
            "role": "assistant",
            "content": full_response,
            "label": label,
            "reason": reason
        })

        # Показываем оценку сразу после ответа
        if label == 1:
            st.warning(f"⚠️ Оценка: **плохой ответ**\n\n📝 Причина: {reason}")
        elif label == 0:
            st.success(f"✅ Оценка: **хороший ответ**\n\n📝 Причина: {reason}")
        else:
            st.info(f"❓ Не удалось оценить ответ\n\n{reason}")