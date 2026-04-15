import streamlit as st
from groq import Groq
import docx2txt
import fitz
import pandas as pd
import json

st.set_page_config(page_title="Corrector Pro", layout="wide")
st.title("⚖️ Sistema de Evaluación de Cátedra")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    consigna = st.text_area("Preguntas:")
    modelo = st.text_area("Criterios:")

archivos = st.file_uploader("Subir exámenes", type=['pdf', 'docx'], accept_multiple_files=True)

if st.button("🚀 CORREGIR AHORA"):
    if not api_key or not archivos:
        st.error("Faltan datos.")
    else:
        resultados = []
        for arc in archivos:
            with st.spinner(f"Corrigiendo {arc.name}..."):
                # Extracción de texto
                if arc.name.endswith('.pdf'):
                    doc = fitz.open(stream=arc.read(), filetype="pdf")
                    texto = "".join([p.get_text() for p in doc])
                else:
                    texto = docx2txt.process(arc)

                client = Groq(api_key=api_key)
                # Forzamos a la IA a responder en formato de base de datos (JSON)
                prompt = f"""
                Evalúa el examen según la consigna y el modelo.
                Responde ÚNICAMENTE en formato JSON con estas claves:
                "alumno", "p1_nota", "p2_nota", "p3_nota", "nota_final", "justificacion".
                Usa para las notas: BIEN, REGULAR o MAL. 
                Para nota_final usa: EXCELENTE, MUY BIEN, BIEN, REGULAR, INSUFICIENTE.
                
                Consigna: {consigna}
                Modelo: {modelo}
                Examen: {texto[:7000]}
                """
                
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"}
                )
                
                # Convertimos la respuesta de la IA en datos para la tabla
                datos = json.loads(response.choices[0].message.content)
                datos["Archivo"] = arc.name
                resultados.append(datos)

        # MOSTRAR TABLA
        df = pd.DataFrame(resultados)
        
        def s(val):
            v = str(val).upper()
            if "BIEN" in v or "EXCELENTE" in v: c = '#d4edda'
            elif "REGULAR" in v: c = '#fff3cd'
            else: c = '#f8d7da'
            return f'background-color: {c}'

        st.header("📊 Notas Finales")
        st.dataframe(df.style.map(s, subset=["p1_nota", "p2_nota", "p3_nota", "nota_final"]), use_container_width=True)
        st.download_button("📥 Excel", df.to_csv(index=False).encode('utf-8'), "notas.csv")
