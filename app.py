import streamlit as st
import requests
import json
from typing import Optional
from datetime import datetime
import ast

from classifier.retrieval import retrieve_similar_goals
from classifier.judge import classify_with_openrouter
from classifier.local_toxicity import analyze_toxicity
from database import (
    init_db, create_session, delete_session, rename_session,
    get_all_sessions, get_messages, save_message, export_session_messages
)

# ---------- CSS ----------
def load_css():
    with open("style.css", "r", encoding="utf-8") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

load_css()
init_db()

# ---------- Инициализация состояния ----------
if "current_session_id" not in st.session_state:
    sessions = get_all_sessions()
    if sessions:
        st.session_state.current_session_id = sessions[0][0]
    else:
        st.session_state.current_session_id = create_session()

if "sessions_list" not in st.session_state:
    st.session_state.sessions_list = get_all_sessions()

if "messages_cache" not in st.session_state:
    st.session_state.messages_cache = {}

def refresh_sessions():
    st.session_state.sessions_list = get_all_sessions()

def switch_chat(session_id):
    st.session_state.current_session_id = session_id
    st.rerun()

def create_new_chat():
    new_id = create_session()
    refresh_sessions()
    st.session_state.current_session_id = new_id
    st.rerun()

def delete_current_chat():
    delete_session(st.session_state.current_session_id)
    refresh_sessions()
    sessions = st.session_state.sessions_list
    if sessions:
        st.session_state.current_session_id = sessions[0][0]
    else:
        st.session_state.current_session_id = create_session()
    st.rerun()

def rename_current_chat(new_name):
    rename_session(st.session_state.current_session_id, new_name)
    refresh_sessions()
    st.rerun()

# ---------- Боковая панель ----------
with st.sidebar:
    st.header("☰ История чатов")
    if st.button("✚ Новый чат", use_container_width=True):
        create_new_chat()
    st.markdown("---")
    for sid, name, start_time in st.session_state.sessions_list:
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(name, key=f"chat_{sid}", use_container_width=True):
                switch_chat(sid)
        with col2:
            if st.button("🗑", key=f"del_{sid}", help="Удалить чат"):
                if sid == st.session_state.current_session_id:
                    delete_current_chat()
                else:
                    delete_session(sid)
                    refresh_sessions()
                    if st.session_state.current_session_id == sid:
                        delete_current_chat()
                st.rerun()
    st.markdown("---")
    # Экспорт текущего чата
    df_exp = export_session_messages(st.session_state.current_session_id)
    if not df_exp.empty:
        csv_data = df_exp.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="⭳ CSV",
            data=csv_data,
            file_name=f"chat_{st.session_state.current_session_id[:8]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("Нет данных для экспорта")

# ---------- Основная область ----------
st.title("AI-агентная система red teaming и контроль ответов LLM GigaChat")
st.write("Выберите чат слева или создайте новый. Все диалоги сохраняются в БД.")

# Загрузка сообщений текущего чата
if st.session_state.current_session_id not in st.session_state.messages_cache:
    msgs = get_messages(st.session_state.current_session_id)
    formatted = []
    for user_prompt, assistant_response, label, reason, toxicity_details, ts in msgs:
        formatted.append({"role": "user", "content": user_prompt})
        formatted.append({
            "role": "assistant",
            "content": assistant_response,
            "label": label,
            "reason": reason,
            "toxicity": ast.literal_eval(toxicity_details) if toxicity_details else None
        })
    st.session_state.messages_cache[st.session_state.current_session_id] = formatted

# Отображение истории текущего чата
for message in st.session_state.messages_cache[st.session_state.current_session_id]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message["role"] == "assistant":
            if "label" in message:
                reason = message.get("reason", "не указана")
                if message["label"] == 1:
                    st.warning(f"⚠ Оценка OpenRouter: **подозрительный ответ**\n\nПричина: {reason}")
                elif message["label"] == 0:
                    st.success(f"✓ Оценка OpenRouter: **валидный ответ**\n\nПричина: {reason}")
                else:
                    st.info(f"⍰ Оценка OpenRouter не определена\n\n{reason}")
            if "toxicity" in message and message["toxicity"]:
                tox = message["toxicity"]
                if tox["label"] != 0:
                    st.error(f"**Анализ токсичности.** {tox['explanation']}")
                else:
                    st.success(f"**Анализ токсичности.** {tox['explanation']}")

# ---------- Поля ввода API-ключей (как в оригинале) ----------
gigachat_api_key = st.text_input(
    "GigaChat API Key",
    type="password",
    value="MDE5YmMwODYtMjM0MC03NWU2LThiZWQtYWM4M2RhNGQ4N2UxOjY0MDlhNjgxLWU3ZjktNGNmYi04MDkzLWQyMTkyODBkNjM4NA==",
    key="gigachat_key_input"
)
openrouter_api_key = st.text_input(
    "OpenRouter API Key",
    type="password",
    value="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",
    key="openrouter_key_input"
)

if not gigachat_api_key:
    st.info("Пожалуйста, введите API-ключ GigaChat для продолжения.", icon="🔑")
elif not openrouter_api_key:
    st.info("Пожалуйста, введите API-ключ OpenRouter для классификатора.", icon="🔑")
else:
    # ---------- Токен GigaChat ----------
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

    # ---------- Функция вызова GigaChat ----------
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

    # ---------- Поле ввода нового сообщения ----------
    if prompt := st.chat_input("Введите сообщение..."):
        # Добавляем сообщение пользователя в кэш и отображаем
        st.session_state.messages_cache[st.session_state.current_session_id].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # История для GigaChat (все сообщения текущего чата)
        api_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in st.session_state.messages_cache[st.session_state.current_session_id]
        ]

        # Ответ ассистента
        with st.chat_message("assistant"):
            with st.spinner("GigaChat печатает..."):
                response_placeholder = st.empty()
                full_response = ""
                for chunk in gigachat_stream(api_messages, st.session_state.gigachat_token):
                    full_response += chunk
                    response_placeholder.markdown(full_response + "▌")
                response_placeholder.markdown(full_response)

        # Классификация и токсичность
        with st.spinner("Оценка ответа через OpenRouter..."):
            similar = retrieve_similar_goals(prompt, k=3)
            label, reason = classify_with_openrouter(prompt, full_response, similar, openrouter_api_key)

        with st.spinner("Анализ ответа локальной моделью..."):
            toxicity = analyze_toxicity(full_response)

        # Сохраняем в кэш
        st.session_state.messages_cache[st.session_state.current_session_id].append({
            "role": "assistant",
            "content": full_response,
            "label": label,
            "reason": reason,
            "toxicity": toxicity
        })

        # Сохраняем в БД
        save_message(
            session_id=st.session_state.current_session_id,
            user_prompt=prompt,
            assistant_response=full_response,
            label=label,
            reason=reason,
            toxicity_details=toxicity
        )

        # Отображаем оценки
        if label == 1:
            st.warning(f"⚠ Оценка OpenRouter: **подозрительный ответ**\n\nПричина: {reason}")
        elif label == 0:
            st.success(f"✓ Оценка OpenRouter: **валидный ответ**\n\nПричина: {reason}")
        else:
            st.info(f"⍰ Оценка OpenRouter не определена\n\n{reason}")

        if toxicity["label"] != 0:
            st.error(f"**Анализ токсичности.** {toxicity['explanation']}")
        else:
            st.success(f"**Анализ токсичности.** {toxicity['explanation']}")

        st.rerun()