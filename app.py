import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="centered")

st.title("MEI Monitor — Relatório de Situação e Desenquadramento")
st.write("Envie sua planilha de CNPJs para auditar o enquadramento SIMEI e gerar o relatório gerencial para o DP.")

# Formulário Web
uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])

if st.button("Gerar Relatório de Auditoria", type="primary"):
    if not uploaded_file:
        st.error("Envie uma planilha Excel primeiro.")
    else:
        st.info("Processamento iniciado! Analisando dados cadastrais e de desenquadramento...")
        
        df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
        
        # Criação/Garantia das colunas de controle exigidas pelo DP
        colunas_necessarias = {
            "Status_Consulta": "Processado",
            "Situação Cadastral": "",
            "Optante SIMEI (MEI)": "",
            "Data Exclusão SIMEI": "",
            "Alerta Desenquadramento": "",
            "DAS em Aberto (Checagem)": "Verificar Portal PGMEI",
            "Declaração DASN Pendente": "Verificar Portal PGMEI"
        }
        
        for col, val in colunas_necessarias.items():
            if col not in df.columns:
                df[col] = val

        total = len(df)
        barra_progresso = st.progress(0)
        status_texto = st.empty()

        for idx, row in df.iterrows():
            cnpj_limpo = "".join(filter(str.isdigit, str(row["CNPJ"])))
            if not cnpj_limpo or len(cnpj_limpo) != 14:
                df.at[idx, "Status_Consulta"] = "CNPJ Inválido"
                continue

            status_texto.text(f"Analisando empresa {idx + 1} de {total}: {cnpj_limpo}")

            try:
                url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                response = requests.get(url, timeout=10)

                if response.status_code == 200:
                    dados = response.json()
                    
                    situacao = dados.get("descricao_situacao_cadastral", "Ativa")
                    data_situacao = dados.get("data_situacao_cadastral", "")
                    
                    # Dados específicos do MEI (SIMEI)
                    opcao_simei = dados.get("opcao_pelo_simei")
                    data_exclusao = dados.get("data_exclusao_do_simei")
                    
                    df.at[idx, "Status_Consulta"] = "Sucesso"
                    df.at[idx, "Situação Cadastral"] = f"{situacao} (desde {data_situacao})"
                    
                    if opcao_simei is True:
                        df.at[idx, "Optante SIMEI (MEI)"] = "SIM (Enquadrado)"
                        df.at[idx, "Alerta Desenquadramento"] = "Regular (Enquadrado como MEI)"
                    else:
                        df.at[idx, "Optante SIMEI (MEI)"] = "NÃO"
                        df.at[idx, "Alerta Desenquadramento"] = "⚠️ ATENÇÃO: DESENQUADRADO do SIMEI!"

                    if data_exclusao:
                        df.at[idx, "Data Exclusão SIMEI"] = str(data_exclusao)
                        df.at[idx, "Alerta Desenquadramento"] = f"⚠️ DESENQUADRADO em {data_exclusao}"
                    else:
                        df.at[idx, "Data Exclusão SIMEI"] = "Nenhuma exclusão registrada"

                elif response.status_code == 404:
                    df.at[idx, "Status_Consulta"] = "CNPJ não localizado na base federal"
                else:
                    df.at[idx, "Status_Consulta"] = f"Erro HTTP {response.status_code}"

            except Exception as err:
                df.at[idx, "Status_Consulta"] = "Erro de conexão"

            barra_progresso.progress((idx + 1) / total)
            time.sleep(0.3)

        status_texto.text("Relatório gerado com sucesso!")
        st.success("Auditoria cadastral e de desenquadramento concluída!")

        # Gera o arquivo Excel para download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Baixar Relatório Completo para DP",
            data=output.getvalue(),
            file_name="relatorio_auditoria_mei.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
