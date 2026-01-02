import streamlit as st
from pypdf import PdfReader
import pandas as pd
from io import BytesIO
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import json
import os

# --- 1. CONFIGURAÇÃO DO FIREBASE (Nuvem e Local) ---
def inicializar_firebase():
    if not firebase_admin._apps:
        try:
            # Primeiro, tenta carregar dos Secrets (Streamlit Cloud)
            if "firebase" in st.secrets:
                # Transforma o objeto de segredos em um dicionário real
                key_dict = dict(st.secrets["firebase"])
                # Importante: Corrige quebras de linha na chave privada se necessário
                if "private_key" in key_dict:
                    key_dict["private_key"] = key_dict["private_key"].replace("\\n", "\n")
                
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://extracaonadpdf-excel-default-rtdb.firebaseio.com/'
                })
            # Se não achar Secrets, tenta carregar o arquivo local (PC)
            else:
                diretorio_atual = os.path.dirname(os.path.abspath(__file__))
                caminho_chave = os.path.join(diretorio_atual, "chave.json")
                cred = credentials.Certificate(caminho_chave)
                firebase_admin.initialize_app(cred, {
                    'databaseURL': 'https://extracaonadpdf-excel-default-rtdb.firebaseio.com/'
                })
        except Exception as e:
            st.error(f"Erro na conexão com o Banco de Dados: {e}")

inicializar_firebase()

# --- 2. INTERFACE DO APP ---
st.set_page_config(page_title="SOLICITAÇÃO DE PEDIDOS", layout="wide")
st.title("💊 SOLICITAÇÃO DE PEDIDOS - PDF PARA EXCEL")
st.write("Versão Nuvem (Firebase Ativo)")

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
                # Busca o paciente
                paciente = "Não encontrado"
                campo_paci = campos.get("Caixa de texto 4_3")
                if campo_paci and campo_paci.get('/V'):
                    paciente = str(campo_paci.get('/V')).strip()

                # Ler as 12 linhas de itens
                sufixos = ["", "_2", "_3", "_4", "_5", "_6", "_7", "_8", "_9", "_10", "_11", "_12"]
                
                for suf in sufixos:
                    id_qtd = f"Caixa de texto 5{suf}"
                    id_desc = f"Caixa de texto 6{suf}"
                    
                    campo_qtd = campos.get(id_qtd)
                    campo_desc = campos.get(id_desc)
                    
                    if campo_qtd and campo_desc:
                        qtd = str(campo_qtd.get('/V', '')).strip()
                        desc = str(campo_desc.get('/V', '')).strip()
                        
                        if qtd and desc and qtd.upper() != "/OFF" and desc.upper() != "/OFF":
                            item_dados = {
                                "Paciente": paciente,
                                "Quantidade": qtd,
                                "Descrição": desc,
                                "Hora_Importacao": datetime.now().strftime("%H:%M:%S"),
                                "Arquivo": arq.name
                            }
                            lista_final.append(item_dados)
                            # Envio para o Firebase
                            ref_pedidos.push(item_dados)
        
        if lista_final:
            st.success(f"✅ {len(lista_final)} itens processados!")
            df = pd.DataFrame(lista_final)
            st.table(df)
            
            # Gerar Excel para baixar
            data_hoje_arquivo = datetime.now().strftime("%d%m%Y")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Baixar Planilha Excel",
                data=output.getvalue(),
                file_name=f"PedidoNAD_{data_hoje_arquivo}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
