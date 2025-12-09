import streamlit as st
import pandas as pd
import altair as alt

# -----------------------------------------------------
# Configuración general de la página
# -----------------------------------------------------
st.set_page_config(page_title="Tablero e-BEO", layout="wide")

# -----------------------------------------------------
# Funciones auxiliares
# -----------------------------------------------------

def clasificar_percentil(p):
    """
    Asigna un rango cualitativo según el percentil.
    Rangos aproximados basados en desviaciones típicas:
    Muy bajo, Bajo, Medio-bajo, Medio, Medio-alto, Alto, Muy alto.
    """
    if pd.isna(p):
        return None
    p = float(p)
    if p <= 2:
        return "Muy bajo"
    elif p <= 15:
        return "Bajo"
    elif p <= 30:
        return "Medio-bajo"
    elif p <= 69:
        return "Medio"
    elif p <= 84:
        return "Medio-alto"
    elif p <= 97:
        return "Alto"
    else:
        return "Muy alto"


def sheet_to_long(df: pd.DataFrame, area: str) -> pd.DataFrame:
    # Normalizar nombre de columna
    df = df.rename(columns={'Número lista': 'Numero lista'})
    personal = {'Numero lista', 'NIA', 'Nombre', 'Apellidos'}
    base_cols = [c for c in df.columns if c in ['Clase', 'Sexo']]
    value_cols = [c for c in df.columns
                  if c not in personal and c not in base_cols]

    long_df = df.melt(
        id_vars=base_cols,
        value_vars=value_cols,
        var_name='Variable',
        value_name='Puntuacion'
    )
    long_df['Area'] = area
    long_df['Puntuacion'] = pd.to_numeric(long_df['Puntuacion'],
                                          errors='coerce')
    return long_df


def ipp_sheet_to_long(xls: pd.ExcelFile) -> pd.DataFrame:
    """
    Pasa la hoja de orientación vocacional (IPP-R) a formato largo.
    Usa cabecera en dos filas (área / Actividades - Profesiones).
    """
    df = pd.read_excel(
        xls,
        "Orientación vocacional - IPP-R",
        header=[0, 1]
    )
    base1 = ['Clase', 'Número lista', 'NIA', 'Nombre', 'Apellidos', 'Sexo']
    base_cols = [col for col in df.columns if col[1] in base1]
    var_cols = [col for col in df.columns if col not in base_cols]

    data = {}
    # columnas base (Clase, Sexo, etc.)
    for col in base_cols:
        name = col[1]
        if name == 'Número lista':
            name = 'Numero lista'
        data[name] = df[col]

    # variables de orientación vocacional
    for col in var_cols:
        name = f"{col[0]} - {col[1]}"  # ej. "Campo científico - Actividades"
        data[name] = df[col]

    df2 = pd.DataFrame(data)
    personal = {'Numero lista', 'NIA', 'Nombre', 'Apellidos'}
    base_cols_simple = [c for c in df2.columns if c in ['Clase', 'Sexo']]
    value_cols = [c for c in df2.columns
                  if c not in personal and c not in base_cols_simple]

    long_df = df2.melt(
        id_vars=base_cols_simple,
        value_vars=value_cols,
        var_name='Variable',
        value_name='Puntuacion'
    )
    long_df['Area'] = 'Orientación vocacional (IPP-R)'
    long_df['Puntuacion'] = pd.to_numeric(long_df['Puntuacion'],
                                          errors='coerce')
    return long_df


