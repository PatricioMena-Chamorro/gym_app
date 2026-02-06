import streamlit as st
from db_sqlite import init_db, list_routines

st.set_page_config(page_title="Gym App", page_icon="💪", layout="wide")
init_db()

st.title("💪 Gym App")

routines = list_routines()
if routines:
    routine_map = {f"{r['name']} (id={r['id']})": r["id"] for r in routines}
    sel = st.selectbox("Atajo: elige una rutina para entrenar", list(routine_map.keys()))
    routine_id = routine_map[sel]

    if st.button("▶️ Ir a Entrenar", type="primary"):
        st.session_state.selected_routine_id = routine_id
        st.switch_page("pages/2_Entrenar.py")
else:
    st.info("Aún no tienes rutinas. Crea una en la pestaña Rutinas.")
