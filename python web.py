import streamlit as st
from groq import Groq
import docx2txt
import fitz
import pandas as pd
import json
import time
from fpdf import FPDF

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="Corrector Cátedra Pro", layout="wide")
st.title("⚖️ Sistema de Evaluación: Familia y Sucesiones")

# --- FUNCIÓN PARA EL PDF ---
def generar_pdf_bytes(datos_alumno):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", 'B', 16)
    pdf.cell(0, 10, "Informe de Calificación Detallado", ln=True, align='C')
    pdf.ln(10)
    
    # Info Alumno
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, f"Alumno: {datos_alumno.get('alumno', 'S/N')}", ln=True)
    pdf.set_font("Helvetica", '', 10)
    pdf.cell(0, 10, f"Archivo: {datos_alumno.get('Archivo', 'S/N')}", ln=True)
    pdf.ln(5)
    
    # Desglose Dinámico
    pdf.set_font("Helvetica", 'B', 12)
    pdf.cell(0, 10, "Evaluacion por Puntos:", ln=True)
    
    claves = sorted([k for k in datos_alumno.keys() if k.startswith('P') and '_nota' in k])
    for clave in claves:
        num = clave.split('_')[0]
        nota = datos_alumno[clave]
        comentario = datos_alumno.get(f"{num}_comentario", "Sin observaciones adicionales.")
        
        pdf.set_font("Helvetica", 'B', 11)
        pdf.cell(0, 8, f"Pregunta {num[1:]}: {nota}", ln=True)
        pdf.set_font("Helvetica", '', 10)
        pdf.multi_cell(0, 7, f"Comentario: {comentario}")
        pdf.ln(2)

    pdf.ln(10)
    pdf.set_font("Helvetica", 'B', 14)
    pdf.cell(0, 15, f"NOTA FINAL: {datos_alumno.get('nota_final', 'S/N')}", ln=True, align='C', border=1)
    
    return pdf.output()

# --- ESTILO DE SEMÁFORO PARA LA TABLA ---
def aplicar_color_semaforo(val):
    v = str(val).upper()
    if any(x in v for x in ["BIEN", "EXCELENTE", "MUY BIEN"]): color = '#d4edda' # Verde
    elif "REGULAR" in v: color = '#fff3cd' # Amarillo
    elif any(x in v for x in ["MAL", "INSUFICIENTE"]): color = '#f8d7da' # Rojo
    else: color = 'white'
    return f'background-color: {color}'

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    consigna = st.text_area("Consigna del Examen:")
    modelo = st.text_area("Criterios de Corrección:")

archivos = st.file_uploader("Subir exámenes", accept_multiple_files=True)

if st.button("🚀 PROCESAR Y CORREGIR"):
    if not api_key or not archivos:
        st.error("Faltan datos.")
    else:
        resultados_totales = []
        barra = st.progress(0)
        
        for idx, arc in enumerate(archivos):
            try:
                # Leer Archivo
                if arc.name.endswith('.pdf'):
                    doc = fitz.open(stream=arc.read(), filetype="pdf")
                    texto = "".join([p.get_text() for p in doc])
                else:
                    texto = docx2txt.process(arc)

                # IA - Análisis Detallado
                client = Groq(api_key=api_key)
                prompt = f"""
                Evalúa el examen. Crea un JSON con:
                "alumno", "nota_final", y para cada pregunta (P1, P2, P3...) crea:
                "P#_nota": "BIEN/REGULAR/MAL" y "P#_comentario": "explicación".
                
                Consigna: {consigna}
                Modelo: {modelo}
                Examen: {texto[:7000]}
                """
                
                resp = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                datos = json.loads(resp.choices[0].message.content)
                datos["Archivo"] = arc.name
                resultados_totales.append(datos)
                time.sleep(1)
                
            except Exception as e:
                st.error(f"Error en {arc.name}: {e}")
            
            barra.progress((idx + 1) / len(archivos))

        # --- MOSTRAR RESULTADOS (LA CONFIGURACIÓN QUE TE GUSTÓ) ---
        if resultados_totales:
            st.header("📊 Cuadro de Calificaciones")
            df = pd.DataFrame(resultados_totales)
            
            # Filtramos solo las columnas de notas para el semáforo
            cols_notas = [c for c in df.columns if '_nota' in c or c == 'nota_final']
            
            # Mostramos la tabla con colores
            st.dataframe(
                df[["alumno"] + cols_notas].style.applymap(aplicar_color_semaforo, subset=cols_notas),
                use_container_width=True
            )

            st.divider()
            st.header("📥 Descarga de Devoluciones Detalladas")
            
            for res in resultados_totales:
                c1, c2 = st.columns([3, 1])
                nombre_alu = res.get('alumno', 'S/N')
                with c1:
                    st.write(f"📄 **{nombre_alu}** (Nota: {res.get('nota_final')})")
                with c2:
                    pdf_bytes = generar_pdf_bytes(res)
                    st.download_button(
                        label="Descargar PDF",
                        data=bytes(pdf_bytes),
                        file_name=f"Devolucion_{nombre_alu}.pdf",
                        mime="application/pdf",
                        key=f"dl_{res['Archivo']}"
                    )
