import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="wide")

st.title("MEI Monitor — Auditoria e Consulta MEI")
st.write("Envie sua planilha de CNPJs para verificar a situação cadastral, desenquadramento e obter os links diretos para consulta manual.")

uploaded_file = st.file_uploader("Selecione sua planilha de CNPJs (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
    
    if st.button("Gerar Relatório e Links de Consulta", type="primary"):
        with st.spinner("Analisando os dados da planilha..."):
            
            resultados = []
            
            for idx, row in df.iterrows():
                nome_empresa = row.get("Nome da Empresa", f"Empresa {idx + 1}")
                cnpj_raw = str(row.get("CNPJ", ""))
                
                # Corrige zeros à esquerda e garante 14 dígitos
                cnpj_limpo = "".join(filter(str.isdigit, cnpj_raw)).zfill(14)
                
                if len(cnpj_limpo) != 14:
                    resultados.append({
                        "Nome da Empresa": nome_empresa,
                        "CNPJ": cnpj_raw,
                        "Situação Cadastral": "CNPJ Inválido/Incompleto",
                        "Situação SIMEI (Desenquadramento)": "Inválido",
                        "DAS em Aberto (Consulta Manual)": "Pendente",
                        "DASN-SIMEI (Consulta Manual)": "Pendente",
                        "Link PGMEI": ""
                    })
                    continue
                
                # Formatação visual do CNPJ
                cnpj_fmt = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
                
                try:
                    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                    resp = requests.get(url, timeout=8)
                    
                    if resp.status_code == 200:
                        dados = resp.json()
                        situacao = dados.get("descricao_situacao_cadastral", "Ativa")
                        data_sit = dados.get("data_situacao_cadastral", "")
                        opcao_simei = dados.get("opcao_pelo_simei")
                        data_exclusao = dados.get("data_exclusao_do_simei")
                        
                        # Análise do SIMEI (Desenquadramento)
                        if opcao_simei is True:
                            status_simei = "Enquadrado como MEI (Ativo)"
                        else:
                            status_simei = "⚠️ DESENQUADRADO DO SIMEI"
                            
                        if data_exclusao:
                            status_simei = f"⚠️ Desenquadrado em {data_exclusao}"
                            
                        link_pgmei = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/"
                        
                        resultados.append({
                            "Nome da Empresa": nome_empresa,
                            "CNPJ": cnpj_fmt,
                            "Situação Cadastral": f"{situacao} (Desde {data_sit})",
                            "Situação SIMEI (Desenquadramento)": status_simei,
                            "DAS em Aberto (Consulta Manual)": "Verificar no PGMEI",
                            "DASN-SIMEI (Consulta Manual)": "Verificar no Portal",
                            "Link PGMEI": link_pgmei
                        })
                    else:
                        resultados.append({
                            "Nome da Empresa": nome_empresa,
                            "CNPJ": cnpj_fmt,
                            "Situação Cadastral": "Não localizado na Receita Federal",
                            "Situação SIMEI (Desenquadramento)": "-",
                            "DAS em Aberto (Consulta Manual)": "-",
                            "DASN-SIMEI (Consulta Manual)": "-",
                            "Link PGMEI": ""
                        })
                except Exception:
                    resultados.append({
                        "Nome da Empresa": nome_empresa,
                        "CNPJ": cnpj_fmt,
                        "Situação Cadastral": "Erro de conexão",
                        "Situação SIMEI (Desenquadramento)": "-",
                        "DAS em Aberto (Consulta Manual)": "-",
                        "DASN-SIMEI (Consulta Manual)": "-",
                        "Link PGMEI": ""
                    })
                
                time.sleep(0.2)
                
            df_resultado = pd.DataFrame(resultados)
            st.session_state["df_resultado"] = df_resultado
            st.success("Relatório gerado com sucesso!")

    # Exibe o painel e os botões de link manual se o relatório estiver pronto
    if "df_resultado" in st.session_state:
        st.subheader("📋 Prévia do Relatório de Auditoria")
        st.dataframe(st.session_state["df_resultado"], use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔗 Links Rápidos para Consulta Manual")
        st.write("Utilize os botões abaixo para acessar os portais oficiais da Receita Federal e realizar as consultas manuais:")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px 15px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;">Portal PGMEI (DAS) ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px 15px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;">DASN-SIMEI (Declaração) ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                '<a href="https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px 15px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;">Consulta CNPJ RFB ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            st.session_state["df_resultado"].to_excel(writer, index=False)
            
        st.download_button(
            label="📥 Baixar Planilha com Relatório e Links (.xlsx)",
            data=output.getvalue(),
            file_name="relatorio_mei_auditoria.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
