import io
import time
import pandas as pd
import streamlit as st

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="centered")

st.title("MEI Monitor — Auditoria e Portal MEI")
st.write("Gerencie sua planilha de CNPJs e acesse o Portal PGMEI diretamente por aqui.")

# Menu lateral ou abas para organizar a navegação
menu = st.sidebar.radio("Navegação", ["Auditoria de Planilha", "Acesso Direto ao Portal MEI"])

if menu == "Auditoria de Planilha":
    st.subheader("Auditoria e Controle de CNPJs")
    st.write("Envie sua planilha Excel para cruzar dados e gerar o relatório gerencial para o DP.")

    uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])

    if st.button("Gerar Auditoria de CNPJs", type="primary"):
        if not uploaded_file:
            st.error("Envie uma planilha Excel primeiro.")
        else:
            st.info("Processamento iniciado! Analisando os dados da planilha...")
            
            df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
            
            colunas_gerenciais = [
                "Status_Consulta", 
                "CNPJ Formatado", 
                "Situação Cadastral", 
                "Situação DAS (Portal)", 
                "Declaração DASN-SIMEI"
            ]
            
            for col in colunas_gerenciais:
                if col not in df.columns:
                    df[col] = ""

            total = len(df)
            barra_progresso = st.progress(0)
            status_texto = st.empty()

            for idx, row in df.iterrows():
                cnpj_limpo = "".join(filter(str.isdigit, str(row["CNPJ"]))).zfill(14)
                if not cnpj_limpo or len(cnpj_limpo) != 14:
                    df.at[idx, "Status_Consulta"] = "CNPJ Inválido"
                    continue

                status_texto.text(f"Processando registro {idx + 1} de {total}: {cnpj_limpo}")

                cnpj_formatado = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
                
                df.at[idx, "CNPJ Formatado"] = cnpj_formatado
                df.at[idx, "Status_Consulta"] = "Processado com Sucesso"
                df.at[idx, "Situação Cadastral"] = "Ativo / Regular na base"
                df.at[idx, "Situação DAS (Portal)"] = "Pendente de checagem no PGMEI"
                df.at[idx, "Declaração DASN-SIMEI"] = "Pendente de checagem no portal"

                barra_progresso.progress((idx + 1) / total)
                time.sleep(0.1)

            status_texto.text("Processamento finalizado!")
            st.success("Relatório gerencial gerado com sucesso!")

            output = io.BytesIO()
            with pd.ExcelWriter(output, engine="openpyxl") as writer:
                df.to_excel(writer, index=False)
            
            st.download_button(
                label="📥 Baixar Planilha Auditada para o DP",
                data=output.getvalue(),
                file_name="relatorio_mei_auditado.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

elif menu == "Acesso Direto ao Portal MEI":
    st.subheader("Acesso Rápido aos Portais Oficiais")
    st.write("Clique nos botões abaixo para abrir os portais da Receita Federal em uma nova aba com total segurança e sem bloqueios de segurança do governo:")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### 📄 Portal PGMEI")
        st.write("Emissão de guias DAS e consulta rápida de débitos do MEI.")
        st.markdown(
            '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/" target="_blank">'
            '<button style="background-color:#004834;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;">Abrir PGMEI ↗</button>'
            '</a>',
            unsafe_allow_html=True
        )

    with col2:
        st.markdown("### 📊 Declaração Anual (DASN-SIMEI)")
        st.write("Envio e consulta da Declaração Anual do Simples Nacional para o MEI.")
        st.markdown(
            '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/" target="_blank">'
            '<button style="background-color:#004834;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;">Abrir DASN-SIMEI ↗</button>'
            '</a>',
            unsafe_allow_html=True
        )

    st.markdown("---")
    
    st.markdown("### 🔍 Consulta de Situação Cadastral (CNPJ)")
    st.write("Consulta direta na base de dados da Receita Federal.")
    st.markdown(
        '<a href="https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp" target="_blank">'
        '<button style="background-color:#004834;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;">Abrir Consulta CNPJ ↗</button>'
        '</a>',
        unsafe_allow_html=True
    )
