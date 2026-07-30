import os
import re
import pandas as pd
import streamlit as st

# Configuración de la página web
st.set_page_config(
    page_title="Sistema Consolidado SAP - TECSUR",
    page_icon="⚡",
    layout="wide"
)

st.title("⚡ Sistema Consolidado de Mapeo SAP y Programas TECSUR")
st.markdown("Plataforma relacional unificada que conecta el **Catálogo Maestro de Programas (CR)** con el **Detalle Operativo SAP (PEP, OM, Actividades PM/OP)**.")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def extraer_tres_digitos(val):
    """Extrae los últimos 3 dígitos numéricos (Ejemplo: 60132 -> '132', 132.0 -> '132')"""
    if pd.isna(val):
        return ""
    val_clean = str(val).split('.')[0].strip()
    match = re.search(r'(\d{3})$', val_clean)
    return match.group(1) if match else val_clean

@st.cache_data
def cargar_y_consolidar_datos():
    archivos = os.listdir(BASE_DIR)
    
    archivos_excel = [f for f in archivos if f.lower().endswith(('.xlsx', '.xls')) and not f.startswith('~$')]
    csv_programas = [f for f in archivos if 'programas' in f.lower() and f.lower().endswith('.csv')]
    csv_actividades = [f for f in archivos if 'actividad' in f.lower() and f.lower().endswith('.csv')]

    # 1. Cargar DataFrames base
    if archivos_excel:
        ruta = os.path.join(BASE_DIR, archivos_excel[0])
        xls = pd.ExcelFile(ruta)
        hojas = xls.sheet_names
        h_prog = next((h for h in hojas if 'prog' in h.lower()), hojas[0])
        h_act = next((h for h in hojas if 'act' in h.lower()), hojas[1] if len(hojas) > 1 else hojas[0])
        
        df_prog = pd.read_excel(xls, sheet_name=h_prog)
        df_act = pd.read_excel(xls, sheet_name=h_act)
    elif csv_programas and csv_actividades:
        df_prog = pd.read_csv(os.path.join(BASE_DIR, csv_programas[0]))
        df_act = pd.read_csv(os.path.join(BASE_DIR, csv_actividades[0]))
    else:
        raise FileNotFoundError("No se encontraron los archivos de origen de datos.")

    # 2. Limpieza de columnas
    df_prog.columns = [str(c).strip() for c in df_prog.columns]
    df_act.columns = [str(c).strip() for c in df_act.columns]

    col_desc_prog = 'Operación Lima / Cañete' if 'Operación Lima / Cañete' in df_prog.columns else df_prog.columns[-1]
    col_desc_act = 'ACTIVIDAD/PROGRAMA TECSUR' if 'ACTIVIDAD/PROGRAMA TECSUR' in df_act.columns else df_act.columns[1]

    # 3. Creación de Llaves compuestas de cruce
    # Llave 1: Texto de la Actividad
    df_prog['key_desc'] = df_prog[col_desc_prog].astype(str).str.strip().str.upper()
    df_act['key_desc'] = df_act[col_desc_act].astype(str).str.strip().str.upper()

    # Llave 2: Código numérico (CR de 5 dígitos -> 3 dígitos vs GP de 3 dígitos)
    df_prog['key_gp'] = df_prog['CR'].apply(extraer_tres_digitos)
    df_act['key_gp'] = df_act['GP'].apply(extraer_tres_digitos)

    # 4. CRUCE RELACIONAL POR DOBLE LLAVE EXACTA (key_gp + key_desc)
    df_merged = pd.merge(
        df_act,
        df_prog[['PROGRAMA', 'ACTIVIDAD', 'CR', 'key_desc', 'key_gp']],
        on=['key_gp', 'key_desc'],
        how='left'
    )

    # Limpieza de columnas auxiliares
    df_merged.drop(columns=['key_desc', 'key_gp'], inplace=True)
    
    # Ordenamiento lógico de columnas
    cols_orden = [
        'PROGRAMA', 'ACTIVIDAD', 'CR', 'GP', 'ACTIVIDAD/PROGRAMA TECSUR', 
        'Unidad', 'PEP', 'Clase de OM', 'Act PM', 'Descripcion Actividad PM', 
        'Act Operativa', 'Descripción Act Operativa'
    ]
    cols_finales = [c for c in cols_orden if c in df_merged.columns] + [c for c in df_merged.columns if c not in cols_orden]
    
    return df_prog, df_act, df_merged[cols_finales]