@st.cache_data
def build_long_dataset(path: str) -> pd.DataFrame:
    """
    Carga el Excel, pasa todo a formato largo y limpia valores especiales (-999).
    """
    xls = pd.ExcelFile(path)
    sheets = {name: pd.read_excel(xls, name) for name in xls.sheet_names}

    parts = []
    parts.append(sheet_to_long(
        sheets['Ap. intelectuales - EFAI 4'],
        'Aptitudes intelectuales (EFAI 4)'
    ))
    parts.append(sheet_to_long(
        sheets['Ap. intelectuales - BAT 7-S'],
        'Aptitudes intelectuales (BAT 7-S)'
    ))
    parts.append(sheet_to_long(
        sheets['Atención - CARAS-R, Test de Pe'],
        'Atención (CARAS-R)'
    ))
    parts.append(sheet_to_long(
        sheets['Atención - BAT 7-S'],
        'Atención (BAT 7-S)'
    ))
    parts.append(sheet_to_long(
        sheets['Inteligencia emocional - CTI'],
        'Inteligencia emocional (CTI)'
    ))
    parts.append(ipp_sheet_to_long(xls))

    big = pd.concat(parts, ignore_index=True)

    # Limpiar puntuaciones: numérico y sin códigos negativos (-999 = sin dato)
    big['Puntuacion'] = pd.to_numeric(big['Puntuacion'], errors='coerce')
    big.loc[big['Puntuacion'] < 0, 'Puntuacion'] = pd.NA
    big = big.dropna(subset=['Puntuacion'])

    return big


# -----------------------------------------------------
# Carga de datos
# -----------------------------------------------------

excel_path = "Ebeo_Percentiles.xlsx"   # Ajusta si está en otra ruta
data = build_long_dataset(excel_path)

# Añadir el rango cualitativo por percentil
data = data.copy()
data['Rango'] = data['Puntuacion'].apply(clasificar_percentil)

orden_rangos = [
    "Muy bajo", "Bajo", "Medio-bajo",
    "Medio", "Medio-alto", "Alto", "Muy alto"
]
# -----------------------------------------------------
# Definiciones simples por variable (para no psicólogos)
# Basadas en los epígrafes "¿Qué evalúa?" del informe e-BEO.
# -----------------------------------------------------

