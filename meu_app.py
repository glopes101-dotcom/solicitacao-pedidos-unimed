import streamlit as st
from pypdf import PdfReader
import pandas as pd
from io import BytesIO
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import json

# --- CONFIGURAÇÃO DO FIREBASE ---
def inicializar_firebase():
    if not firebase_admin._apps:
        try:
            # Tenta pegar dos Secrets (Nuvem)
            if "firebase" in st.secrets:
                info_json = st.secrets["firebase"]["info"]
                key_dict = json.loads(info_json)
                cred = credentials.Certificate(key_dict)
            else:
                # Se rodar local, procura o arquivo na mesma pasta
                cred = credentials.Certificate("chave.json")
                
            firebase_admin.initialize_app(cred, {
                'databaseURL': 'https://extracaonadpdf-excel-default-rtdb.firebaseio.com/'
            })
        except Exception as e:
            st.error(f"Erro na conexão com o Banco de Dados: {e}")

inicializar_firebase()

st.set_page_config(page_title="Extração NAD", layout="wide")
st.title("💊 Sistema de Extração NAD")

upload = st.file_uploader("Arraste os PDFs aqui", type="pdf", accept_multiple_files=True)

if upload:
    lista_final = []
    try:
        data_hoje_db = datetime.now().strftime("%Y-%m-%d")
        ref_pedidos = db.reference(f'pedidos/{data_hoje_db}')
        for arq in upload:
            reader = PdfReader(arq)
            campos = reader.get_fields()
            if campos:
                paciente = "Não encontrado"
                campo_paci = campos.get("Caixa de texto 4_3")
                if campo_paci and campo_paci.get('/V'):
                    paciente = str(campo_paci.get('/V')).strip()

                sufixos = ["", "_2", "_3", "_4", "_5", "_6", "_7", "_8", "_9", "_10", "_11", "_12"]
                for suf in sufixos:
                    qtd = campos.get(f"Caixa de texto 5{suf}")
                    desc = campos.get(f"Caixa de texto 6{suf}")
                    if qtd and desc:
                        v_qtd = str(qtd.get('/V', '')).strip()
                        v_desc = str(desc.get('/V', '')).strip()
                        if v_qtd and v_desc and v_qtd.upper() != "/OFF":
                            item = {"Paciente": paciente, "Qtd": v_qtd, "Medicamento": v_desc}
                            lista_final.append(item)
                            ref_pedidos.push(item)
        if lista_final:
            df = pd.DataFrame(lista_final)
            st.table(df)
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("Baixar Excel", output.getvalue(), "pedido.xlsx")
    except Exception as e:
        st.error(f"Erro: {e}")




