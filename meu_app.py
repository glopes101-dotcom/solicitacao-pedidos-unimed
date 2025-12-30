import streamlit as st
from pypdf import PdfReader
import pandas as pd
from io import BytesIO
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import os

# --- FUNÇÃO DE SEGURANÇA (LOGIN) ---
def check_password():
    """Retorna True se o usuário inseriu a senha correta."""
    def password_entered():
        # --- ALTERE SUA SENHA AQUI ---
        if st.session_state["password"] == "Unimed@2025":
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Limpa a senha da memória
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # Primeira vez: pede a senha
        st.info("Acesso Restrito: Identifique-se para continuar.")
        st.text_input("Digite a senha de acesso", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Senha errada
        st.text_input("Senha incorreta. Tente novamente", type="password", on_change=password_entered, key="password")
        st.error("🔒 Acesso Negado")
        return False
    else:
        # Senha correta
        return True

# Bloqueia o app se não estiver logado
if not check_password():
    st.stop()

# --- ABAIXO: CÓDIGO DO SISTEMA (SÓ RODA SE A SENHA ESTIVER CORRETA) ---

# Localizar a chave na pasta (Certifique-se que o arquivo chave.json está no GitHub)
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_chave = os.path.join(diretorio_atual, "chave.json")

# Configuração do Firebase
if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(caminho_chave)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://extracaonadpdf-excel-default-rtdb.firebaseio.com/'
        })
    except Exception as e:
        st.error(f"Erro ao carregar a chave: {e}")

st.set_page_config(page_title="SOLICITAÇÃO DE PEDIDOS", layout="wide")
st.title("💊 SOLICITAÇÃO DE PEDIDOS - UNIMED")
st.sidebar.success(f"Logado em: {datetime.now().strftime('%d/%m/%Y')}")

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
                            ref_pedidos.push(item_dados)
        
        if lista_final:
            st.success(f"✅ {len(lista_final)} itens processados com sucesso!")
            df = pd.DataFrame(lista_final)
            st.table(df)
            
            data_hoje_arquivo = datetime.now().strftime("%d%m%Y")
            nome_excel = f"PedidoNAD_{data_hoje_arquivo}.xlsx"
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(f"📥 Baixar Planilha {nome_excel}", output.getvalue(), nome_excel)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
