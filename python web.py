import streamlit as st
from groq import Groq
import docx2txt
import PyPDF2

st.set_page_config(page_title="Cátedra Familia y Sucesiones", page_icon="⚖️")

# --- CONTRASEÑA DOCENTE ---
PWD = "catedra_derecho" 

if "consigna" not in st.session_state: st.session_state.consigna = ""
if "modelo" not in st.session_state: st.session_state.modelo = ""

with st.sidebar:
    st.title("Panel de Control")
    api_key = st.text_input("Groq API Key", type="password")
    st.divider()
    ingreso_pwd = st.text_input("Clave Docente", type="password")

# --- MODO DOCENTE (Configuración) ---
if ingreso_pwd == PWD:
    st.header("👨‍🏫 Configuración del TP")
    st.session_state.consigna = st.text_area("Pregunta/Caso:", value=st.session_state.consigna)
    st.session_state.modelo = st.text_area("Respuesta Correcta (Modelo):", value=st.session_state.modelo)
    st.success("Configuración activa. Los alumnos verán esto.")
    st.divider()

# --- MODO ALUMNO (Interfaz Principal) ---
st.title("⚖️ Entrega de TP: Familia y Sucesiones")
mail = st.text_input("Mail Institucional")

if not st.session_state.consigna:
    st.info("Esperando que el docente habilite el TP...")
else:
    st.warning(f"**CONSIGNA:** {st.session_state.consigna}")
    archivo = st.file_uploader("Subí tu TP (PDF o Word)", type=['pdf', 'docx'])

    if st.button("Enviar para Corrección Automática"):
        if not mail or not archivo:
            st.error("Completá tu mail y subí el archivo.")
        else:
            with st.spinner("Corrigiendo..."):
                # Leer texto del archivo
                texto_alumno = ""
                if archivo.type == "application/pdf":
                    reader = PyPDF2.PdfReader(archivo)
                    for page in reader.pages: texto_alumno += page.extract_text()
                else:
                    texto_alumno = docx2txt.process(archivo)

                # Llamar a la IA
                try:
                    client = Groq(api_key=api_key)
                    prompt = f"Sos profesor de Derecho. Corregí este TP basándote en la RESPUESTA MODELO.\n\nMODELO: {st.session_state.modelo}\n\nALUMNO: {texto_alumno}\n\nEntrega Nota del 1 al 10 y breve fundamento jurídico."
                    
                    res = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}]
                    )
                    st.success(f"Evaluación para {mail}:")
                    st.markdown(res.choices[0].message.content)
                except Exception as e:
                    st.error(f"Error: {e}")
