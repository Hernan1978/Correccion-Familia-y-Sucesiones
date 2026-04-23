import streamlit as st
from groq import Groq
import docx2txt
import fitz
import pandas as pd
import json
import time
from fpdf import FPDF # Librería para generar PDFs

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Sistema de Evaluación Detallada", layout="wide")
st.title("⚖️ Corrector de Cátedra con Reporte PDF")

# --- FUNCIÓN PARA GENERAR PDF ---
def generar_pdf(datos_alumno):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, "Reporte de Evaluación Académica", ln=True, align='C')
    pdf.ln(10)
    
    # Datos del Alumno
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(200, 10, f"Alumno: {datos_alumno['alumno']}", ln=True)
    pdf.set_font("Arial", '', 11)
    pdf.cell(200, 10, f"Archivo: {datos_alumno['Archivo']}", ln=True)
    pdf.ln(5)
    
    # Preguntas Detalladas
    for p in ["p1", "p2", "p3"]:
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(200, 10, f"Evaluación {p.upper()}:", ln=True)
        pdf.set_font("Arial", '', 11)
        # Multi_cell para que el texto no se salga de la hoja
        pdf.multi_cell(0, 10, f"Resultado: {datos_alumno[f'{p}_nota']}\nComentario: {datos_alumno[f'{p}_comentario']}")
        pdf.ln(2)

    pdf.ln(5)
    pdf.set_font("Arial", 'B', 14)
    pdf.cell(200, 10, f"NOTA FINAL: {datos_alumno['nota_final']}", ln=True, align='C')
    
    return pdf.output(dest='S').encode('latin-1')

# --- INTERFAZ ---
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    consigna = st.text_area("Preguntas del Examen (P1, P2, P3...):")
    modelo = st.text_area("Respuesta Ideal / Criterios:")

archivos_subidos = st.file_uploader("Subir exámenes de alumnos", type=['pdf', 'docx'], accept_multiple_files=True)

if st.button("🚀 INICIAR CORRECCIÓN DETALLADA"):
    if not api_key or not archivos_subidos:
        st.error("Faltan datos o archivos.")
    else:
        lista_final = []
        barra = st.progress(0)
        
        for idx, arc in enumerate(archivos_subidos):
            try:
                # Leer archivo
                if arc.name.endswith('.pdf'):
                    doc = fitz.open(stream=arc.read(), filetype="pdf")
                    texto_examen = "".join([p.get_text() for p in doc])
                else:
                    texto_examen = docx2txt.process(arc)

                # Prompt para análisis por pregunta
                client = Groq(api_key=api_key)
                prompt = f"""
                Eres un profesor de Derecho. Analiza el examen y devuelve UN SOLO JSON con esta estructura:
                {{
                  "alumno": "nombre",
                  "p1_nota": "BIEN/REGULAR/MAL", "p1_comentario": "...",
                  "p2_nota": "BIEN/REGULAR/MAL", "p2_comentario": "...",
                  "p3_nota": "BIEN/REGULAR/MAL", "p3_comentario": "...",
                  "nota_final": "EXCELENTE/MUY BIEN/BIEN/REGULAR/INSUFICIENTE"
                }}
                Consigna: {consigna}
                Criterios: {modelo}
                Examen: {texto_examen[:6000]}
                """
                
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                res_json = json.loads(response.choices[0].message.content)
                res_json["Archivo"] = arc.name
                lista_final.append(res_json)
                time.sleep(1) # Pausa de seguridad
                
            except Exception as e:
                st.error(f"Error con {arc.name}: {e}")
            
            barra.progress((idx + 1) / len(archivos_subidos))

        # --- MOSTRAR RESULTADOS ---
        if lista_final:
            df = pd.DataFrame(lista_final)
            st.header("📊 Planilla General")
            st.dataframe(df[["alumno", "p1_nota", "p2_nota", "p3_nota", "nota_final"]], use_container_width=True)

            st.divider()
            st.header("📥 Descargar Reportes Individuales (PDF)")
            
            for alumno_data in lista_final:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"**{alumno_data['alumno']}** - Nota Final: {alumno_data['nota_final']}")
                with col2:
                    # Botón para descargar el PDF generado en el momento
                    pdf_bytes = generar_pdf(alumno_data)
                    st.download_button(
                        label="📄 Descargar PDF",
                        data=pdf_bytes,
                        file_name=f"Correccion_{alumno_data['alumno']}.pdf",
                        mime="application/pdf",
                        key=f"btn_{alumno_data['Archivo']}"
                    )
