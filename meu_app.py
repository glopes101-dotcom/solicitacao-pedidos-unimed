import streamlit as st
from pypdf import PdfReader
import pandas as pd
from io import BytesIO
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import os
import streamlit_authenticator as stauth

# --- CONFIGURAÇÃO DE USUÁRIOS ---
# Importante: Senhas em texto simples precisam ser tratadas pela biblioteca
credentials_data = {
    "usernames": {
        "ludmilla.vilela": {"name": "Ludmilla Vilela", "password": "Unimed@540"},
        "gustavo.lopes": {"name": "Gustavo Lopes Rodrigues", "password": "Unimed@540"}
    }
}

# Criando o objeto de autenticação
authenticator = stauth.Authenticate(
    credentials_data,
    "unimed_cookie",
    "unimed_key",
    cookie_expiry_days=30
)

# --- NOVA FORMA DE LOGIN (SEM ARGUMENTOS QUE CAUSAM ERRO) ---
# Aqui usamos apenas o parâmetro que a biblioteca exige agora
authenticator.login(location='main')

# Verificação de status via Session State (Memória do navegador)
if st.session_state.get("authentication_status") == False:
    st.error("Usuário ou senha incorretos")
    st.stop()
elif st.session_state.get("authentication_status") == None:
    st.warning("Por favor, insira seu usuário e senha institucional para acessar o extrator.")
    st.stop()

# --- LOGIN BEM SUCEDIDO ---
name = st.session_state["name"]
st.sidebar.title(f"Bem-vindo(a), {name}")
authenticator.logout("Sair", "sidebar")

# --- INICIALIZAÇÃO DO FIREBASE ---
diretorio_atual = os.path.dirname(os.path.abspath(__file__))
caminho_chave = os.path.join(diretorio_atual, "chave.json")

if not firebase_admin._apps:
    try:
        cred = credentials.Certificate(caminho_chave)
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://extracaonadpdf-excel-default-rtdb.firebaseio.com/'
        })
    except Exception as e:
        st.error(f"Erro no Firebase: {e}")

# --- INTERFACE DO APP ---
st.title("💊 SOLICITAÇÃO DE PEDIDOS - UNIMED")

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
                                "Farmaceutico": name,
                                "Paciente": paciente,
                                "Quantidade": qtd,
                                "Descrição": desc,
                                "Hora": datetime.now().strftime("%H:%M:%S")
                            }
                            lista_final.append(item_dados)
                            ref_pedidos.push(item_dados)
        
        if lista_final:
            st.success(f"✅ Itens processados!")
            df = pd.DataFrame(lista_final)
            st.table(df)
            
            nome_excel = f"PedidoNAD_{datetime.now().strftime('%d%m%Y')}.xlsx"
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(f"📥 Baixar Planilha {nome_excel}", output.getvalue(), nome_excel)

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
