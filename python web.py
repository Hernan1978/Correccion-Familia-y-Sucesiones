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

# --- FUNCIÓN PDF CORREGIDA ---
def generar_pdf_dinamico(datos_alumno):
    # Usamos 'latin-1' o configuramos para que ignore errores de caracteres
    pdf = FPDF()
    pdf.add_page()
    
    # Título
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "Reporte de Evaluacion Academica".encode('latin-1', 'ignore').decode('latin-1'), ln=True, align='C')
    pdf.ln(10)
    
    # Encabezado
    pdf.set_font("Arial", 'B', 12)
    nombre = str(datos_alumno.get('alumno', 'S/N')).encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 10, f"Alumno: {nombre}", ln=True)
    
    pdf.set_font("Arial", '', 10)
    archivo = str(datos_alumno.get('Archivo', 'S/N')).encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 10, f"Archivo original: {archivo}", ln=True)
    pdf.ln(5)
    
    # Desglose
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 10, "Desglose de Calificaciones:".encode('latin-1', 'ignore').decode('latin-1'), ln=True)
    pdf.ln(2)
    
    # Buscamos preguntas dinámicamente
    for clave in sorted(datos_alumno.keys()):
        if clave.startswith('P') and '_nota' in clave:
            num_pregunta = clave.split('_')[0]
            nota = str(datos_alumno[clave]).encode('latin-1', 'ignore').decode('latin-1')
            comentario = str(datos_alumno.get(f"{num_pregunta}_comentario", "Sin comentario")).encode('latin-1', 'ignore').decode('latin-1')
            
            pdf.set_font("Arial", 'B', 11)
            pdf.cell(0, 8, f"Pregunta {num_pregunta[1:]}: {nota}", ln=True)
            pdf.set_font("Arial", 'I', 10)
            pdf.multi_cell(0, 7, f"Observaciones: {comentario}")
            pdf.ln(3)

    pdf.ln(10)
    pdf.set_font("Arial", 'B', 14)
    nota_final = str(datos_alumno.get('nota_final', 'S/N')).encode('latin-1', 'ignore').decode('latin-1')
    pdf.cell(0, 15, f"NOTA FINAL: {nota_final}", ln=True, align='C')
    
    return pdf.output(dest='S')

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
                prompt = f"""
                Evalúa el examen. Crea un objeto JSON con el nombre del alumno, nota final y un desglose 
                para CADA pregunta detectada (P1, P2, P3, etc.) con su nota (BIEN/REGULAR/MAL) y comentario.
                
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
                time.sleep(1)
                
            except Exception as e:
                st.error(f"Error en {arc.name}: {e}")
            
            barra.progress((idx + 1) / len(archivos))

        # --- RESULTADOS ---
        if resultados_lista:
            st.header("📋 Resultados Detallados")
            df = pd.DataFrame(resultados_lista)
            cols_principales = [c for c in df.columns if 'comentario' not in c and c != 'Archivo']
            st.dataframe(df[cols_principales], use_container_width=True)

            st.divider()
            for alu in resultados_lista:
                nombre_display = alu.get('alumno', 'S/N')
                st.write(f"📄 **Reporte:** {nombre_display} ({alu['Archivo']})")
                
                try:
                    pdf_bytes = generar_pdf_dinamico(alu)
                    st.download_button(
                        label=f"Descargar PDF de {nombre_display}",
                        data=pdf_bytes,
                        file_name=f"Correccion_{nombre_display}.pdf",
                        mime="application/pdf",
                        key=f"pdf_{alu['Archivo']}_{idx}"
                    )
                except Exception as e:
                    st.error(f"No se pudo generar este PDF específico por un error de caracteres.")
