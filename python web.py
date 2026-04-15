import streamlit as st
from groq import Groq
import docx2txt
import fitz  # PyMuPDF
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

# 1. CONFIGURACIÓN DE LA PÁGINA
st.set_page_config(page_title="Asistente de Cátedra", layout="wide")

st.title("⚖️ Sistema de Corrección de Cátedra")
st.markdown("### Herramienta de Evaluación Automática (Texto y Gráficos)")

# 2. PANEL LATERAL: CONFIGURACIÓN DEL DOCENTE
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    st.divider()
    
    st.subheader("📝 Definición del Examen")
    consigna = st.text_area("Preguntas oficiales (numeradas):", 
                            placeholder="1. Explique...\n2. Dibuje...", height=150)
    
    respuesta_modelo = st.text_area("Criterios de Corrección / Respuesta Ideal:", 
                                   placeholder="Punto 1: El alumno debe decir...\nPunto 2: El gráfico debe mostrar...", height=150)
    
    st.info("Escala: MAL, REGULAR, BIEN, MUY BIEN, EXCELENTE.")

# Función para convertir imagen para la IA
def preparar_imagen(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# 3. CARGA DE ARCHIVOS
st.header("📂 Cargar Exámenes")
archivos = st.file_uploader("Suba los PDFs o Word de los alumnos", 
                            type=['pdf', 'docx'], 
                            accept_multiple_files=True)

# 4. PROCESAMIENTO (VERSIÓN OPTIMIZADA PARA EVITAR LÍMITES)
if st.button("🚀 INICIAR CORRECCIÓN"):
    if not api_key or not archivos or not consigna:
        st.error("Falta configuración (API Key, Consigna o Archivos).")
    else:
        lista_resultados = []
        barra_progreso = st.progress(0)
        
        for index, arc in enumerate(archivos):
            with st.spinner(f"Analizando: {arc.name}..."):
                texto_extraido = ""
                try:
                    if arc.name.endswith('.pdf'):
                        documento = fitz.open(stream=arc.read(), filetype="pdf")
                        for pagina in documento:
                            texto_extraido += pagina.get_text()
                    else:
                        texto_extraido = docx2txt.process(arc)

                    # --- RECORTE DE SEGURIDAD PARA NO SUPERAR EL LÍMITE ---
                    # Limitamos el texto del alumno a unos 8000 caracteres (aprox 2000 palabras)
                    # Esto deja espacio para la consigna y la respuesta de la IA.
                    texto_recortado = texto_extraido[:8000] 

                    client = Groq(api_key=api_key)
                    
                    instruccion = f"""
                    Actúa como profesor de Derecho. Sé conciso pero preciso.
                    CONSIGNA: {consigna}
                    MODELO: {respuesta_modelo}
                    
                    TAREA:
                    - Evalúa cada punto (BIEN/REGULAR/MAL).
                    - Da una nota final.
                    """

                    chat_completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[
                            {
                                "role": "user",
                                "content": f"{instruccion}\n\nEXAMEN:\n{texto_recortado}"
                            }
                        ],
                        temperature=0.2,
                        max_tokens=1500  # Limitamos el largo de la respuesta de la IA para ahorrar
                    )

                    analisis = chat_completion.choices[0].message.content
                    lista_resultados.append({"Alumno": arc.name, "Evaluación": analisis})
                
                except Exception as e:
                    lista_resultados.append({"Alumno": arc.name, "Evaluación": f"Error: {str(e)}"})
                
                barra_progreso.progress((index + 1) / len(archivos))

        # 5. RESULTADOS
        st.divider()
        st.header("📊 Resultados")
        for res in lista_resultados:
            with st.expander(f"📝 Examen: {res['Alumno']}"):
                st.markdown(res['Evaluación'])

        # 5. RESULTADOS
        st.divider()
        st.header("📊 Resultados")
        for res in lista_resultados:
            with st.expander(f"📝 Examen: {res['Alumno/Archivo']}"):
                st.markdown(res['Evaluación'])
        
        if lista_resultados:
            df = pd.DataFrame(lista_resultados)
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Planilla Excel", csv, "notas_catedra.csv", "text/csv")
