import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import date
import requests

# --- Base de datos ---
def get_connection():
    return sqlite3.connect("biblioteca.db", check_same_thread=False)

def crear_tablas():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fecha TEXT,
            rango_edad TEXT,
            motivo TEXT,
            motivo_otro TEXT,
            libro TEXT,
            genero TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS eventos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT,
            fecha TEXT,
            asistentes INTEGER,
            motivo TEXT,
            dias_aviso INTEGER
        )
    """)
    conn.commit()
    conn.close()

crear_tablas()

# --- 1. Lista Oficial de Géneros Literarios ---
GENEROS = [
    "Narrativo / Novela",
    "Narrativo / Cuento",
    "Literatura Argentina / Latinoamericana",
    "Infantil / Juvenil",
    "Fantasía",
    "Ciencia ficción",
    "Literatura romántica",
    "Poesía / Lírico",
    "Ensayo / Filosófico",
    "Historia / Biografía",
    "Autoayuda / Desarrollo personal",
    "Ciencia y tecnología",
    "Cómic / Manga",
    "Teatro / Dramático",
    "Otro"
]

# --- 2. Catálogo Local de Libros Conocidos ---
LIBROS_LOCALES = {
    "el principito": "Narrativo / Cuento",
    "cien años de soledad": "Literatura Argentina / Latinoamericana",
    "don quijote": "Narrativo / Novela",
    "don quijote de la mancha": "Narrativo / Novela",
    "1984": "Ciencia ficción",
    "rayuela": "Literatura Argentina / Latinoamericana",
    "facciones": "Literatura Argentina / Latinoamericana",
    "el aleph": "Literatura Argentina / Latinoamericana",
    "ficciones": "Literatura Argentina / Latinoamericana",
    "mi planta de naranja lima": "Infantil / Juvenil",
    "martín fierro": "Literatura Argentina / Latinoamericana",
    "el hobbit": "Fantasía",
    "harry potter": "Infantil / Juvenil",
    "el señor de los anillos": "Fantasía",
    "orgullo y prejuicio": "Literatura romántica",
    "hábitos atómicos": "Autoayuda / Desarrollo personal",
    "padre rico padre pobre": "Autoayuda / Desarrollo personal"
}

# --- 3. Mapeo para interpretar etiquetas de APIs externas ---
MAPEO_GENEROS = {
    "argentina": "Literatura Argentina / Latinoamericana",
    "latin american": "Literatura Argentina / Latinoamericana",
    "fiction": "Narrativo / Novela",
    "novel": "Narrativo / Novela",
    "novela": "Narrativo / Novela",
    "narrative": "Narrativo / Novela",
    "story": "Narrativo / Cuento",
    "cuento": "Narrativo / Cuento",
    "children": "Infantil / Juvenil",
    "infantil": "Infantil / Juvenil",
    "juvenil": "Infantil / Juvenil",
    "fantasy": "Fantasía",
    "fantasía": "Fantasía",
    "science fiction": "Ciencia ficción",
    "ciencia ficción": "Ciencia ficción",
    "romance": "Literatura romántica",
    "romántica": "Literatura romántica",
    "poetry": "Poesía / Lírico",
    "poesía": "Poesía / Lírico",
    "essay": "Ensayo / Filosófico",
    "philosophy": "Ensayo / Filosófico",
    "filosofía": "Ensayo / Filosófico",
    "history": "Historia / Biografía",
    "biography": "Historia / Biografía",
    "self-help": "Autoayuda / Desarrollo personal",
    "autoayuda": "Autoayuda / Desarrollo personal",
    "technology": "Ciencia y tecnología",
    "comics": "Cómic / Manga",
    "drama": "Teatro / Dramático",
    "plays": "Teatro / Dramático"
}

def _detectar_por_texto(texto):
    texto = texto.lower()
    candidatos = []
    for clave, valor in MAPEO_GENEROS.items():
        if clave in texto:
            candidatos.append((len(clave), valor))
    if not candidatos:
        return None
    candidatos.sort(reverse=True)
    return candidatos[0][1]

def buscar_genero_open_library(titulo):
    try:
        resp = requests.get(
            "https://openlibrary.org/search.json",
            params={"title": titulo, "limit": 3},
            timeout=8
        )
        docs = resp.json().get("docs", [])
        for doc in docs:
            key = doc.get("key")
            if not key:
                continue
            work_resp = requests.get(f"https://openlibrary.org{key}.json", timeout=8)
            subjects = work_resp.json().get("subjects", [])
            if subjects:
                resultado = _detectar_por_texto(" ".join(subjects))
                if resultado:
                    return resultado
        return None
    except Exception:
        return None

def buscar_genero_google_books(titulo):
    try:
        resp = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": f"intitle:{titulo}", "maxResults": 5},
            timeout=8
        )
        items = resp.json().get("items", [])
        for item in items:
            categorias = item.get("volumeInfo", {}).get("categories", [])
            if categorias:
                resultado = _detectar_por_texto(" ".join(categorias))
                if resultado:
                    return resultado
        return None
    except Exception:
        return None

def buscar_genero(titulo):
    if not titulo:
        return None
        
    titulo_limpio = titulo.strip().lower()
    
    # 1. Comprobar catálogo local
    for libro_clave, genero_exacto in LIBROS_LOCALES.items():
        if libro_clave in titulo_limpio:
            return genero_exacto

    # 2. Si no está local, buscar en internet
    resultado = buscar_genero_open_library(titulo)
    if resultado:
        return resultado
    return buscar_genero_google_books(titulo)

st.set_page_config(page_title="Sistema Biblioteca", page_icon="📚", layout="wide")

st.markdown("""
<style>
.stApp {
    background-color: #F7F7FC;
}
.metric-card {
    background: white;
    padding: 22px;
    border-radius: 16px;
    text-align: center;
    box-shadow: 0 4px 14px rgba(108, 92, 231, 0.12);
    border: none;
}
.metric-card h3 {
    color: #6C5CE7;
    font-size: 2.1em;
    margin-bottom: 4px;
}
.header-banner {
    background: linear-gradient(135deg, #6C5CE7, #A29BFE);
    padding: 26px;
    border-radius: 18px;
    color: white;
    margin-bottom: 22px;
    box-shadow: 0 4px 14px rgba(108, 92, 231, 0.25);
}
.header-banner h1 {
    margin: 0;
}
.header-banner p {
    margin: 4px 0 0 0;
    opacity: 0.9;
}
section[data-testid="stSidebar"] {
    background-color: #EDEBFA;
}
div.stButton > button {
    height: 3.2em;
    font-size: 1.05em;
    border-radius: 14px;
    border: none;
    background-color: white;
    box-shadow: 0 2px 6px rgba(0,0,0,0.06);
}
div.stButton > button:hover {
    background-color: #6C5CE7;
    color: white;
}
[data-testid="stForm"], div[data-testid="stVerticalBlockBorderWrapper"] {
    background-color: white;
    border-radius: 16px;
    padding: 8px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.06);
}
</style>
""", unsafe_allow_html=True)

RANGOS_EDAD = ["Niño (0-12)", "Adolescente (13-17)", "Joven (18-25)", "Adulto (26-59)", "Adulto mayor (60+)"]
MOTIVOS = ["Lectura en sala", "Préstamo de libros", "Uso de computadoras/internet",
           "Estudio/tarea", "Actividad cultural", "Consulta/referencia", "Otro"]
MOTIVOS_EVENTO = ["Taller", "Charla/Conferencia", "Club de lectura", "Exposición",
                   "Actividad infantil", "Presentación de libro", "Otro"]

if "pagina" not in st.session_state:
    st.session_state.pagina = "Inicio"

st.sidebar.markdown("## 📚 Menú")
if st.sidebar.button("🏠 Inicio", use_container_width=True):
    st.session_state.pagina = "Inicio"
if st.sidebar.button("📝 Registrar visita", use_container_width=True):
    st.session_state.pagina = "Registrar visita"
if st.sidebar.button("🎉 Registrar evento", use_container_width=True):
    st.session_state.pagina = "Registrar evento"
if st.sidebar.button("📊 Reportes", use_container_width=True):
    st.session_state.pagina = "Reportes"

opcion = st.session_state.pagina

def eventos_proximos():
    conn = get_connection()
    eventos = pd.read_sql_query("SELECT * FROM eventos", conn)
    conn.close()
    if eventos.empty:
        return eventos
    eventos["fecha"] = pd.to_datetime(eventos["fecha"])
    hoy = pd.Timestamp(date.today())
    eventos["dias_restantes"] = (eventos["fecha"] - hoy).dt.days
    return eventos[(eventos["dias_restantes"] >= 0) & (eventos["dias_restantes"] <= eventos["dias_aviso"])]

def mostrar_recordatorios():
    proximos = eventos_proximos()
    if not proximos.empty:
        for _, ev in proximos.iterrows():
            dias = int(ev["dias_restantes"])
            texto_dias = "hoy" if dias == 0 else f"en {dias} día(s)"
            st.warning(f"🔔 Recordatorio: el evento **{ev['nombre']}** es {texto_dias} ({ev['fecha'].date()}).")

# --- Inicio ---
if opcion == "Inicio":
    st.markdown('<div class="header-banner"><h1>📚 Sistema de Biblioteca</h1><p>Registro y estadísticas de afluencia</p></div>', unsafe_allow_html=True)
    mostrar_recordatorios()

    conn = get_connection()
    visitas = pd.read_sql_query("SELECT * FROM visitas", conn)
    eventos = pd.read_sql_query("SELECT * FROM eventos", conn)
    conn.close()

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f'<div class="metric-card"><h3>{len(visitas)}</h3>Visitas registradas</div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="metric-card"><h3>{len(eventos)}</h3>Eventos registrados</div>', unsafe_allow_html=True)
    with col3:
        total_asist = int(eventos["asistentes"].sum()) if not eventos.empty else 0
        st.markdown(f'<div class="metric-card"><h3>{total_asist}</h3>Asistentes a eventos</div>', unsafe_allow_html=True)

    if not eventos.empty:
        st.subheader("Próximos eventos")
        st.dataframe(eventos[["nombre", "fecha", "motivo", "asistentes"]], use_container_width=True)

# --- Registrar visita ---
elif opcion == "Registrar visita":
    st.header("📝 Registrar visita")
    with st.container(border=True):
        rango_edad = st.selectbox("Rango de edad", RANGOS_EDAD)
        motivo = st.selectbox("Motivo de la visita", MOTIVOS)

        motivo_otro = ""
        libro = ""
        genero = ""

        if motivo == "Otro":
            motivo_otro = st.text_input("Especificar motivo de la visita:")

        if motivo == "Préstamo de libros":
            libro = st.text_input("Título del libro")

            if st.button("🔍 Buscar género automáticamente"):
                if libro.strip() == "":
                    st.warning("Escribí primero el título del libro.")
                else:
                    with st.spinner("Buscando..."):
                        detectado = buscar_genero(libro)
                    if detectado:
                        st.session_state["genero_auto"] = detectado
                        st.success(f"Género detectado: {detectado}")
                    else:
                        st.warning("No se encontró género para ese libro. Elegilo manualmente abajo.")

            genero_sugerido = st.session_state.get("genero_auto", GENEROS[0])
            indice = GENEROS.index(genero_sugerido) if genero_sugerido in GENEROS else 0
            genero = st.selectbox("Género literario (podés corregirlo)", GENEROS, index=indice)

            if genero == "Otro":
                genero_otro_texto = st.text_input("Especificar género literario:")
                if genero_otro_texto.strip():
                    genero = f"Otro: {genero_otro_texto.strip()}"

        if st.button("Guardar visita"):
            conn = get_connection()
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO visitas (fecha, rango_edad, motivo, motivo_otro, libro, genero)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (str(date.today()), rango_edad, motivo, motivo_otro, libro, genero))
            conn.commit()
            conn.close()
            if "genero_auto" in st.session_state:
                del st.session_state["genero_auto"]
            st.success("Visita registrada correctamente ✅")

# --- Registrar evento ---
elif opcion == "Registrar evento":
    st.header("🎉 Registrar evento especial")
    with st.container(border=True):
        nombre = st.text_input("Nombre del evento")
        motivo_evento = st.selectbox("Motivo / tipo de evento", MOTIVOS_EVENTO)
        
        if motivo_evento == "Otro":
            motivo_evento_otro = st.text_input("Especificar motivo/tipo de evento:")
            if motivo_evento_otro.strip():
                motivo_evento = motivo_evento_otro

        fecha_evento = st.date_input("Fecha del evento", value=date.today())
        asistentes = st.number_input("Cantidad de asistentes (aproximadamente)", min_value=0, step=1)
        dias_aviso = st.number_input("¿Con cuántos días de anticipación querés el recordatorio?", min_value=0, step=1, value=3)

        if st.button("Guardar evento"):
            if nombre.strip() == "":
                st.error("⚠️ Por favor, poné un nombre para el evento.")
            else:
                dias_restantes = (fecha_evento - date.today()).days
                
                if dias_restantes < 0:
                    st.error("⚠️ La fecha del evento ya pasó. Elegí una fecha de hoy en adelante.")
                elif dias_restantes == 0 and dias_aviso > 0:
                    st.warning("⚠️ El evento es HOY. Se registrará, pero no requiere días de aviso previos.")
                    dias_aviso = 0
                    
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO eventos (nombre, fecha, asistentes, motivo, dias_aviso)
                        VALUES (?, ?, ?, ?, ?)
                    """, (nombre, str(fecha_evento), asistentes, motivo_evento, dias_aviso))
                    conn.commit()
                    conn.close()
                    st.success("Evento registrado correctamente ✅")

                elif dias_aviso >= dias_restantes and dias_restantes > 0:
                    st.error(f"⚠️ Faltan solo {dias_restantes} día(s) para el evento. La cantidad de días de aviso ({dias_aviso}) debe ser menor a {dias_restantes}.")
                else:
                    conn = get_connection()
                    cur = conn.cursor()
                    cur.execute("""
                        INSERT INTO eventos (nombre, fecha, asistentes, motivo, dias_aviso)
                        VALUES (?, ?, ?, ?, ?)
                    """, (nombre, str(fecha_evento), asistentes, motivo_evento, dias_aviso))
                    conn.commit()
                    conn.close()
                    st.success("Evento registrado correctamente ✅")

