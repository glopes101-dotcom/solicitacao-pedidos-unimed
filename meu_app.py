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
# Aqui cadastramos a Ludmilla e você. A senha padrão é Unimed@540
names = ["Ludmilla Vilela", "Gustavo Lopes Rodrigues"]
usernames = ["ludmilla.vilela", "gustavo.lopes"]
# As senhas no Authenticator precisam estar criptografadas ou em texto simples (neste caso simplificado)
passwords = ["Unimed@540", "Unimed@540"]

# Criando o objeto de autenticação
authenticator = stauth.Authenticate(
    {"usernames": {
        usernames[0]: {"name": names[0], "password": passwords[0]},
        usernames[1]: {"name": names[1], "password": passwords[1]}
    }},
    "unimed_cookie", "unimed_key", cookie_expiry_days=30
)

# Renderiza a tela de login
name, authentication_status, username = authenticator.login("Login - Extrator Unimed", "main")

if authentication_status == False:
    st.error("Usuário ou senha incorretos")
    st.stop()
elif authentication_status == None:
    st.warning("Por favor, insira seu e-mail e senha institucional.")
    st.stop()

# --- SE CHEGOU AQUI, O LOGIN FOI SUCESSO ---
st.sidebar.title(f"Bem-vindo(a), {name}")
authenticator.logout("Sair", "sidebar")

# Localizar a chave na pasta
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
        st.error(f"Erro ao carregar a chave do Firebase: {e}")

st.title("💊 SOLICITAÇÃO DE PEDIDOS - UNIMED")
st.write(f"Usuário logado: **{name}**")

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
                                "Farmaceutico": name, # Agora sabemos quem enviou!
                                "Paciente": paciente,
                                "Quantidade": qtd,
                                "Descrição": desc,
                                "Hora_Importacao": datetime.now().strftime("%H:%M:%S")
                            }
                            lista_final.append(item_dados)
                            ref_pedidos.push(item_dados)
        
        if lista_final:
            st.success(f"✅ {len(lista_final)} itens processados por {name}!")
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
