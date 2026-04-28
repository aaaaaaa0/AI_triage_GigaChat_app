import streamlit as st
import requests
import json
import threading
from datetime import datetime
import pandas as pd
import io

QWEN_VM_URL = "http://82.202.156.156:11434"

# ---------- Получение списка моделей с ВМ ----------
@st.cache_data(ttl=60)
def get_models():
    try:
        r = requests.get(f"{QWEN_VM_URL}/api/tags", timeout=3)
        if r.status_code == 200:
            models = [m['name'] for m in r.json().get('models', [])]
            if models:
                return models
    except Exception as e:
        st.error(f"Не удалось подключиться к ВМ: {e}")
    return ["huihui_ai/qwen2.5-abliterate:7b", "huihui_ai/qwen2.5-abliterate:14b"]


def stream_qwen(prompt, model, temperature, max_tokens, system_prompt, stop_event):
    payload = {
        "model": model,
        "prompt": prompt,
        "system": system_prompt,  
        "stream": True,
        "num_predict": max_tokens,
        "temperature": temperature
    }
    try:
        with requests.post(f"{QWEN_VM_URL}/api/generate", json=payload, stream=True, timeout=180) as resp:
            resp.raise_for_status()
            for line in resp.iter_lines():
                if stop_event.is_set():
                    yield "\n[Остановлено пользователем]"
                    break
                if not line:
                    continue
                data = json.loads(line.decode())
                if 'response' in data:
                    yield data['response']
                if data.get('done'):
                    break
    except requests.exceptions.ConnectionError:
        yield "\n[Ошибка: не удалось подключиться к ВМ. Проверьте доступность сервера.]"
    except Exception as e:
        yield f"\n[Ошибка: {e}]"

def is_model_available(model):
    return model in get_models()

# ---------- Инициализация состояния ----------
st.set_page_config(page_title="Секрет мефедрона", page_icon="🤖", layout="wide")
st.title("Познай все тайны мироздания")

# Инициализация переменных сессии
if "messages" not in st.session_state:
    st.session_state.messages = []
if "generating" not in st.session_state:
    st.session_state.generating = False
if "stop_gen" not in st.session_state:
    st.session_state.stop_gen = threading.Event()

# Применённые настройки
if "applied_model" not in st.session_state:
    st.session_state.applied_model = get_models()[0]
if "applied_temperature" not in st.session_state:
    st.session_state.applied_temperature = 0.7
if "applied_max_tokens" not in st.session_state:
    st.session_state.applied_max_tokens = 500
if "applied_system_prompt" not in st.session_state:
    st.session_state.applied_system_prompt = "Ты полезный ассистент."

# Временные настройки (виджеты)
if "temp_model" not in st.session_state:
    st.session_state.temp_model = st.session_state.applied_model
if "temp_temperature" not in st.session_state:
    st.session_state.temp_temperature = st.session_state.applied_temperature
if "temp_max_tokens" not in st.session_state:
    st.session_state.temp_max_tokens = st.session_state.applied_max_tokens
if "temp_system_prompt" not in st.session_state:
    st.session_state.temp_system_prompt = st.session_state.applied_system_prompt

