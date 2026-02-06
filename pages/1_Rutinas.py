import streamlit as st
from db_sqlite import (
    list_routines, create_routine, rename_routine, delete_routine,
    list_exercises, add_exercise, update_exercise, delete_exercise,
    save_exercise_image
)

st.title("Rutinas")

# --- Crear rutina ---
with st.expander("➕ Crear rutina", expanded=True):
    new_name = st.text_input("Nombre de la rutina", placeholder="Ej: Empuje / Jalón / Piernas")
    if st.button("Crear rutina", type="primary", disabled=not new_name.strip()):
        create_routine(new_name.strip())
        st.rerun()

routines = list_routines()
if not routines:
    st.info("Aún no tienes rutinas. Crea una arriba.")
    st.stop()

# --- Seleccionar rutina ---
routine_map = {f"{r['name']} (id={r['id']})": r["id"] for r in routines}
sel = st.selectbox("Selecciona rutina", list(routine_map.keys()))
routine_id = routine_map[sel]

colA, colB = st.columns(2)
with colA:
    new_rname = st.text_input("Renombrar rutina", value=[r["name"] for r in routines if r["id"] == routine_id][0])
    if st.button("Guardar nombre"):
        rename_routine(routine_id, new_rname.strip())
        st.rerun()

with colB:
    if st.button("🗑️ Eliminar rutina (y ejercicios)", type="secondary"):
        delete_routine(routine_id)
        st.rerun()

st.divider()
st.subheader("Ejercicios")

exs = list_exercises(routine_id)

with st.expander("➕ Agregar ejercicio", expanded=True):
    name = st.text_input("Nombre", placeholder="Ej: Bench press", key="ex_name")
    order_index = st.number_input("Orden", min_value=0, value=(len(exs) if exs else 0), step=1)
    default_sets = st.number_input("Sets por defecto", min_value=1, max_value=10, value=3, step=1)
    rest = st.number_input("Descanso (segundos)", min_value=0, max_value=600, value=60, step=5)

    img = st.file_uploader("Imagen (opcional)", type=["png", "jpg", "jpeg", "webp"], key="ex_img")

    if st.button("Agregar", disabled=not name.strip()):
        image_path = save_exercise_image(img) if img is not None else None
        add_exercise(routine_id, name.strip(), int(order_index), int(default_sets), int(rest), image_path)
        st.rerun()

if not exs:
    st.info("Agrega ejercicios para esta rutina.")
    st.stop()

for ex in exs:
    with st.container(border=True):
        c1, c2, c3, c4, c5 = st.columns([3,1,1,1,1])
        with c1:
            n = st.text_input("Ejercicio", value=ex["name"], key=f"n_{ex['id']}")
        with c2:
            oi = st.number_input("Orden", min_value=0, value=ex["order_index"], step=1, key=f"oi_{ex['id']}")
        with c3:
            ds = st.number_input("Sets", min_value=1, max_value=10, value=ex["default_sets"], step=1, key=f"ds_{ex['id']}")
        with c4:
            rs = st.number_input("Rest(s)", min_value=0, max_value=600, value=ex["default_rest_seconds"], step=5, key=f"rs_{ex['id']}")
        with c5:
            if st.button("🗑️", key=f"del_{ex['id']}"):
                delete_exercise(ex["id"])
                st.rerun()
        # Mostrar imagen actual si existe
        if ("image_path" in ex.keys()) and ex["image_path"]:
            st.image(ex["image_path"], caption="Imagen actual", width=220)
        
        new_img = st.file_uploader(
            "Reemplazar imagen (opcional)",
            type=["png", "jpg", "jpeg", "webp"],
            key=f"img_{ex['id']}"
        )

        if st.button("Guardar cambios", key=f"save_{ex['id']}"):
            new_path = save_exercise_image(new_img) if new_img is not None else None
            update_exercise(ex["id"], n.strip(), int(oi), int(ds), int(rs), new_path)
            st.rerun()

