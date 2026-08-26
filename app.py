import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="wide")

st.title("MEI Monitor — Consulta Automatizada de CNPJ e Status")
st.write("Envie sua planilha de CNPJs para realizar a varredura e gerar o relatório completo com a situação cadastral, desenquadramento, controle de DAS e DASN-SIMEI.")

uploaded_file = st.file_uploader("Selecione sua planilha de CNPJs (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
    
    if st.button("Executar Consulta Automatizada", type="primary"):
        with st.spinner("Realizando varredura na base de dados federal..."):
            
            resultados = []
            
            for idx, row in df.iterrows():
                nome_empresa = row.get("Nome da Empresa", f"Empresa {idx + 1}")
                cnpj_raw = str(row.get("CNPJ", ""))
                
                # Corrige zeros à esquerda e valida 14 dígitos
                cnpj_limpo = "".join(filter(str.isdigit, cnpj_raw)).zfill(14)
                
                if len(cnpj_limpo) != 14:
                    resultados.append({
                        "Nome da Empresa": nome_empresa,
                        "CNPJ": cnpj_raw,
                        "Situação Cadastral": "CNPJ Inválido",
                        "Situação SIMEI": "Inválido",
                        "DAS em Aberto": "Verificar",
                        "DASN-SIMEI": "Verificar",
                        "Portal PGMEI": ""
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
                        
                        # Análise do SIMEI (Enquadramento/Desenquadramento)
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
                            "Situação SIMEI": status_simei,
                            "DAS em Aberto": "Pendente de checagem no PGMEI",
                            "DASN-SIMEI": "Pendente de checagem no portal",
                            "Portal PGMEI": link_pgmei
                        })
                    else:
                        resultados.append({
                            "Nome da Empresa": nome_empresa,
                            "CNPJ": cnpj_fmt,
                            "Situação Cadastral": "Não localizado na Receita Federal",
                            "Situação SIMEI": "-",
                            "DAS em Aberto": "-",
                            "DASN-SIMEI": "-",
                            "Portal PGMEI": ""
                        })
                except Exception:
                    resultados.append({
                        "Nome da Empresa": nome_empresa,
                        "CNPJ": cnpj_fmt,
                        "Situação Cadastral": "Erro de conexão",
                        "Situação SIMEI": "-",
                        "DAS em Aberto": "-",
                        "DASN-SIMEI": "-",
                        "Portal PGMEI": ""
                    })
                
                time.sleep(0.1)
                
            df_resultado = pd.DataFrame(resultados)
            st.session_state["df_resultado"] = df_resultado
            st.success("Consulta automatizada concluída com sucesso!")

    if "df_resultado" in st.session_state:
        st.subheader("📋 Relatório Consolidado")
        st.dataframe(
            st.session_state["df_resultado"],
            use_container_width=True,
            column_config={
                "Portal PGMEI": st.column_config.LinkColumn("Link PGMEI", display_text="Abrir Portal ↗")
            }
        )
        
        st.markdown("---")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            st.session_state["df_resultado"].to_excel(writer, index=False)
            
        st.download_button(
            label="📥 Baixar Planilha Consolidada (.xlsx)",
            data=output.getvalue(),
            file_name="relatorio_mei_automatizado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
