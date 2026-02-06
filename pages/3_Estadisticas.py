import streamlit as st
import pandas as pd
import plotly.express as px
import os
from pathlib import Path
from db_sqlite import stats_sets

st.title("Estadísticas")

def get_db_path() -> str:
    return os.getenv("GYM_DB_PATH", "gym.db")

rows = stats_sets()
if not rows:
    st.info("Aún no hay sets registrados. Ve a Entrenar y marca series.")
    st.stop()

st.subheader("Backup y restauración")

db_path = get_db_path()

# --- Descargar DB actual ---
if Path(db_path).exists():
    st.download_button(
        label="⬇️ Descargar backup completo (gym.db)",
        data=Path(db_path).read_bytes(),
        file_name="gym_backup.db",
        mime="application/octet-stream",
        use_container_width=True
    )
else:
    st.warning(f"No encuentro la base de datos en: {db_path}")

st.divider()

# --- Restaurar desde backup ---
st.markdown("### Restaurar desde un backup (.db)")
st.caption("Sube tu archivo .db. Esto reemplaza la base actual y reinicia la app.")

uploaded = st.file_uploader("Subir backup .db", type=["db"])

confirm = st.checkbox("Entiendo que esto reemplaza mi base actual", value=False)

if uploaded and confirm:
    if st.button("♻️ Restaurar backup", type="primary"):
        try:
            Path(db_path).write_bytes(uploaded.read())
            st.success("✅ Backup restaurado. Reiniciando app…")
            st.rerun()
        except Exception as e:
            st.error(f"❌ Error restaurando backup: {e}")

st.divider()



df = pd.DataFrame([dict(r) for r in rows])
df["created_at"] = (
    pd.to_datetime(df["created_at"], utc=True)
      .dt.tz_convert("America/Santiago")
      .dt.tz_localize(None)
)

df["session_date"] = df["created_at"].dt.date  # <-- clave: date sin hora

# -------------------------
# Filtro temporal
# -------------------------
st.subheader("Filtros")
range_opt = st.selectbox(
    "Rango",
    ["Últimas 4 semanas", "Últimas 8 semanas", "Últimos 3 meses", "Todo"],
    index=0
)

now = pd.Timestamp.now(tz=None)
if range_opt == "Últimas 4 semanas":
    cutoff = now - pd.Timedelta(days=28)
    df = df[df["created_at"] >= cutoff]
elif range_opt == "Últimas 8 semanas":
    cutoff = now - pd.Timedelta(days=56)
    df = df[df["created_at"] >= cutoff]
elif range_opt == "Últimos 3 meses":
    cutoff = now - pd.Timedelta(days=90)
    df = df[df["created_at"] >= cutoff]

if df.empty:
    st.warning("No hay registros en el rango seleccionado.")
    st.stop()

st.caption(f"Registros (sets) en rango: {len(df)}")
st.dataframe(df.sort_values("created_at", ascending=False), use_container_width=True)

# -------------------------
# Métricas derivadas
# -------------------------
# fecha "de sesión" (día)
df["session_date"] = df["created_at"].dt.date

# e1RM (Epley). Si weight=0, queda 0.
df["e1rm"] = df["weight"] * (1 + (df["reps"] / 30.0))

# ID de sesión simple: (día + rutina)
df["session_id"] = df["session_date"].astype(str) + " | " + df["routine"].astype(str)

# -------------------------
# 1) Volumen por ejercicio
# -------------------------
st.subheader("Volumen por ejercicio (rango seleccionado)")
vol = (
    df.groupby(["exercise"], as_index=False)["volume"]
      .sum()
      .sort_values("volume", ascending=False)
)
fig = px.bar(vol, x="exercise", y="volume")
st.plotly_chart(fig, use_container_width=True)

# -------------------------
# 2) Progreso por SET (tal como lo tienes)
# -------------------------
st.subheader("Progreso por set (peso)")
ex = st.selectbox("Ejercicio (por set)", sorted(df["exercise"].unique()), key="ex_set")
df_set = df[df["exercise"] == ex].sort_values("created_at")

fig2 = px.line(df_set, x="created_at", y="weight", markers=True, hover_data=["routine", "reps", "set_index", "volume"])
st.plotly_chart(fig2, use_container_width=True)

# -------------------------
# 3) Progreso por SESIÓN (Top set)
# -------------------------
st.subheader("Progreso por sesión (top set de peso)")
ex2 = st.selectbox("Ejercicio (por sesión)", sorted(df["exercise"].unique()), key="ex_sess")

df_ex = df[df["exercise"] == ex2].copy()

# agregación por sesión: top weight, volumen total, top e1rm
sess = (
    df_ex.groupby(["session_date", "routine"], as_index=False)
         .agg(
             top_weight=("weight", "max"),
             session_volume=("volume", "sum"),
             top_e1rm=("e1rm", "max"),
             n_sets=("weight", "count"),
         )
         .sort_values("session_date")
)

fig3 = px.line(sess, x="session_date", y="top_weight", markers=True, hover_data=["routine", "n_sets", "session_volume", "top_e1rm"])
st.plotly_chart(fig3, use_container_width=True)

# -------------------------
# 4) e1RM por sesión (mejor set)
# -------------------------
st.subheader("Progreso por sesión (1RM estimada - Epley)")
st.caption("e1RM = weight * (1 + reps/30). Útil si cambias reps entre sesiones.")

fig4 = px.line(sess, x="session_date", y="top_e1rm", markers=True, hover_data=["routine", "top_weight", "n_sets"])
st.plotly_chart(fig4, use_container_width=True)

# -------------------------
# 5) Constancia: sesiones por semana
# -------------------------
st.subheader("Constancia: sesiones por semana")

# semana ISO basada en created_at
df["week"] = df["created_at"].dt.isocalendar().week.astype(int)
df["year"] = df["created_at"].dt.isocalendar().year.astype(int)

# sesiones únicas: (año, semana, session_id)
weekly = (
    df.drop_duplicates(subset=["year", "week", "session_id"])
      .groupby(["year", "week"], as_index=False)
      .size()
      .rename(columns={"size": "sessions"})
)

# etiqueta "YYYY-WW"
weekly["year_week"] = weekly["year"].astype(str) + "-W" + weekly["week"].astype(str).str.zfill(2)

fig5 = px.bar(weekly, x="year_week", y="sessions")
st.plotly_chart(fig5, use_container_width=True)

st.caption("Tip: si tu meta es 4 sesiones/semana, este gráfico te deja ver rápidamente si estás cumpliendo.")
