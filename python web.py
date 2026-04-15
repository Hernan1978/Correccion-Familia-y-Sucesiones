import streamlit as st
from groq import Groq
import docx2txt
import fitz  # PyMuPDF para manejar imágenes en PDFs
import pandas as pd
import base64
from io import BytesIO
from PIL import Image

st.set_page_config(page_title="Asistente de Cátedra con Visión", layout="wide")

st.title("⚖️ Corrector Privado con Visión Artificial")
st.write("Este asistente lee textos y analiza esquemas o dibujos en los exámenes.")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    consigna = st.text_area("Preguntas del examen:", height=100)
    respuesta_modelo = st.text_area("Criterios/Respuesta Ideal:", height=100)
    st.info("Escala: MAL, REGULAR, BIEN, MUY BIEN, EXCELENTE.")

# --- FUNCIÓN PARA PROCESAR IMÁGENES ---
def encode_image(image):
    buffered = BytesIO()
    image.save(buffered, format="JPEG")
    return base64.b64encode(buffered.getvalue()).decode('utf-8')

# --- CARGA DE EXÁMENES ---
archivos = st.file_uploader("Subí los exámenes (PDF/DOCX)", type=['pdf', 'docx'], accept_multiple_files=True)

if st.button("🚀 INICIAR CORRECCIÓN INTEGRAL"):
    if not api_key or not archivos:
        st.error("Faltan datos obligatorios.")
    else:
        resultados = []
        client = Groq(api_key=api_key)
        
        for archivo in archivos:
            with st.spinner(f"Analizando {archivo.name}..."):
                texto_total = ""
                base64_images = []

                if archivo.name.endswith('.pdf'):
                    # Extraer texto e imágenes del PDF
                    doc = fitz.open(stream=archivo.read(), filetype="pdf")
                    for page in doc:
                        texto_total += page.get_text()
                        # Convertir página a imagen para que la IA la "vea"
                        pix = page.get_pixmap()
                        img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        base64_images.append(encode_image(img))
                else:
                    texto_total = docx2txt.process(archivo)

                try:
                    # Instrucciones para la IA con Visión
                    prompt = f"Sos un profesor de Derecho. Evaluá este examen.\nCONSIGNA: {consigna}\nMODELO: {respuesta_modelo}\nTEXTO EXTRAÍDO: {texto_total}\nAnalizá también las imágenes adjuntas (esquemas, árboles genealógicos o cuadros). Calificá de MAL a EXCELENTE y justificá."
                    
                    # Llamada al modelo de visión
                    mensajes = [
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": prompt},
                            ]
                        }
                    ]
                    
                    # Agregamos las imágenes al mensaje si existen
                    for b64 in base64_images[:3]: # Limitamos a las primeras 3 páginas para evitar errores
                        mensajes[0]["content"].append({
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{b64}"}
                        })

                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=mensajes
                    )
                    
                    respuesta = res.choices[0].message.content
                    resultados.append({"Archivo": archivo.name, "Resultado": respuesta})
                
                except Exception as e:
                    resultados.append({"Archivo": archivo.name, "Resultado": f"Error: {e}"})

        # Mostrar tabla final
        st.header("Planilla de Calificaciones")
        st.table(pd.DataFrame(resultados))