VARIABLE_INFO = {
    # ---------------- Aptitudes intelectuales (EFAI 4 / BAT 7-S) ----------------
    "Aptitud espacial": (
        "Habilidad para imaginar y manipular mentalmente objetos "
        "(girarlos, moverlos), orientarse y comprender relaciones espaciales."
    ),
    "Aptitud numérica": (
        "Habilidad para razonar con números: realizar operaciones, "
        "resolver problemas numéricos e interpretar tablas y gráficos."
    ),
    "Razonamiento abstracto": (
        "Habilidad para descubrir reglas y relaciones lógicas en problemas "
        "nuevos o con figuras/series abstractas."
    ),
    "Aptitud verbal": (
        "Habilidad para comprender y razonar con palabras; "
        "se relaciona con vocabulario y comprensión de conceptos."
    ),

    # ---------------- Atención (BAT 7-S) ----------------
    # Según el manual, son dos componentes complementarios:
    "Atención": (
        "Velocidad para identificar información relevante e ignorar lo irrelevante "
        "en tareas visuales. Se asocia a rapidez de procesamiento."
    ),
    "Concentración": (
        "Precisión al procesar información visual, independiente de la velocidad. "
        "Se asocia a calidad del procesamiento."
    ),
    # Variantes frecuentes de nombre en hojas:
    "Atención (A)": (
        "Velocidad para identificar información relevante e ignorar lo irrelevante "
        "en tareas visuales."
    ),
    "Concentración (CON)": (
        "Precisión del procesamiento visual, independiente de la velocidad."
    ),

    # ---------------- Atención y percepción (CARAS-R) ----------------
    "Aciertos netos (A-E)": (
        "Eficacia visoperceptiva y atencional considerando aciertos y errores."
    ),
    "Control impulsividad (ICI)": (
        "Grado de control al responder; refleja un estilo más impulsivo o más reflexivo."
    ),

    # ---------------- Inteligencia emocional (CTI) ----------------
    "Pensamiento constructivo global (PCG)": (
        "Indicador general de la forma de pensar que facilita o dificulta "
        "afrontar problemas de manera eficaz."
    ),
    "Afrontamiento emocional": (
        "Forma de manejar emociones negativas con autoaceptación, resiliencia "
        "y sin sobregeneralizar ni rumiar en exceso."
    ),
    "Autoaceptación": (
        "Autoestima y actitud favorable hacia uno mismo."
    ),
    "Aus. de sobregeneralización": (
        "Capacidad de interpretar experiencias negativas sin concluir que 'todo saldrá mal'."
    ),
    "Aus. de hipersensibilidad": (
        "Resiliencia ante críticas, contratiempos o incertidumbre."
    ),
    "Aus. de rumiaciones": (
        "Tendencia baja a quedarse enganchado a lo negativo."
    ),
    "Afrontamiento conductual": (
        "Forma de pensar que impulsa acciones eficaces ante problemas."
    ),
    "Pensamiento positivo": (
        "Tendencia a interpretar situaciones de forma realista y favorable para actuar."
    ),
    "Orientación a la acción": (
        "Tendencia a actuar ante los problemas en vez de postergar."
    ),
    "Responsabilidad": (
        "Planificación y cuidado al realizar tareas."
    ),
    "Pensamiento mágico": (
        "Tendencia a supersticiones privadas o ideas no basadas en evidencia."
    ),
    "Pensamiento categórico": (
        "Tendencia a ver la realidad en blanco/negro, con poca tolerancia a matices."
    ),
    "Pensamiento polarizado": (
        "Componente de rigidez cognitiva tipo 'todo o nada'."
    ),
    "Suspicacia": (
        "Tendencia a desconfiar o interpretar intenciones negativas en otros."
    ),
    "Intransigencia": (
        "Dificultad para aceptar diferencias en los demás."
    ),
    "Pensamiento esotérico": (
        "Tendencia a creer en fenómenos mágicos o paranormales."
    ),
    "Creencias paranormales": (
        "Creencia en fenómenos como lectura de mente, fantasmas, clarividencia, etc."
    ),
    "Pensamiento supersticioso": (
        "Creencia en supersticiones convencionales y agüeros."
    ),
    "Optimismo ingenuo": (
        "Optimismo sin suficiente fundamento; puede llevar a decisiones poco realistas."
    ),
    "Pensamiento exagerado": (
        "Esperar éxitos encadenados tras un resultado favorable."
    ),
    "Pensamiento estereotipado": (
        "Creencias idealizadas o simplificadas sobre la realidad social."
    ),
    "Ingenuidad": (
        "Tendencia a asumir que los demás actuarán siempre con buenas intenciones."
    ),
}

def get_variable_info(area: str, variable: str) -> str:
    """
    Devuelve una explicación breve y amigable para no psicólogos.
    Incluye lógica especial para IPP-R, porque sus nombres se construyen como:
    'Campo X - Actividades' / 'Campo X - Profesiones'.
    """
    # IPP-R dinámico
    if area.startswith("Orientación vocacional") and " - " in variable:
        campo, tipo = variable.split(" - ", 1)
        tipo_low = tipo.strip().lower()
        if tipo_low.startswith("activ"):
            return f"Interés por las actividades típicas del **{campo}**."
        if tipo_low.startswith("prof"):
            return f"Interés por profesiones representativas del **{campo}**."
        return f"Interés relativo en el **{campo}**."

    return VARIABLE_INFO.get(
        variable,
        "Variable específica de la prueba seleccionada. "
        "Si quieres, puedo ayudarte a añadir su definición exacta cuando veamos el nombre tal cual aparece en tu Excel."
    )

# -----------------------------------------------------
# Interfaz principal
# -----------------------------------------------------

st.title("Tablero de resultados Orientación")
st.caption("Visualización de percentiles, rangos cualitativos e interpretación grupal por área, prueba, variable y sexo (sin datos personales).")

