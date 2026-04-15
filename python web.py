import streamlit as st
from groq import Groq
import docx2txt
import fitz  # PyMuPDF
import pandas as pd

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Asistente de Cátedra", layout="wide")
st.title("⚖️ Sistema de Corrección de Cátedra")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    st.divider()
    consigna = st.text_area("Preguntas oficiales:", height=150)
    respuesta_modelo = st.text_area("Respuesta Ideal:", height=150)

# 2. CARGA
archivos = st.file_uploader("Suba los exámenes", type=['pdf', 'docx'], accept_multiple_files=True)

# 3. PROCESAMIENTO
if st.button("🚀 INICIAR CORRECCIÓN"):
    if not api_key or not archivos or not consigna:
        st.error("Falta completar datos.")
    else:
        lista_resultados = []
        barra_progreso = st.progress(0)
        
        for index, arc in enumerate(archivos):
            with st.spinner(f"Analizando: {arc.name}..."):
                try:
                    # Extraer texto
                    if arc.name.endswith('.pdf'):
                        doc = fitz.open(stream=arc.read(), filetype="pdf")
                        texto = "".join([pagina.get_text() for pagina in doc])
                    else:
                        texto = docx2txt.process(arc)

                    # Recorte de seguridad para evitar el error de tokens (413)
                    texto_final = texto[:7000] 

                    client = Groq(api_key=api_key)
                    
                    # Llamada a la IA (Modelo estable 2026)
                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{
                            "role": "user", 
                            "content": f"Evalúa como docente. Consigna: {consigna}. Modelo: {respuesta_modelo}. Examen: {texto_final}"
                        }],
                        temperature=0.2,
                        max_tokens=1000
                    )

                    analisis = completion.choices[0].message.content
                    
                    # AQUÍ ESTÁ LA CLAVE: Guardamos con el nombre 'NombreArchivo'
                    lista_resultados.append({
                        "NombreArchivo": arc.name, 
                        "Evaluación": analisis
                    })
                
                except Exception as e:
                    lista_resultados.append({
                        "NombreArchivo": arc.name, 
                        "Evaluación": f"Error: {str(e)}"
                    })
                
                barra_progreso.progress((index + 1) / len(archivos))

        # 4. RESULTADOS (Usando exactamente 'NombreArchivo')
        st.divider()
        for res in lista_resultados:
            with st.expander(f"📝 Examen: {res['NombreArchivo']}"):
                st.markdown(res['Evaluación'])
        
        if lista_resultados:
            df = pd.DataFrame(lista_resultados)
            st.download_button("📥 Descargar Planilla", df.to_csv(index=False).encode('utf-8'), "notas.csv")
