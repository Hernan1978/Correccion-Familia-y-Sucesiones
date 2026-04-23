import streamlit as st
from groq import Groq
import docx2txt
import fitz
import pandas as pd
import json
import time
from fpdf import FPDF

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Corrector Pro Dinámico", layout="wide")
st.title("⚖️ Sistema de Evaluación Integral")

def generar_pdf_dinamico(datos_alumno):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Reporte de Evaluación Académica", ln=True, align='C')
    pdf.ln(10)
    
    # Encabezado
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, f"Alumno: {datos_alumno.get('alumno', 'N/A')}", ln=True)
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Archivo original: {datos_alumno.get('Archivo', 'N/A')}", ln=True)
    pdf.ln(5)
    
    # Recorrer preguntas dinámicamente
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Desglose de Calificaciones:", ln=True)
    pdf.ln(2)
    
    # Buscamos en el diccionario todo lo que empiece con "P" seguido de número
    for clave, valor in datos_alumno.items():
        if clave.startswith('P') and '_nota' in clave:
            num_pregunta = clave.split('_')[0] # Extrae "P1", "P2", etc.
            comentario = datos_alumno.get(f"{num_pregunta}_comentario", "Sin comentario.")
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, f"Pregunta {num_pregunta[1:]}: {valor}", ln=True)
            pdf.set_font("Arial", 'I', 10)
            pdf.multi_cell(0, 7, f"Observaciones: {comentario}")
            pdf.ln(3)

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 15, f"NOTA FINAL: {datos_alumno.get('nota_final', 'S/N')}", ln=True, align='C', fill=True)
    
    return pdf.output()

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    consigna = st.text_area("Cargue aquí todas las preguntas:")
    modelo = st.text_area("Criterios/Respuestas esperadas:")

archivos = st.file_uploader("Exámenes (PDF/DOCX)", accept_multiple_files=True)

if st.button("🚀 INICIAR PROCESAMIENTO"):
    if not api_key or not archivos:
        st.error("Faltan datos.")
    else:
        resultados_lista = []
        barra = st.progress(0)
        
        for idx, arc in enumerate(archivos):
            try:
                # Lectura de archivo
                if arc.name.endswith('.pdf'):
                    doc = fitz.open(stream=arc.read(), filetype="pdf")
                    texto = "".join([p.get_text() for p in doc])
                else:
                    texto = docx2txt.process(arc)

                client = Groq(api_key=api_key)
                # Prompt Dinámico: Le pedimos que cree llaves P1, P2... Pn
                prompt = f"""
                Evalúa el examen. Crea un objeto JSON con el nombre del alumno, nota final y un desglose 
                para CADA pregunta detectada (P1, P2, P3, etc.) con su nota (BIEN/REGULAR/MAL) y comentario.
                
                IMPORTANTE: Usa el formato: 
                "P1_nota": "...", "P1_comentario": "...", 
                "P2_nota": "...", "P2_comentario": "..." (así sucesivamente).
                
                Consigna: {consigna}
                Criterios: {modelo}
                Examen: {texto[:7000]}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                res_dict = json.loads(resp.choices[0].message.content)
                res_dict["Archivo"] = arc.name
                resultados_lista.append(res_dict)
                time.sleep(1.5)
                
            except Exception as e:
                st.error(f"Error en {arc.name}: {e}")
            
            barra.progress((idx + 1) / len(archivos))

        # --- RESULTADOS ---
        if resultados_lista:
            st.header("📋 Resultados Detallados")
            df = pd.DataFrame(resultados_lista)
            # Mostrar solo columnas principales en la tabla general
            cols_principales = [c for c in df.columns if 'comentario' not in c and c != 'Archivo']
            st.dataframe(df[cols_principales], use_container_width=True)

            st.divider()
            for alu in resultados_lista:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"📄 **Reporte:** {alu.get('alumno', 'S/N')} ({alu['Archivo']})")
                with col2:
                    try:
                        pdf_data = generar_pdf_dinamico(alu)
                        st.download_button(
                            "Descargar PDF",
                            data=pdf_data,
                            file_name=f"Correccion_{alu.get('alumno','alu')}.pdf",
                            mime="application/pdf",
                            key=f"pdf_{alu['Archivo']}"
                        )
                    except Exception as e:
                        st.write("Error PDF")
