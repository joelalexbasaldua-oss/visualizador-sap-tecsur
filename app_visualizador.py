import os
import pandas as pd
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title="Visualizador de Datos SAP - TECSUR",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Visualizador e Inspector de Mapeo SAP")
st.markdown("Herramienta interactiva para explorar la relación entre **Programas, Elementos PEP, Clases de OM y Actividades PM / OP**.")

# Obtener la carpeta donde está guardado este archivo script
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

@st.cache_data
def cargar_datos_robusto():
    archivos = os.listdir(BASE_DIR)
    
    # 1. Buscar archivos Excel en la carpeta
    archivos_excel = [f for f in archivos if f.lower().endswith(('.xlsx', '.xls')) and not f.startswith('~$')]
    
    # 2. Buscar archivos CSV en la carpeta
    csv_programas = [f for f in archivos if 'programas' in f.lower() and f.lower().endswith('.csv')]
    csv_actividades = [f for f in archivos if 'actividad' in f.lower() and f.lower().endswith('.csv')]
    
    df_prog = None
    df_act = None

    # Intento A: Cargar desde Excel
    if archivos_excel:
        ruta_excel = os.path.join(BASE_DIR, archivos_excel[0])
        xls = pd.ExcelFile(ruta_excel)
        hojas = xls.sheet_names
        
        hoja_prog = next((h for h in hojas if 'prog' in h.lower()), hojas[0])
        hoja_act = next((h for h in hojas if 'act' in h.lower()), hojas[1] if len(hojas) > 1 else hojas[0])
        
        df_prog = pd.read_excel(xls, sheet_name=hoja_prog)
        df_act = pd.read_excel(xls, sheet_name=hoja_act)
    
    # Intento B: Cargar desde CSVs
    elif csv_programas and csv_actividades:
        ruta_prog = os.path.join(BASE_DIR, csv_programas[0])
        ruta_act = os.path.join(BASE_DIR, csv_actividades[0])
        df_prog = pd.read_csv(ruta_prog)
        df_act = pd.read_csv(ruta_act)
    else:
        raise FileNotFoundError(f"No se encontraron archivos de datos. Archivos detectados en la carpeta: {archivos}")

    # Limpieza de columnas
    df_prog.columns = [str(c).strip() for c in df_prog.columns]
    df_act.columns = [str(c).strip() for c in df_act.columns]

    return df_prog, df_act, archivos

# Intentar la carga de datos
try:
    df_prog, df_act, archivos_detectados = cargar_datos_robusto()
    st.success("✅ Base de datos cargada correctamente.")
except Exception as e:
    st.error(f"❌ No se pudo cargar la base de datos.")
    st.warning(f"Detalle del aviso: {e}")
    st.info(f"📁 Ruta del proyecto: `{BASE_DIR}`")
    st.stop()

# --- FILTROS EN BARRA LATERAL ---
st.sidebar.header("🎯 Filtros de Consulta SAP")

col_prog = next((c for c in df_prog.columns if 'programa' in c.lower()), df_prog.columns[0])
programas = ["Todos"] + sorted(list(df_prog[col_prog].dropna().astype(str).unique()))
programa_sel = st.sidebar.selectbox("Seleccionar Programa:", programas)

# Detectar columna de Clase de OM en Actividades
col_om = next((c for c in df_act.columns if 'om' in c.lower() or 'clase' in c.lower()), None)

if col_om:
    clases_om = ["Todas"] + sorted([str(x).strip() for x in df_act[col_om].dropna().unique() if str(x).strip() not in ['-', 'nan']])
    om_sel = st.sidebar.selectbox("Clase de OM:", clases_om)
else:
    om_sel = "Todas"

busqueda = st.sidebar.text_input("🔍 Búsqueda rápida por texto:", "")

# --- FILTRADO DE DATOS ---
df_act_filt = df_act.copy()

if programa_sel != "Todos":
    col_act_prog = next((c for c in df_act_filt.columns if 'actividad' in c.lower() or 'programa' in c.lower()), df_act_filt.columns[0])
    df_act_filt = df_act_filt[
        df_act_filt[col_act_prog].astype(str).str.contains(programa_sel, case=False, na=False)
    ]

if om_sel != "Todas" and col_om:
    df_act_filt = df_act_filt[df_act_filt[col_om].astype(str) == om_sel]

if busqueda:
    condiciones = [
        df_act_filt[c].astype(str).str.contains(busqueda, case=False, na=False)
        for c in df_act_filt.columns
    ]
    mask = condiciones[0]
    for cond in condiciones[1:]:
        mask = mask | cond
    df_act_filt = df_act_filt[mask]

# --- MÉTRICAS PRINCIPALES ---
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Programas", len(df_prog))
col2.metric("Coincidencias", len(df_act_filt))

col_pep = next((c for c in df_act.columns if 'pep' in c.lower()), None)
col1_act_pm = next((c for c in df_act.columns if 'act' in c.lower() and 'pm' in c.lower()), None)

col3.metric("Elementos PEP Únicos", df_act[col_pep].nunique() if col_pep else "N/A")
col4.metric("Actividades PM Únicas", df_act[col1_act_pm].nunique() if col1_act_pm else "N/A")

st.divider()

# --- VISTA EN DOS COLUMNAS ---
c_left, c_right = st.columns([1, 2])

with c_left:
    st.subheader("📋 Catálogo de Programas")
    if programa_sel != "Todos":
        df_prog_show = df_prog[df_prog[col_prog] == programa_sel]
    else:
        df_prog_show = df_prog
    st.dataframe(df_prog_show, use_container_width=True, height=500)

with c_right:
    st.subheader("🛠️ Detalle de Coincidencias SAP")
    st.dataframe(df_act_filt, use_container_width=True, height=500)