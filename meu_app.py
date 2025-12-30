import streamlit as st
from pypdf import PdfReader
import pandas as pd
from io import BytesIO
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import os

# --- LOCALIZAR A CHAVE NA PASTA ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_chave = os.path.join(diretorio_atual, "chave.json")

# --- CONFIGURAÇÃO DO NOVO FIREBASE ---
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(caminho_chave)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://extracaonadpdf-excel-default-rtdb.firebaseio.com/'
        })
    except Exception as e:
        st.error(f"Erro ao carregar a chave: {e}")

# --- INTERFACE DO APP ---
st.set_page_config(page_title="SOLICITAÇÃO DE PEDIDOS", layout="wide")
st.title("💊 SOLICITAÇÃO DE PEDIDOS - TRANSFORMA PDF PARA EXCEL")

upload = st.file_uploader("Arraste os PDFs aqui", type="pdf", accept_multiple_files=True)

if upload:
    lista_final = []
    try:
        # Organizando por data no Firebase para facilitar sua visualização
        data_hoje_db = datetime.now().strftime("%Y-%m-%d")
        ref_pedidos = db.reference(f'pedidos/{data_hoje_db}')

        for arq in upload:
            reader = PdfReader(arq)
            campos = reader.get_fields()
            
            if campos:
                # 1. BUSCA O PACIENTE NA CAIXA 4_3
                paciente = "Não encontrado"
                campo_paci = campos.get("Caixa de texto 4_3")
                if campo_paci and campo_paci.get('/V'):
                    paciente = str(campo_paci.get('/V')).strip()

                # 2. LER AS 12 LINHAS DE ITENS
                sufixos = ["", "_2", "_3", "_4", "_5", "_6", "_7", "_8", "_9", "_10", "_11", "_12"]
                
                for suf in sufixos:
                    id_qtd = f"Caixa de texto 5{suf}"
                    id_desc = f"Caixa de texto 6{suf}"
                    
                    campo_qtd = campos.get(id_qtd)
                    campo_desc = campos.get(id_desc)
                    
                    if campo_qtd and campo_desc:
                        qtd = str(campo_qtd.get('/V', '')).strip()
                        desc = str(campo_desc.get('/V', '')).strip()
                        
                        if qtd and qtd.upper() != "/OFF" and desc and desc.upper() != "/OFF":
                            item_dados = {
                                "Paciente": paciente,
                                "Quantidade": qtd,
                                "Descrição": desc,
                                "Hora_Importacao": datetime.now().strftime("%H:%M:%S"),
                                "Arquivo": arq.name
                            }
                            lista_final.append(item_dados)
                            
                            # ENVIO PARA O FIREBASE
                            ref_pedidos.push(item_dados)
        
        if lista_final:
            st.success(f"✅ {len(lista_final)} itens enviados para o Firebase!")
            df = pd.DataFrame(lista_final)
            st.table(df)
            
            # GERAR NOME DO ARQUIVO: PedidoNAD_ddmmaaaa
            data_hoje_arquivo = datetime.now().strftime("%d%m%Y")
            nome_excel = f"PedidoNAD_{data_hoje_arquivo}.xlsx"
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(f"📥 Baixar {nome_excel}", output.getvalue(), nome_excel)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")