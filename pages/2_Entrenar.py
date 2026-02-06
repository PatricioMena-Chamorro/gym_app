import streamlit as st
import time
import os
from datetime import datetime
from pathlib import Path
from db_sqlite import list_routines, list_exercises, start_session, finish_session, log_set

st.title("Entrenar")

def get_db_path() -> str:
    # Debe coincidir con db_sqlite.py si usas env var
    return os.getenv("GYM_DB_PATH", "gym.db")

def make_backup_bytes() -> tuple[bytes, str]:
    db_path = get_db_path()
    data = Path(db_path).read_bytes()
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    filename = f"gym_backup_{ts}.db"
    return data, filename

routines = list_routines()
if not routines:
    st.info("Primero crea una rutina en la pestaña Rutinas.")
    st.stop()

# Prefill desde Home (si venías desde app.py)
default_id = st.session_state.get("selected_routine_id")

routine_labels = [f"{r['name']} (id={r['id']})" for r in routines]
routine_ids = [r["id"] for r in routines]

default_index = 0
if default_id in routine_ids:
    default_index = routine_ids.index(default_id)

sel = st.selectbox("Rutina", routine_labels, index=default_index)
routine_id = routine_ids[routine_labels.index(sel)]

# opcional: limpiar para que no quede “pegado”
st.session_state.pop("selected_routine_id", None)


exs = list_exercises(routine_id)
if not exs:
    st.info("Esta rutina no tiene ejercicios aún.")
    st.stop()

# --- estado sesión ---
if "session_id" not in st.session_state:
    st.session_state.session_id = None

if st.session_state.session_id is None:
    if st.button("▶️ Iniciar sesión", type="primary"):
        st.session_state.session_id = start_session(routine_id)
        st.session_state.set_done = {}   # (exercise_id, set_index) -> bool
        st.session_state.set_extra = {}  # exercise_id -> extra sets
        st.rerun()
else:
    st.success(f"Sesión activa: {st.session_state.session_id}")
    if st.button("⏹️ Finalizar sesión"):
        finish_session(st.session_state.session_id)
        st.session_state.session_id = None

        # ✅ backup automático (genera bytes + nombre y lo deja listo para descargar)
        try:
            b, fname = make_backup_bytes()
            st.session_state.last_backup_bytes = b
            st.session_state.last_backup_name = fname
            st.session_state.last_backup_ready = True
            st.session_state.last_backup_error = None
        except Exception as e:
            st.session_state.last_backup_ready = False
            st.session_state.last_backup_error = str(e)

        st.rerun()

# --- Backup listo para descargar (aparece después de finalizar sesión) ---
if st.session_state.get("last_backup_ready"):
    st.success("✅ Sesión finalizada. Backup listo para descargar.")
    st.download_button(
        label=f"⬇️ Descargar backup ({st.session_state.get('last_backup_name','gym_backup.db')})",
        data=st.session_state["last_backup_bytes"],
        file_name=st.session_state.get("last_backup_name", "gym_backup.db"),
        mime="application/octet-stream",
        type="primary",
        use_container_width=True,
    )
elif st.session_state.get("last_backup_error"):
    st.warning(f"⚠️ No pude generar el backup automático: {st.session_state['last_backup_error']}")



st.divider()

rest_default = st.number_input("Descanso global (segundos)", min_value=0, max_value=600, value=60, step=5)

BEEP_PATH = Path("assets/beep.wav")

def run_timer(seconds: int):
    ph = st.empty()
    for t in range(seconds, -1, -1):
        ph.info(f"⏱️ Descanso: {t}s")
        time.sleep(1)
    ph.success("✅ Listo!")

    # 🔊 Beep al terminar
    if BEEP_PATH.exists():
        st.audio(str(BEEP_PATH), autoplay=True)

if st.session_state.session_id is None:
    st.stop()

for ex in exs:
    ex_id = ex["id"]
    base_sets = int(ex["default_sets"])
    extra = st.session_state.set_extra.get(ex_id, 0)
    total_sets = base_sets + extra

    with st.container(border=True):
        st.subheader(ex["name"])

        if ("image_path" in ex.keys()) and ex["image_path"]:
            st.image(ex["image_path"], width=260)

        # inputs globales por ejercicio
        cA, cB = st.columns(2)
        with cA:
            weight = st.number_input("Peso (kg)", min_value=0.0, value=0.0, step=1.0, key=f"w_{ex_id}")
        with cB:
            reps = st.number_input("Reps", min_value=1, value=10, step=1, key=f"r_{ex_id}")

        cols = st.columns([1]*total_sets + [2])
        for i in range(total_sets):
            key = (ex_id, i)
            done = st.session_state.set_done.get(key, False)
            label = f"S{i+1}"
            with cols[i]:
                new_done = st.checkbox(label, value=done, key=f"cb_{ex_id}_{i}")

            # Si lo marca recién ahora: log + timer
            if (not done) and new_done:
                st.session_state.set_done[key] = True
                log_set(st.session_state.session_id, ex_id, i+1, int(reps), float(weight))
                run_timer(int(rest_default))

        with cols[-1]:
            if st.button("➕ Agregar 1 serie", key=f"add_{ex_id}"):
                st.session_state.set_extra[ex_id] = extra + 1
                st.rerun()
