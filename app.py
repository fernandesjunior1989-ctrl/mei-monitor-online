import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="centered")

st.title("MEI Monitor — Consulta Rápida via API")
st.write("Envie sua planilha de CNPJs para consultar o status cadastral e do Simples Nacional de forma instantânea.")

# Formulário Web
uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])

if st.button("Iniciar Processamento", type="primary"):
    if not uploaded_file:
        st.error("Envie uma planilha Excel primeiro.")
    else:
        st.info("Processamento iniciado! Consultando base de dados...")
        
        # Lê a planilha preservando o CNPJ como string
        df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
        
        # Garante a existência das colunas de retorno se não existirem
        if "Status_Consulta" not in df.columns:
            df["Status_Consulta"] = ""
        if "Situação Simples" not in df.columns:
            df["Situação Simples"] = ""
            
        total = len(df)
        barra_progresso = st.progress(0)
        status_texto = st.empty()

        for idx, row in df.iterrows():
            cnpj_limpo = "".join(filter(str.isdigit, str(row["CNPJ"])))
            if not cnpj_limpo or len(cnpj_limpo) != 14:
                df.at[idx, "Status_Consulta"] = "CNPJ Inválido/Incompleto"
                continue

            status_texto.text(f"Consultando MEI {idx + 1} de {total}: {cnpj_limpo}")

            try:
                # Consulta estruturada na API pública de CNPJ e Simples Nacional
                url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    dados = response.json()
                    
                    # Extrai dados da empresa
                    situacao_cadastral = dados.get("descricao_situacao_cadastral", "Ativa")
                    opcao_simples = dados.get("opcao_pelo_simples")
                    opcao_simei = dados.get("opcao_pelo_simei")
                    
                    # Formata status amigável para o DP
                    status_partes = [f"Situação: {situacao_cadastral}"]
                    if opcao_simples is True:
                        status_partes.append("Simples: Sim")
                    elif opcao_simples is False:
                        status_partes.append("Simples: Não")
                        
                    if opcao_simei is True:
                        status_partes.append("MEI (Simei): Sim")
                    elif opcao_simei is False:
                        status_partes.append("MEI (Simei): Não")

                    df.at[idx, "Status_Consulta"] = "Consulta Concluída"
                    df.at[idx, "Situação Simples"] = " | ".join(status_partes)
                
                elif response.status_code == 404:
                    df.at[idx, "Status_Consulta"] = "CNPJ não encontrado"
                else:
                    df.at[idx, "Status_Consulta"] = f"Erro API: Status {response.status_code}"

            except Exception as err:
                df.at[idx, "Status_Consulta"] = f"Erro de conexão"

            barra_progresso.progress((idx + 1) / total)
            time.sleep(0.3) # Pequena pausa para estabilidade da requisição

        status_texto.text("Processamento finalizado com sucesso!")
        st.success("Todas as consultas foram concluídas!")

        # Gera o arquivo Excel atualizado para download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Baixar Planilha com Resultados",
            data=output.getvalue(),
            file_name="resultado_meis_atualizado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
