import streamlit as st
from groq import Groq
import docx2txt
import fitz
import pandas as pd
import json

st.set_page_config(page_title="Corrector Multialumno", layout="wide")
st.title("⚖️ Corrector de Cátedra: Procesamiento por Lote")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    consigna = st.text_area("Consigna:")
    modelo = st.text_area("Criterios:")

# 1. CARGA DE ARCHIVOS (Asegurate de seleccionar VARIOS en la ventana)
archivos_subidos = st.file_uploader("Subir exámenes", type=['pdf', 'docx'], accept_multiple_files=True)

if st.button("🚀 CORREGIR TODOS LOS EXÁMENES"):
    if not api_key or not archivos_subidos:
        st.error("Faltan archivos o la clave API.")
    else:
        # AQUÍ ESTÁ EL SECRETO: Una lista limpia que se llena en cada vuelta del bucle
        resultados_acumulados = []
        
        contenedor_progreso = st.empty()
        barra = st.progress(0)
        
        # 2. EL BUCLE QUE RECORRE CADA ARCHIVO
        for idx, arc in enumerate(archivos_subidos):
            nombre_archivo = arc.name
            contenedor_progreso.info(f"Procesando ({idx+1}/{len(archivos_subidos)}): {nombre_archivo}")
            
            try:
                # Extraer texto según formato
                if nombre_archivo.endswith('.pdf'):
                    doc = fitz.open(stream=arc.read(), filetype="pdf")
                    texto_examen = "".join([p.get_text() for p in doc])
                else:
                    texto_examen = docx2txt.process(arc)

                # Llamada a Groq
                client = Groq(api_key=api_key)
                prompt_docente = f"""
                Eres un profesor corrigiendo TPs. Devuelve SOLO un objeto JSON con:
                "alumno", "nota", "comentario".
                Notas: EXCELENTE, BIEN, REGULAR, INSUFICIENTE.
                
                Examen: {texto_examen[:6000]}
                Consigna: {consigna}
                Criterios: {modelo}
                """
                
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt_docente}],
                    response_format={"type": "json_object"}
                )
                
                # 3. EXTRAER Y GUARDAR
                res_json = json.loads(response.choices[0].message.content)
                res_json["Archivo"] = nombre_archivo # Para saber de qué PDF salió
                
                # Agregamos este alumno a nuestra lista global
                resultados_acumulados.append(res_json)
                
            except Exception as e:
                st.error(f"Error con {nombre_archivo}: {e}")
            
            barra.progress((idx + 1) / len(archivos_subidos))

        # 4. MOSTRAR TODO JUNTO AL FINAL
        if resultados_acumulados:
            st.success(f"¡Procesamiento completo! Se corrigieron {len(resultados_acumulados)} alumnos.")
            
            df_final = pd.DataFrame(resultados_acumulados)
            
            # Semáforo de colores
            def color_nota(val):
                v = str(val).upper()
                if "BIEN" in v or "EXCELENTE" in v: return 'background-color: #d4edda'
                if "REGULAR" in v: return 'background-color: #fff3cd'
                return 'background-color: #f8d7da'

            st.header("📋 Planilla de Notas")
            st.dataframe(df_final.style.map(color_nota, subset=['nota']), use_container_width=True)
            
            # Devoluciones individuales
            st.divider()
            st.subheader("✉️ Devoluciones Detalladas")
            for r in resultados_acumulados:
                with st.expander(f"Alumno: {r.get('alumno', 'Desconocido')} ({r['Archivo']})"):
                    st.write(f"**Nota:** {r['nota']}")
                    st.info(f"**Devolución:** {r['comentario']}")
            
            st.download_button("📥 Descargar Excel", df_final.to_csv(index=False).encode('utf-8'), "notas.csv")
