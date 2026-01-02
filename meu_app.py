import firebase_admin
from firebase_admin import credentials, firestore
import streamlit as st
import json

# Função para garantir que o Firebase só ligue UMA vez
def inicializar_firebase():
    if not firebase_admin._apps:
        # Tenta pegar a chave dos Secrets do Streamlit
        try:
            if "firebase" in st.secrets:
                # Se estiver no Streamlit Cloud
                key_dict = json.loads(st.secrets["firebase"]["key"])
                cred = credentials.Certificate(key_dict)
                firebase_admin.initialize_app(cred)
            else:
                # Se estiver rodando no seu PC localmente
                cred = credentials.Certificate("chave.json")
                firebase_admin.initialize_app(cred)
        except Exception as e:
            st.error(f"Erro ao carregar credenciais: {e}")

# Chama a função logo no início do app
inicializar_firebase()

# Só depois disso você cria o banco de dados
db = firestore.client()
