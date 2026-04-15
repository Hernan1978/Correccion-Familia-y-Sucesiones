import streamlit as st
from groq import Groq
import docx2txt
import fitz  # PyMuPDF
import pandas as pd

# 1. CONFIGURACIÓN E INTERFAZ
st.set_page_config(page_title="Cátedra IA Pro", layout="wide")
st.title("⚖️ Sistema de Corrección con Semáforo")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    st.divider()
    consigna = st.text_area("Preguntas oficiales:", height=150)
    respuesta_modelo = st.text_area("Criterios de Corrección:", height=150)

# 2. CARGA DE ARCHIVOS
archivos = st.file_uploader("Suba los exámenes", type=['pdf', 'docx'], accept_multiple_files=True)

# 3. PROCESAMIENTO
if st.button("🚀 INICIAR EVALUACIÓN"):
    if not api_key or not archivos or not consigna:
        st.error("Faltan datos (Clave, Consignas o Archivos).")
    else:
        resultados_finales = []
        barra_progreso = st.progress(0)
        
        for index, arc in enumerate(archivos):
            with st.spinner(f"Analizando: {arc.name}..."):
                try:
                    if arc.name.endswith('.pdf'):
                        doc = fitz.open(stream=arc.read(), filetype="pdf")
                        texto = "".join([p.get_text() for p in doc])
                    else:
                        texto = docx2txt.process(arc)

                    texto_final = texto[:7000]
                    client = Groq(api_key=api_key)
                    
                    # PROMPT ESTRUCTURADO PARA TABULACIÓN
                    prompt_sistema = f"""
                    Actúa como profesor de Derecho. Evalúa el examen.
                    CONSIGNA: {consigna}
                    MODELO: {respuesta_modelo}
                    
                    Responde siguiendo estrictamente este esquema:
                    NOMBRE: [Nombre del alumno]
                    P1: [BIEN/REGULAR/MAL]
                    P2: [BIEN/REGULAR/MAL]
                    P3: [BIEN/REGULAR/MAL]
                    FINAL: [EXCELENTE, MUY BIEN, BIEN, REGULAR o INSUFICIENTE]
                    JUSTIFICACION: [Resumen breve de la corrección]
                    """

                    completion = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": f"{prompt_sistema}\n\nEXAMEN:\n{texto_final}"}],
                        temperature=0.2
                    )

                    analisis = completion.choices[0].message.content
                    resultados_finales.append({"Archivo": arc.name, "Detalle": analisis})
                
                except Exception as e:
                    resultados_finales.append({"Archivo": arc.name, "Detalle": f"Error: {str(e)}"})
                
                barra_progreso.progress((index + 1) / len(archivos))

        # 4. TABLA CON SEMÁFORO TEXTUAL
        st.divider()
        st.header("📊 Cuadro de Calificaciones")

        def aplicar_semaforo(val):
            v = str(val).upper()
            if any(x in v for x in ["BIEN", "EXCELENTE"]): color = '#d4edda' # Verde
            elif "REGULAR" in v: color = '#fff3cd' # Amarillo
            elif any(x in v for x in ["MAL", "INSUFICIENTE"]): color = '#f8d7da' # Rojo
            else: color = 'white'
            return f'background-color: {color}'

        # Procesar los datos para la tabla
        resumen_data = []
        for r in resultados_finales:
            d = r['Detalle']
            # Extracción simple de cada campo
            try:
                nombre = d.split("NOMBRE:")[1].split("\n")[0].strip()
                p1 = d.split("P1:")[1].split("\n")[0].strip()
                p2 = d.split("P2:")[1].split("\n")[0].strip()
                p3 = d.split("P3:")[1].split("\n")[0].strip()
                final = d.split("FINAL:")[1].split("\n")[0].strip()
                resumen_data.append({
                    "Alumno": nombre, 
                    "P1": p1, "P2": p2, "P3": p3, 
                    "Nota Final": final,
                    "Archivo": r['Archivo']
                })
            except:
                resumen_data.append({"Alumno": "Error formato", "Nota Final": "REVISAR", "Archivo": r['Archivo']})

        df = pd.DataFrame(resumen_data)

        if not df.empty:
            # Mostramos la tabla con el semáforo aplicado a todas las columnas de notas
            st.dataframe(df.style.applymap(aplicar_semaforo, subset=['P1', 'P2', 'P3', 'Nota Final']), use_container_width=True)
            
            # Botón de descarga
            st.download_button("📥 Descargar Planilla", df.to_csv(index=False).encode('utf-8'), "notas.csv")

       # 5. DETALLE INDIVIDUAL
        with st.expander("🔍 Ver justificaciones detalladas"):
            for res in resultados_finales:
                st.subheader(f"Examen: {res['Archivo']}")
                st.text(res['Detalle'])
                st.divider()