with st.expander("¿Cómo se interpretan los percentiles y los rangos?"):
    st.markdown(
        """
- Los **percentiles** van de 1 a 99 y expresan la **posición relativa** del estudiante frente al grupo normativo.
- Un percentil 50 implica que el resultado es similar al de la mitad del grupo; un percentil 75 indica que está por encima del 75 % del grupo, etc.
- Para facilitar la lectura, agrupamos los percentiles en 7 **rangos cualitativos** aproximados:

  - **Muy bajo**: percentiles ≤ 2  
  - **Bajo**: 3–15  
  - **Medio-bajo**: 16–30  
  - **Medio**: 31–69  
  - **Medio-alto**: 70–84  
  - **Alto**: 85–97  
  - **Muy alto**: 98–99  

Estos rangos siguen la lógica del informe (basada en desviaciones típicas) y están pensados para describir 
si el grupo se sitúa por debajo, en torno o por encima del promedio del grupo normativo.
        """
    )

# ---------------- Filtros globales (no personales) ----------------

col1, col2 = st.columns(2)

with col1:
    clases = sorted(data['Clase'].dropna().unique())
    clases_sel = st.multiselect(
        "Filtrar por sede/curso (columna 'Clase')",
        options=clases,
        default=clases
    )

with col2:
    sexos = sorted(data['Sexo'].dropna().unique())
    sexos_sel = st.multiselect(
        "Filtrar por sexo",
        options=sexos,
        default=sexos
    )

df_filtrado = data[
    data['Clase'].isin(clases_sel) &
    data['Sexo'].isin(sexos_sel)
].copy()

# ---------------- Selección de área y variables ----------------

st.markdown("### Selección de área y variables")

if df_filtrado.empty:
    st.warning("No hay datos con los filtros actuales (Clase / Sexo).")
    st.stop()

area_sel = st.selectbox(
    "Área de evaluación",
    options=sorted(df_filtrado['Area'].unique())
)

df_area = df_filtrado[df_filtrado['Area'] == area_sel].copy()

vars_disponibles = sorted(df_area['Variable'].unique())
vars_sel = st.multiselect(
    "Variables dentro del área",
    options=vars_disponibles,
    default=vars_disponibles
)

df_area = df_area[df_area['Variable'].isin(vars_sel)].copy()

if df_area.empty:
    st.warning("No hay datos para las variables seleccionadas.")
    st.stop()

# -----------------------------------------------------
# Bloque visible: significado de las variables seleccionadas
# -----------------------------------------------------

st.markdown("### ¿Qué miden estas variables? (explicación simple)")

with st.expander("Ver explicación de cada variable seleccionada", expanded=True):
    for v in vars_sel:
        st.markdown(f"**{v}**: {get_variable_info(area_sel, v)}")


# -----------------------------------------------------
# Resumen numérico agregado (grupo completo)
# -----------------------------------------------------

st.markdown("### Resumen estadístico por variable (percentiles del grupo)")

resumen = (
    df_area
    .groupby('Variable')['Puntuacion']
    .agg(['count', 'mean', 'median', 'std', 'min', 'max'])
    .reset_index()
    .rename(columns={
        'count': 'n',
        'mean': 'media',
        'median': 'mediana',
        'std': 'des_est',
        'min': 'minimo',
        'max': 'maximo'
    })
    .sort_values('media', ascending=False)
)

resumen['Rango_media'] = resumen['media'].apply(clasificar_percentil)

st.dataframe(
    resumen[['Variable', 'n', 'media', 'mediana', 'des_est', 'minimo', 'maximo', 'Rango_media']],
    use_container_width=True
)

# -----------------------------------------------------
# Gráficos agregados (grupo completo)
# -----------------------------------------------------

# 1) Media de percentiles por variable
st.markdown("### Gráfico 1: Media de percentiles por variable (grupo completo)")

