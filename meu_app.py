import streamlit as st
from pypdf import PdfReader
import pandas as pd
from io import BytesIO
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Conversor NAD", layout="centered")

st.title("💊 Conversor de Pedidos NAD")
st.write("Transforme seus PDFs em planilhas Excel instantaneamente.")

# 1. Upload dos arquivos
arquivos_pdf = st.file_uploader("Selecione os arquivos PDF", type="pdf", accept_multiple_files=True)

if arquivos_pdf:
    dados_extraidos = []
    
    for pdf in arquivos_pdf:
        try:
            leitor = PdfReader(pdf)
            campos = leitor.get_fields()
            
            if campos:
                # Pega o nome do paciente (ajuste o ID se necessário)
                paciente = "Não Identificado"
                campo_paci = campos.get("Caixa de texto 4_3")
                if campo_paci and campo_paci.get('/V'):
                    paciente = str(campo_paci.get('/V')).strip()

                # Percorre as 12 linhas do formulário padrão
                sufixos = ["", "_2", "_3", "_4", "_5", "_6", "_7", "_8", "_9", "_10", "_11", "_12"]
                
                for suf in sufixos:
                    qtd = campos.get(f"Caixa de texto 5{suf}")
                    desc = campos.get(f"Caixa de texto 6{suf}")
                    
                    if qtd and desc:
                        v_qtd = str(qtd.get('/V', '')).strip()
                        v_desc = str(desc.get('/V', '')).strip()
                        
                        # Só adiciona se tiver texto na descrição e quantidade
                        if v_qtd and v_desc and v_qtd.upper() != "/OFF":
                            dados_extraidos.append({
                                "Paciente": paciente,
                                "Qtd": v_qtd,
                                "Medicamento/Item": v_desc,
                                "Origem": pdf.name
                            })
        except Exception as e:
            st.error(f"Erro ao ler o arquivo {pdf.name}: {e}")

    # 2. Exibição e Download
    if dados_extraidos:
        st.success(f"Sucesso! {len(dados_extraidos)} itens encontrados.")
        df = pd.DataFrame(dados_extraidos)
        
        # Mostra a tabela para conferência
        st.dataframe(df, use_container_width=True)
        
        # Cria o arquivo Excel na memória
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 BAIXAR PLANILHA EXCEL",
            data=output.getvalue(),
            file_name=f"Pedido_NAD_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
