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

# 4. PROCESAMIENTO
if st.button("🚀 INICIAR CORRECCIÓN"):
    if not api_key or not archivos or not consigna:
        st.error("Por favor, complete la API Key, las preguntas y suba al menos un archivo.")
    else:
        lista_resultados = []
        barra_progreso = st.progress(0)
        
        for index, arc in enumerate(archivos):
            with st.spinner(f"Analizando: {arc.name}..."):
                texto_extraido = ""
                imagenes_paginas = []

                try:
                    # Procesar PDF
                    if arc.name.endswith('.pdf'):
                        documento = fitz.open(stream=arc.read(), filetype="pdf")
                        for pagina in documento:
                            texto_extraido += pagina.get_text()
                            # Capturar imagen de la página para visión
                            pix = pagina.get_pixmap()
                            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                            imagenes_paginas.append(preparar_imagen(img))
                    # Procesar Word
                    else:
                        texto_extraido = docx2txt.process(arc)

                    client = Groq(api_key=api_key)
                    
                    # Instrucciones para la IA
                    instruccion = f"""
                    Actúa como un profesor de Derecho riguroso. 
                    Evalúa el examen comparándolo con la RESPUESTA MODELO.
                    
                    CONSIGNA: {consigna}
                    RESPUESTA MODELO: {respuesta_modelo}
                    
                    TAREA:
                    1. Analiza cada punto por separado.
                    2. Evalúa texto y esquemas gráficos si los hay.
                    3. Para cada punto indica: [BIEN/REGULAR/MAL] + Justificación.
                    4. Al final da una NOTA FINAL: (MAL, REGULAR, BIEN, MUY BIEN, EXCELENTE).
                    """

                    # Estructura de mensajes compatible con Llama 3.2 Vision
                    contenido_usuario = [{"type": "text", "text": f"{instruccion}\n\nTEXTO DEL EXAMEN:\n{texto_extraido}"}]
                    
                    # Añadir hasta 3 páginas como imágenes
                    for b64 in imagenes_paginas[:3]:
                        contenido_usuario.append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                        })

                    mensajes = [{"role": "user", "content": contenido_usuario}]

                    # LLAMADA AL MODELO (Actualizado 2026)
                    chat_completion = client.chat.completions.create(
                       model="llama-3.2-90b-vision",
                        messages=mensajes,
                        temperature=0.2 # Menos creatividad, más precisión
                    )

                    analisis = chat_completion.choices[0].message.content
                    lista_resultados.append({"Alumno/Archivo": arc.name, "Evaluación": analisis})
                
                except Exception as e:
                    lista_resultados.append({"Alumno/Archivo": arc.name, "Evaluación": f"Error: {str(e)}"})
                
                barra_progreso.progress((index + 1) / len(archivos))

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
