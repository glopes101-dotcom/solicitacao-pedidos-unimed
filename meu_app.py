import streamlit as st
from pypdf import PdfReader
import pandas as pd
from io import BytesIO
from datetime import datetime
import firebase_admin
from firebase_admin import credentials, db
import json
import streamlit_authenticator as stauth

# 1. CONFIGURAÇÃO DE LOGIN
credentials_data = {
    "usernames": {
        "ludmilla.vilela": {"name": "Ludmilla Vilela", "password": "Unimed@540"},
        "gustavo.lopes": {"name": "Gustavo Lopes Rodrigues", "password": "Unimed@540"}
    }
}

# Inicializa o autenticador
authenticator = stauth.Authenticate(credentials_data, "unimed_cookie", "unimed_key", cookie_expiry_days=30)

# Tela de Login
authenticator.login(location='main')

if st.session_state.get("authentication_status") is False:
    st.error("Usuário ou senha incorretos")
    st.stop()
elif st.session_state.get("authentication_status") is None:
    st.warning("Por favor, insira seu usuário e senha institucional.")
    st.stop()

# --- LOGIN SUCESSO ---
name = st.session_state["name"]
st.sidebar.title(f"Olá, {name}")
authenticator.logout("Sair", "sidebar")

# 2. CONEXÃO COM O FIREBASE (MODO NUVEM)
if not firebase_admin._apps:
    try:
        # Tenta ler do "Cofre" do Streamlit primeiro
        if "firebase" in st.secrets:
            # Converte a string do segredo em dicionário
            firebase_info = json.loads(st.secrets["firebase"]["key"])
            cred = credentials.Certificate(firebase_info)
        else:
            # Se não achar o segredo, tenta o arquivo local (para seu teste no PC)
            cred = credentials.Certificate("chave.json")
            
        firebase_admin.initialize_app(cred, {
            'databaseURL': 'https://extracaonadpdf-excel-default-rtdb.firebaseio.com/'
        })
    except Exception as e:
        st.error(f"Erro de conexão com o Banco de Dados: {e}")

# 3. INTERFACE DO SISTEMA
st.title("💊 EXTRATOR DE PEDIDOS - UNIMED")

upload = st.file_uploader("Arraste os PDFs aqui", type="pdf", accept_multiple_files=True)

if upload:
    lista_final = []
    try:
        data_hoje = datetime.now().strftime("%Y-%m-%d")
        ref_pedidos = db.reference(f'pedidos/{data_hoje}')

        for arq in upload:
            reader = PdfReader(arq)
            campos = reader.get_fields()
            if campos:
                paci = campos.get("Caixa de texto 4_3", {}).get('/V', "Não encontrado")
                sufixos = ["", "_2", "_3", "_4", "_5", "_6", "_7", "_8", "_9", "_10", "_11", "_12"]
                
                for s in sufixos:
                    qtd = campos.get(f"Caixa de texto 5{s}", {}).get('/V')
                    desc = campos.get(f"Caixa de texto 6{s}", {}).get('/V')
                    
                    if qtd and desc and str(qtd).upper() != "/OFF":
                        item = {
                            "Farmaceutico": name,
                            "Paciente": str(paci),
                            "Quantidade": str(qtd),
                            "Descricao": str(desc),
                            "Hora": datetime.now().strftime("%H:%M:%S")
                        }
                        lista_final.append(item)
                        ref_pedidos.push(item) # Envia para o Firebase
        
        if lista_final:
            st.success(f"✅ {len(lista_final)} itens processados!")
            df = pd.DataFrame(lista_final)
            st.table(df)
            
            # Gerar Excel para baixar
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            st.download_button("📥 Baixar Planilha Excel", output.getvalue(), "Pedido_Unimed.xlsx")

    except Exception as e:
        st.error(f"Erro no processamento: {e}")