chart_bar = (
    alt.Chart(resumen)
    .mark_bar()
    .encode(
        x=alt.X('Variable:N', sort='-y'),
        y=alt.Y('media:Q'),
        tooltip=['Variable', 'media', 'mediana', 'n', 'Rango_media']
    )
)

st.altair_chart(chart_bar, use_container_width=True)

# 2) Distribución de percentiles (boxplot)
st.markdown("### Gráfico 2: Distribución de percentiles por variable (boxplot, grupo completo)")

chart_box = (
    alt.Chart(df_area)
    .mark_boxplot()
    .encode(
        x=alt.X('Variable:N'),
        y=alt.Y('Puntuacion:Q'),
        tooltip=['Variable', 'Puntuacion']
    )
)

st.altair_chart(chart_box, use_container_width=True)

# 3) Distribución de rangos cualitativos (apilado jerárquico)
st.markdown("### Gráfico 3: Porcentaje de estudiantes en cada rango cualitativo (grupo completo)")

dist = (
    df_area
    .groupby(['Variable', 'Rango'])
    .size()
    .reset_index(name='n')
)

chart_rangos = (
    alt.Chart(dist)
    .mark_bar()
    .encode(
        x=alt.X('Variable:N'),
        y=alt.Y(
            'n:Q',
            stack='normalize',
            axis=alt.Axis(format='%', title='Proporción de estudiantes')
        ),
        # El orden jerárquico lo controla el sort de color
        color=alt.Color('Rango:N', sort=orden_rangos),
        tooltip=['Variable', 'Rango', 'n']
    )
)


st.altair_chart(chart_rangos, use_container_width=True)

st.markdown(
    """
    **Nota:** El gráfico muestra, para cada variable, qué porcentaje del grupo se sitúa
    en cada rango (Muy bajo, Bajo, Medio-bajo, Medio, Medio-alto, Alto, Muy alto),
    respetando este orden jerárquico tanto en la leyenda como en la pila.
    """
)

# -----------------------------------------------------
# Interpretación automática (grupo completo)
# -----------------------------------------------------

st.markdown("### Interpretación automática del grupo (por variable)")

interpretaciones = []
for _, row in resumen.iterrows():
    r = row['Rango_media']
    if r is None:
        continue
    var = row['Variable']
    media = row['media']

    if r in ["Muy bajo", "Bajo"]:
        extra = (
            "conviene revisar si existen factores contextuales o dificultades "
            "específicas que estén influyendo en esta área."
        )
    elif r in ["Medio-bajo", "Medio"]:
        extra = (
            "el rendimiento grupal es similar al de la mayoría de estudiantes "
            "del grupo normativo."
        )
    else:  # Medio-alto, Alto, Muy alto
        extra = (
            "se observa un punto fuerte del grupo en comparación con el grupo normativo."
        )

    definicion = get_variable_info(area_sel, var)

    interpretaciones.append(
        f"- **{var}**: {definicion} "
        f"Nivel grupal **{r}** (percentil medio ≈ {media:.0f}); {extra}"
    )
    
st.markdown(
    "Estas frases están pensadas para usarse en informes de grupo o presentaciones:"
)
for linea in interpretaciones:
    st.markdown(linea)

with st.expander("Guía rápida de lectura (para equipos no especializados)"):
    st.markdown(
        """
- Este tablero muestra resultados **agregados** por curso/sede y sexo.
- Las variables describen **habilidades, estilos de pensamiento o intereses** evaluados con pruebas estandarizadas.
- Una media alta no siempre es “mejor” en todas las escalas; depende de lo que mida la variable.
        """
    )

# -----------------------------------------------------
# NUEVO BLOQUE: Análisis desagregado por sexo
# -----------------------------------------------------

st.markdown("## Análisis desagregado por sexo")

# ---------------- Resumen por sexo y variable ----------------

