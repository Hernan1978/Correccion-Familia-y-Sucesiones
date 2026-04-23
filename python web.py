import streamlit as st
from groq import Groq
import docx2txt
import fitz
import pandas as pd
import json
import time # Para que la IA no se atore

st.set_page_config(page_title="Corrector Masivo", layout="wide")
st.title("⚖️ Corrector de Cátedra: Modo ráfaga")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    consigna = st.text_area("Consigna:")
    modelo = st.text_area("Criterios:")

# IMPORTANTE: Aquí seleccionás TODOS los archivos
archivos_subidos = st.file_uploader("Subir exámenes", type=['pdf', 'docx'], accept_multiple_files=True)

if st.button("🚀 CORREGIR A TODOS LOS ALUMNOS"):
    if not api_key or not archivos_subidos:
        st.error("Faltan archivos o la clave API.")
    else:
        # LISTA MAESTRA: Aquí se guardan todos sin excepción
        lista_final = []
        
        barra = st.progress(0)
        status = st.empty()
        
        for idx, arc in enumerate(archivos_subidos):
            status.info(f"Procesando alumno {idx+1} de {len(archivos_subidos)}: {arc.name}")
            
            try:
                # 1. Leer archivo
                if arc.name.endswith('.pdf'):
                    # Leemos el PDF de forma que no bloquee la memoria
                    arc.seek(0)
                    doc = fitz.open(stream=arc.read(), filetype="pdf")
                    texto_examen = "".join([p.get_text() for p in doc])
                else:
                    texto_examen = docx2txt.process(arc)

                # 2. Llamar a la IA
                client = Groq(api_key=api_key)
                prompt_docente = f"""
                Eres un profesor. Evalúa este examen y responde SOLO en JSON.
                Formato: {{"alumno": "...", "nota": "...", "comentario": "..."}}
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
                
                # 3. Guardar resultado
                res_json = json.loads(response.choices[0].message.content)
                res_json["Archivo"] = arc.name
                lista_final.append(res_json)
                
                # 4. EL SECRETO: Pausa técnica para que Groq no ignore el siguiente
                time.sleep(2) 
                
            except Exception as e:
                st.error(f"Error en {arc.name}: {e}")
            
            barra.progress((idx + 1) / len(archivos_subidos))

        status.success(f"✅ ¡Listo! Se procesaron {len(lista_final)} alumnos.")

        # 5. MOSTRAR LA TABLA COMPLETA
        if lista_final:
            df = pd.DataFrame(lista_final)
            
            def color_nota(val):
                v = str(val).upper()
                if "BIEN" in v or "EXCELENTE" in v: return 'background-color: #d4edda'
                if "REGULAR" in v: return 'background-color: #fff3cd'
                return 'background-color: #f8d7da'

            st.header("📋 Planilla de Notas")
            st.dataframe(df.style.map(color_nota, subset=['nota']), use_container_width=True)
            
            # Botón para descargar el Excel con todos
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar Planilla Completa", csv, "notas.csv", "text/csv")
