import streamlit as st
from groq import Groq
import docx2txt
import fitz
import pandas as pd
import json

st.set_page_config(page_title="Gestión de TP - Cátedra", layout="wide")
st.title("⚖️ Panel de Corrección de Trabajos Prácticos")

with st.sidebar:
    st.header("⚙️ Configuración")
    api_key = st.text_input("Groq API Key", type="password")
    st.divider()
    consigna = st.text_area("Consigna del TP:", placeholder="Ej: Analice el caso de sucesiones...")
    modelo = st.text_area("Criterios de Aprobación:", placeholder="Ej: Uso de terminología técnica, cita de artículos...")

archivos = st.file_uploader("Subir todos los TPs entregados (PDF o DOCX)", type=['pdf', 'docx'], accept_multiple_files=True)

if st.button("🚀 PROCESAR TODAS LAS ENTREGAS"):
    if not api_key or not archivos or not consigna:
        st.error("Por favor, cargue la API Key, la consigna y los archivos.")
    else:
        lista_de_resultados = []
        progreso = st.progress(0)
        
        for i, arc in enumerate(archivos):
            with st.spinner(f"Corrigiendo alumno {i+1} de {len(archivos)}..."):
                try:
                    # 1. Extracción de texto
                    if arc.name.endswith('.pdf'):
                        doc = fitz.open(stream=arc.read(), filetype="pdf")
                        texto = "".join([p.get_text() for p in doc])
                    else:
                        texto = docx2txt.process(arc)

                    # 2. Llamada a la IA
                    client = Groq(api_key=api_key)
                    prompt = f"""
                    Actúa como profesor de Derecho. Evalúa este TP.
                    Responde ÚNICAMENTE en formato JSON con estas claves exactas:
                    "alumno": "nombre completo del alumno",
                    "nota_final": "EXCELENTE, MUY BIEN, BIEN, REGULAR o INSUFICIENTE",
                    "devolucion_personalizada": "un comentario constructivo para el alumno explicando por qué sacó esa nota"

                    Consigna: {consigna}
                    Criterios: {modelo}
                    Examen: {texto[:7000]}
                    """
                    
                    response = client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": prompt}],
                        response_format={"type": "json_object"}
                    )
                    
                    # 3. Guardar en la lista
                    resultado = json.loads(response.choices[0].message.content)
                    resultado["Archivo"] = arc.name
                    lista_de_resultados.append(resultado)
                
                except Exception as e:
                    st.warning(f"No se pudo procesar {arc.name}: {e}")
                
            progreso.progress((i + 1) / len(archivos))

        # 4. TABLA DE GESTIÓN FINAL
        if lista_de_resultados:
            df = pd.DataFrame(lista_de_resultados)
            
            # Estilo de colores para la tabla
            def color_semaforo(val):
                v = str(val).upper()
                if any(x in v for x in ["BIEN", "EXCELENTE"]): return 'background-color: #d4edda; color: #155724'
                if "REGULAR" in v: return 'background-color: #fff3cd; color: #856404'
                return 'background-color: #f8d7da; color: #721c24'

            st.header("📋 Planilla de Notas Generada")
            st.dataframe(df.style.map(color_semaforo, subset=["nota_final"]), use_container_width=True)

            # 5. SECCIÓN DE DEVOLUCIONES INDIVIDUALES
            st.divider()
            st.header("✉️ Devoluciones para Alumnos")
            st.info("Podés copiar estas devoluciones para enviarlas por mail o campus virtual.")
            
            for r in lista_de_resultados:
                with st.expander(f"👤 Alumno: {r['alumno']} - Nota: {r['nota_final']}"):
                    st.write(f"**Archivo:** {r['Archivo']}")
                    st.success(f"**Devolución:** {r['devolucion_personalizada']}")
                    st.button("Copiar Devolución", key=r['Archivo'], on_click=lambda text=r['devolucion_personalizada']: st.write(f"Copiado: {text}"), help="Seleccioná el texto para copiar")

            # 6. DESCARGA DE EXCEL
            st.download_button("📥 Descargar Planilla para Actas (CSV)", df.to_csv(index=False).encode('utf-8'), "notas_catedra.csv")
