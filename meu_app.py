import streamlit as st
from pypdf import PdfReader
import pandas as pd
from io import BytesIO
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="Conversor NAD", layout="wide")

st.title("💊 SISTEMA DE EXTRAÇÃO NAD - VERSÃO LOCAL")
st.write("Suba os PDFs e baixe a planilha. (Nenhum dado é salvo na nuvem)")

# Upload de arquivos
upload = st.file_uploader("Arraste os PDFs aqui", type="pdf", accept_multiple_files=True)

if upload:
    lista_final = []
    
    try:
        for arq in upload:
            reader = PdfReader(arq)
            campos = reader.get_fields()
            
            if campos:
                # Localiza o paciente
                paciente = "Não encontrado"
                campo_paci = campos.get("Caixa de texto 4_3")
                if campo_paci and campo_paci.get('/V'):
                    paciente = str(campo_paci.get('/V')).strip()

                # Percorre as 12 linhas do formulário
                sufixos = ["", "_2", "_3", "_4", "_5", "_6", "_7", "_8", "_9", "_10", "_11", "_12"]
                
                for suf in sufixos:
                    campo_qtd = campos.get(f"Caixa de texto 5{suf}")
                    campo_desc = campos.get(f"Caixa de texto 6{suf}")
                    
                    if campo_qtd and campo_desc:
                        qtd = str(campo_qtd.get('/V', '')).strip()
                        desc = str(campo_desc.get('/V', '')).strip()
                        
                        # Filtra apenas linhas com conteúdo
                        if qtd and desc and qtd.upper() != "/OFF":
                            lista_final.append({
                                "Paciente": paciente,
                                "Quantidade": qtd,
                                "Descrição": desc,
                                "Arquivo Origem": arq.name
                            })
        
        if lista_final:
            st.success(f"✅ {len(lista_final)} itens extraídos com sucesso!")
            df = pd.DataFrame(lista_final)
            
            # Exibe os dados na tela para conferência
            st.dataframe(df, use_container_width=True)
            
            # Preparar o download do Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 BAIXAR PLANILHA EXCEL",
                data=output.getvalue(),
                file_name=f"Relatorio_NAD_{datetime.now().strftime('%d-%m-%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        else:
            st.warning("Nenhum dado válido foi encontrado nos PDFs enviados.")

    except Exception as e:
        st.error(f"Erro ao processar: {e}")