try:
    df_prog, df_act, df_consolidado = cargar_y_consolidar_datos()
    st.success("✅ Base de datos relacional integrada por Doble Llave (CR/GP + Descripción).")
except Exception as e:
    st.error(f"❌ Error durante el procesamiento relacional: {e}")
    st.stop()

# --- BARRA LATERAL CON FILTROS ---
st.sidebar.header("🎯 Filtros de Consulta Consolidada")

# Filtro 1: Programa Maestro
programas = ["Todos"] + sorted([str(p) for p in df_consolidado['PROGRAMA'].dropna().unique()])
prog_sel = st.sidebar.selectbox("Programa Maestro:", programas)

# Filtro 2: Código de Actividad (PL01, PC01, etc.)
codigos_act = ["Todos"]
if prog_sel != "Todos":
    sub_df = df_consolidado[df_consolidado['PROGRAMA'] == prog_sel]
    codigos_act += sorted([str(a) for a in sub_df['ACTIVIDAD'].dropna().unique()])
else:
    codigos_act += sorted([str(a) for a in df_consolidado['ACTIVIDAD'].dropna().unique()])

act_sel = st.sidebar.selectbox("Código Actividad (PL/PC):", codigos_act)

# Filtro 3: Clase de OM
clases_om = ["Todas"] + sorted([str(x).strip() for x in df_consolidado['Clase de OM'].dropna().unique() if str(x).strip() not in ['-', 'nan']])
om_sel = st.sidebar.selectbox("Clase de OM (ZM03/ZM06):", clases_om)

# Filtro 4: Búsqueda rápida por texto libre
busqueda = st.sidebar.text_input("🔍 Búsqueda rápida global:", "")

# --- APLICAR FILTROS EN CASCADA ---
df_filt = df_consolidado.copy()

if prog_sel != "Todos":
    df_filt = df_filt[df_filt['PROGRAMA'] == prog_sel]

if act_sel != "Todos":
    df_filt = df_filt[df_filt['ACTIVIDAD'] == act_sel]

if om_sel != "Todas":
    df_filt = df_filt[df_filt['Clase de OM'].astype(str) == om_sel]

if busqueda:
    mask = pd.Series(False, index=df_filt.index)
    for col in df_filt.columns:
        mask = mask | df_filt[col].astype(str).str.contains(busqueda, case=False, na=False)
    df_filt = df_filt[mask]

# --- VISTA PRINCIPAL & METRICAS DE IMPACTO ---
k1, k2, k3, k4 = st.columns(4)
k1.metric("Registros Filtrados", len(df_filt))
k2.metric("Centros Responsabilidad (CR)", df_filt['CR'].nunique() if 'CR' in df_filt.columns else 0)
k3.metric("Elementos PEP SAP", df_filt['PEP'].nunique() if 'PEP' in df_filt.columns else 0)
k4.metric("Actividades PM Únicas", df_filt['Act PM'].nunique() if 'Act PM' in df_filt.columns else 0)

st.divider()

# --- PESTAÑAS DE VISUALIZACIÓN ---
tab1, tab2 = st.tabs(["📊 Vista Consolidada Unificada", "🔍 Inspector por Programa"])

with tab1:
    st.subheader("📋 Tabla Maestra Consolidada")
    st.dataframe(df_filt, use_container_width=True, height=550)

with tab2:
    st.subheader("📁 Agrupación Jerárquica por Programa")
    for prog, group in df_filt.groupby('PROGRAMA'):
        with st.expander(f"📌 {prog} ({len(group)} registros SAP)"):
            st.dataframe(group[['ACTIVIDAD', 'CR', 'GP', 'PEP', 'Clase de OM', 'Act PM', 'Descripcion Actividad PM', 'Descripción Act Operativa']], use_container_width=True)