resumen_sexo = (
    df_area
    .groupby(['Sexo', 'Variable'])['Puntuacion']
    .agg(['count', 'mean', 'median', 'std', 'min', 'max'])
    .reset_index()
    .rename(columns={
        'count': 'n',
        'mean': 'media',
        'median': 'mediana',
        'std': 'des_est',
        'min': 'minimo',
        'max': 'maximo'
    })
)

resumen_sexo['Rango_media'] = resumen_sexo['media'].apply(clasificar_percentil)

st.markdown("### Tabla 1. Resumen por variable y sexo (percentiles)")

st.dataframe(
    resumen_sexo[['Sexo', 'Variable', 'n', 'media', 'mediana', 'des_est', 'minimo', 'maximo', 'Rango_media']],
    use_container_width=True
)

# ---------------- Distribución de rangos por sexo ----------------

st.markdown("### Tabla 2. Distribución de rangos cualitativos por sexo y variable")

tabla_rangos_sexo = (
    df_area
    .groupby(['Sexo', 'Variable', 'Rango'])
    .size()
    .reset_index(name='n')
)

# calcular porcentaje dentro de cada Sexo-Variable
tabla_rangos_sexo['porcentaje'] = (
    tabla_rangos_sexo['n'] /
    tabla_rangos_sexo.groupby(['Sexo', 'Variable'])['n'].transform('sum') * 100
).round(1)

st.dataframe(
    tabla_rangos_sexo.sort_values(['Sexo', 'Variable', 'Rango']),
    use_container_width=True
)

# ---------------- Gráficos por sexo ----------------

st.markdown("### Gráfico 4: Media de percentiles por variable y sexo")

chart_bar_sexo = (
    alt.Chart(resumen_sexo)
    .mark_bar()
    .encode(
        x=alt.X('Variable:N', sort=resumen['Variable'].tolist()),
        y=alt.Y('media:Q'),
        color=alt.Color('Sexo:N', legend=None),
        tooltip=['Sexo', 'Variable', 'media', 'mediana', 'n', 'Rango_media']
    )
    .facet(
        column='Sexo:N'
    )
)

st.altair_chart(chart_bar_sexo, use_container_width=True)

st.markdown("### Gráfico 5: Distribución de percentiles por variable y sexo (boxplot)")

chart_box_sexo = (
    alt.Chart(df_area)
    .mark_boxplot()
    .encode(
        x=alt.X('Variable:N'),
        y=alt.Y('Puntuacion:Q'),
        color=alt.Color('Sexo:N', legend=None),
        tooltip=['Sexo', 'Variable', 'Puntuacion']
    )
    .facet(
        column='Sexo:N'
    )
)

st.altair_chart(chart_box_sexo, use_container_width=True)

# 6) Distribución de rangos cualitativos por variable y sexo (apilado jerárquico + facet)
st.markdown("### Gráfico 6: Porcentaje de estudiantes en cada rango, por variable y sexo")

dist_sexo = (
    df_area
    .groupby(['Sexo', 'Variable', 'Rango'])
    .size()
    .reset_index(name='n')
)

chart_rangos_sexo = (
    alt.Chart(dist_sexo)
    .mark_bar()
    .encode(
        x=alt.X('Variable:N'),
        y=alt.Y(
            'n:Q',
            stack='normalize',
            axis=alt.Axis(format='%', title='Proporción de estudiantes')
        ),
        color=alt.Color('Rango:N', sort=orden_rangos),
        tooltip=['Sexo', 'Variable', 'Rango', 'n']
    )
    .facet(
        column='Sexo:N'
    )
)

st.altair_chart(chart_rangos_sexo, use_container_width=True)

st.markdown(
    """
    En estos gráficos se ve, para cada **sexo**, cómo se distribuyen los percentiles
    y los rangos cualitativos en cada variable.  
    No se muestra ningún dato identificable (solo agregados por sexo, clase y área).
    """
)