# ---------- Боковая панель ----------
with st.sidebar:
    st.header("⚠️ Предупреждение")
    st.info("После перезагрузки страницы вся история чатов будет потеряна. Обязательно скачайте данные перед обновлением!")

    st.header("⚙️ Настройки")
    if not st.session_state.generating:
        model_list = get_models()
        st.session_state.temp_model = st.selectbox("Модель", model_list,
                                                   index=model_list.index(st.session_state.temp_model) if st.session_state.temp_model in model_list else 0,
                                                   key="temp_model_widget")
        st.session_state.temp_temperature = st.slider("Температура", 0.0, 1.5, st.session_state.temp_temperature, 0.05,
                                                      key="temp_temperature_widget")
        st.session_state.temp_max_tokens = st.slider("Макс. токенов", 50, 2000, st.session_state.temp_max_tokens, 50,
                                                     key="temp_max_tokens_widget", help="Модель может выдать меньше или больше, это ориентир")
        st.session_state.temp_system_prompt = st.text_area("Системный промпт", st.session_state.temp_system_prompt,
                                                           height=120, key="temp_system_prompt_widget")

        if st.button("✅ Применить", use_container_width=True):
            st.session_state.applied_model = st.session_state.temp_model
            st.session_state.applied_temperature = st.session_state.temp_temperature
            st.session_state.applied_max_tokens = st.session_state.temp_max_tokens
            st.session_state.applied_system_prompt = st.session_state.temp_system_prompt
            st.toast("Настройки применены", icon="✅")
            st.rerun()
    else:
        st.info("Настройки недоступны во время генерации ответа")
        st.write(f"**Модель:** {st.session_state.applied_model}")
        st.write(f"**Температура:** {st.session_state.applied_temperature}")
        st.write(f"**Макс. токенов:** {st.session_state.applied_max_tokens}")
        st.write(f"**Системный промпт:** {st.session_state.applied_system_prompt[:100]}...")

    st.markdown("---")
    if st.button("🧹 Очистить историю", use_container_width=True, disabled=st.session_state.generating):
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")
    st.header("💾 Экспорт")
    if st.session_state.messages:
        df = pd.DataFrame(st.session_state.messages)
        csv_data = df.to_csv(index=False).encode('utf-8')
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Chat')
        excel_data = excel_buffer.getvalue()

        col1, col2 = st.columns(2)
        with col1:
            st.download_button("JSON",
                               data=json.dumps({
                                   "model": st.session_state.applied_model,
                                   "temperature": st.session_state.applied_temperature,
                                   "max_tokens": st.session_state.applied_max_tokens,
                                   "system_prompt": st.session_state.applied_system_prompt,
                                   "messages": st.session_state.messages,
                                   "date": datetime.now().isoformat()
                               }, ensure_ascii=False, indent=2),
                               file_name=f"qwen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                               mime="application/json")
        with col2:
            st.download_button("TXT",
                               data="\n\n".join([f"{m['role'].upper()}: {m['content']}" for m in st.session_state.messages]),
                               file_name=f"qwen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                               mime="text/plain")
        col3, col4 = st.columns(2)
        with col3:
            st.download_button("CSV",
                               data=csv_data,
                               file_name=f"qwen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                               mime="text/csv")
        with col4:
            st.download_button("XLSX",
                               data=excel_data,
                               file_name=f"qwen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    else:
        st.info("Нет сообщений для экспорта")

    if st.session_state.generating:
        st.markdown("---")
        if st.button("⏹️ ОСТАНОВИТЬ ГЕНЕРАЦИЮ", use_container_width=True, type="primary"):
            st.session_state.stop_gen.set()

# ---------- Отображение истории чата ----------
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("Введите сообщение...", disabled=st.session_state.generating)

if prompt and not st.session_state.generating:
    # Проверка доступности модели
    if not is_model_available(st.session_state.applied_model):
        st.error(f"Модель {st.session_state.applied_model} не найдена на ВМ. Пожалуйста, выберите другую модель или загрузите её через ollama pull.")
    else:
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        st.session_state.generating = True
        st.session_state.stop_gen.clear()

        with st.chat_message("assistant"):
            placeholder = st.empty()
            full_text = ""
            error_occurred = False
            for chunk in stream_qwen(prompt,
                                     st.session_state.applied_model,
                                     st.session_state.applied_temperature,
                                     st.session_state.applied_max_tokens,
                                     st.session_state.applied_system_prompt,
                                     st.session_state.stop_gen):
                if chunk.startswith("[Ошибка:"):
                    error_occurred = True
                    st.error(chunk)
                    break
                full_text += chunk
                placeholder.markdown(full_text + "▌")
                if st.session_state.stop_gen.is_set():
                    break
            if not error_occurred:
                if st.session_state.stop_gen.is_set():
                    placeholder.markdown(full_text + "\n\n*Генерация прервана*")
                else:
                    placeholder.markdown(full_text)
                st.session_state.messages.append({"role": "assistant", "content": full_text})
            else:
                pass

        st.session_state.generating = False
        st.session_state.stop_gen.clear()
        st.rerun()