# --- Reportes ---
elif opcion == "Reportes":
    st.header("📊 Reportes y Estadísticas")
    mostrar_recordatorios()

    conn = get_connection()
    visitas = pd.read_sql_query("SELECT * FROM visitas", conn)
    eventos = pd.read_sql_query("SELECT * FROM eventos", conn)
    conn.close()

    # --- Filtro de Fechas ---
    st.subheader("📅 Filtrar período")
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        fecha_inicio = st.date_input("Fecha desde", value=date.today())
    with col_f2:
        fecha_fin = st.date_input("Fecha hasta", value=date.today())

    # Filtrar visitas por fecha
    if not visitas.empty:
        visitas["fecha_dt"] = pd.to_datetime(visitas["fecha"]).dt.date
        visitas_filtradas = visitas[(visitas["fecha_dt"] >= fecha_inicio) & (visitas["fecha_dt"] <= fecha_fin)]
    else:
        visitas_filtradas = visitas

    st.markdown("---")
    st.subheader("Cantidad total de visitantes")
    st.metric("Total de visitas en el período seleccionado", len(visitas_filtradas))

    if not visitas_filtradas.empty:
        # Gráficos de Edades y Motivos
        col_g1, col_g2 = st.columns(2)
        
        with col_g1:
            st.markdown("### Rango de edad de los usuarios")
            conteo_edad = visitas_filtradas["rango_edad"].value_counts().reset_index()
            conteo_edad.columns = ["Rango de edad", "Cantidad"]
            fig_edad = px.pie(conteo_edad, names="Rango de edad", values="Cantidad", hole=0.35)
            fig_edad.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_edad, use_container_width=True)

        with col_g2:
            st.markdown("### Motivos de visita")
            conteo_motivo = visitas_filtradas["motivo"].value_counts().reset_index()
            conteo_motivo.columns = ["Motivo", "Cantidad"]
            fig_motivo = px.pie(conteo_motivo, names="Motivo", values="Cantidad")
            fig_motivo.update_traces(textinfo="percent+label")
            st.plotly_chart(fig_motivo, use_container_width=True)

        # Análisis de Préstamos de Libros
        prestamos = visitas_filtradas[visitas_filtradas["motivo"] == "Préstamo de libros"].dropna(subset=["genero"])
        prestamos = prestamos[prestamos["genero"] != ""]
        
        if not prestamos.empty:
            st.markdown("---")
            st.subheader("📖 Géneros más leídos por rango de edad")
            rangos_con_datos = [r for r in RANGOS_EDAD if r in prestamos["rango_edad"].unique()]
            cols = st.columns(2)
            for i, rango in enumerate(rangos_con_datos):
                sub = prestamos[prestamos["rango_edad"] == rango]
                conteo = sub["genero"].value_counts().reset_index()
                conteo.columns = ["Género", "Cantidad"]
                fig = px.pie(conteo, names="Género", values="Cantidad", title=f"Edad: {rango}", hole=0.35)
                fig.update_traces(textinfo="percent+label")
                with cols[i % 2]:
                    st.plotly_chart(fig, use_container_width=True)

        st.markdown("### Tabla detallada de visitas")
        st.dataframe(visitas_filtradas.drop(columns=["fecha_dt"], errors="ignore"), use_container_width=True)
    else:
        st.info("No hay visitas registradas en el rango de fechas seleccionado.")

    st.markdown("---")
    st.subheader("🎉 Registro de eventos")
    if not eventos.empty:
        st.metric("Total de asistentes a eventos", int(eventos["asistentes"].sum()))
        fig_eventos = px.bar(eventos, x="nombre", y="asistentes", color_discrete_sequence=["#6C5CE7"])
        st.plotly_chart(fig_eventos, use_container_width=True)
        st.dataframe(eventos, use_container_width=True)
    else:
        st.info("Todavía no hay eventos registrados.")
