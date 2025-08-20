import streamlit as st
import pandas as pd
import plotly.express as px

# ==============================
# FUNCIONES
# ==============================
@st.cache_data
def cargar_datos(path):
    df = pd.read_parquet(path)
    df['FechaAtencion'] = pd.to_datetime(df['FechaAtencion'])
    df['Periodo'] = df['FechaAtencion'].dt.to_period('M').astype(str)
    df['IPRESS'] = df['IPRESS'].astype('category')
    df['JURISDICCION'] = df['JURISDICCION'].astype('category')
    return df

@st.cache_data
def calcular_ingresos_egresos(df):
    df = df.copy()
    primera = df.groupby("NumeroDocumento")['FechaAtencion'].transform('min')
    ultima = df.groupby("NumeroDocumento")['FechaAtencion'].transform('max')

    df['nuevo'] = (df['FechaAtencion'] == primera).astype(int)
    df['egreso'] = (df['FechaAtencion'] == ultima).astype(int)

    ultimo_mes = df['FechaAtencion'].max().strftime('%Y-%m')
    df.loc[df['Periodo'] == ultimo_mes, 'egreso'] = 0

    primera_mes = df.groupby(['NumeroDocumento', df['FechaAtencion'].dt.to_period('M')])['FechaAtencion'].transform('min')
    df['prevalencia'] = (df['FechaAtencion'] == primera_mes).astype(int)

    return df

def generar_reporte(df, nivel, metrica):
    if nivel == "GLOBAL":
        reporte = df.groupby('Periodo').agg(
            nuevos=('nuevo','sum'),
            egresos=('egreso','sum'),
            prevalencia=('prevalencia','sum')
        ).reset_index()
    elif nivel == "IPRESS":
        reporte = df.groupby(['Periodo','IPRESS']).agg(
            nuevos=('nuevo','sum'),
            egresos=('egreso','sum'),
            prevalencia=('prevalencia','sum')
        ).reset_index()
    elif nivel == "JURISDICCION":
        reporte = df.groupby(['Periodo','JURISDICCION']).agg(
            nuevos=('nuevo','sum'),
            egresos=('egreso','sum'),
            prevalencia=('prevalencia','sum')
        ).reset_index()
    return reporte[['Periodo', nivel] + [metrica]] if nivel != "GLOBAL" else reporte[['Periodo', metrica]]

# ==============================
# DASHBOARD
# ==============================
st.set_page_config(page_title="Dashboard Hemodiálisis", layout="wide")
st.title("📊 Dashboard de Hemodiálisis - Evolución mensual")

# ------------------------------
# CARGAR DATOS
# ------------------------------
ruta = "datos_privadas_2015_202507_v03.parquet"
df = cargar_datos(ruta)
df = calcular_ingresos_egresos(df)

# ------------------------------
# FILTROS
# ------------------------------
st.sidebar.header("Filtros")

nivel = st.sidebar.selectbox("Nivel de reporte:", ["GLOBAL","IPRESS","JURISDICCION"])
metrica = st.sidebar.selectbox("Métrica a mostrar:", ["nuevos","egresos","prevalencia"])

# Selector de rango de fechas
min_fecha, max_fecha = df['FechaAtencion'].min(), df['FechaAtencion'].max()
rango_fechas = st.sidebar.date_input(
    "Rango de fechas:",
    value=(min_fecha, max_fecha),
    min_value=min_fecha,
    max_value=max_fecha
)

# Filtrar por fechas
df = df[(df['FechaAtencion'] >= pd.to_datetime(rango_fechas[0])) &
        (df['FechaAtencion'] <= pd.to_datetime(rango_fechas[1]))]

# Filtro adicional según nivel
if nivel == "IPRESS":
    opciones = ["(Todas)"] + sorted(df['IPRESS'].dropna().unique().tolist())
    seleccion = st.sidebar.selectbox("Seleccionar IPRESS:", opciones)
elif nivel == "JURISDICCION":
    opciones = ["(Todas)"] + sorted(df['JURISDICCION'].dropna().unique().tolist())
    seleccion = st.sidebar.selectbox("Seleccionar Jurisdicción:", opciones)
else:
    seleccion = None

# ------------------------------
# GENERAR REPORTE
# ------------------------------
reporte = generar_reporte(df, nivel, metrica)

if nivel != "GLOBAL" and seleccion != "(Todas)":
    col = nivel
    reporte = reporte[reporte[col] == seleccion]

# ------------------------------
# GRÁFICO INTERACTIVO
# ------------------------------
st.subheader(f"Evolución mensual de {metrica} - {nivel}{'' if not seleccion or seleccion=='(Todas)' else ' - ' + seleccion}")

if nivel == "GLOBAL" or (nivel != "GLOBAL" and seleccion != "(Todas)"):
    fig = px.line(reporte, x="Periodo", y=metrica, markers=True, title=f"{metrica.capitalize()} por mes")
else:
    fig = px.line(reporte, x="Periodo", y=metrica, color=nivel, markers=True, title=f"{metrica.capitalize()} por mes por {nivel}")

fig.update_layout(xaxis=dict(showgrid=False, tickangle=45), yaxis=dict(showgrid=True))
st.plotly_chart(fig, use_container_width=True)

# Mostrar tabla
st.dataframe(reporte.head(50))
