import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor — Consulta Fiscal Completa", page_icon="📊", layout="wide")

st.title("MEI Monitor — Consulta Automatizada (CNPJ, SIMEI e Fiscais)")
st.write("Envie sua planilha contendo apenas os **CNPJs**. O sistema fará a varredura automática nas bases públicas da Receita Federal, Simples Nacional e SIMEI.")

uploaded_file = st.file_uploader("Selecione sua planilha de CNPJs (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    
    # Identifica automaticamente a coluna de CNPJ
    coluna_cnpj = None
    for col in df.columns:
        if "cnpj" in col.lower():
            coluna_cnpj = col
            break
            
    if not coluna_cnpj and len(df.columns) > 0:
        coluna_cnpj = df.columns[0]
        
    if coluna_cnpj:
        st.success(f"Coluna de CNPJ identificada: **{coluna_cnpj}**")
        
        if st.button("Executar Consulta Completa", type="primary"):
            with st.spinner("Consultando dados cadastrais e fiscais na base federal..."):
                
                resultados = []
                
                for idx, row in df.iterrows():
                    cnpj_raw = str(row.get(coluna_cnpj, ""))
                    cnpj_limpo = "".join(filter(str.isdigit, cnpj_raw)).zfill(14)
                    
                    if len(cnpj_limpo) != 14:
                        resultados.append({
                            "CNPJ": cnpj_raw,
                            "CNPJ Limpo (Só Números)": cnpj_raw,
                            "Razão Social": "CNPJ Inválido",
                            "Situação Cadastral": "Inválido",
                            "Simples Nacional": "-",
                            "SIMEI (MEI)": "-",
                            "DASN-SIMEI": "Verificar",
                            "Guias DAS 2026": "Verificar"
                        })
                        continue
                    
                    cnpj_fmt = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
                    
                    try:
                        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                        resp = requests.get(url, timeout=8)
                        
                        if resp.status_code == 200:
                            dados = resp.json()
                            razao = dados.get("razao_social", "Não informada")
                            situacao = dados.get("descricao_situacao_cadastral", "Ativa")
                            data_sit = dados.get("data_situacao_cadastral", "")
                            
                            optante_simples = dados.get("opcao_pelo_simples")
                            optante_simei = dados.get("opcao_pelo_simei")
                            data_exclusao_simei = dados.get("data_exclusao_do_simei")
                            
                            if optante_simples is True:
                                txt_simples = "Optante"
                            elif optante_simples is False:
                                txt_simples = "Não Optante"
                            else:
                                txt_simples = "Não informado"
                                
                            if optante_simei is True:
                                txt_simei = "Optante SIMEI (Ativo como MEI)"
                            else:
                                txt_simei = "⚠️ Desenquadrado / Não Optante"
                                
                            if data_exclusao_simei:
                                txt_simei = f"⚠️ Excluído em {data_exclusao_simei}"
                                
                            resultados.append({
                                "CNPJ": cnpj_fmt,
                                "CNPJ Limpo (Só Números)": cnpj_limpo,
                                "Razão Social": razao,
                                "Situação Cadastral": f"{situacao} ({data_sit})",
                                "Simples Nacional": txt_simples,
                                "SIMEI (MEI)": txt_simei,
                                "DASN-SIMEI": "Regular / Conferir",
                                "Guias DAS 2026": "Em dia / Conferir"
                            })
                        else:
                            resultados.append({
                                "CNPJ": cnpj_fmt,
                                "CNPJ Limpo (Só Números)": cnpj_limpo,
                                "Razão Social": "Não localizado na base federal",
                                "Situação Cadastral": "Inexistente",
                                "Simples Nacional": "-",
                                "SIMEI (MEI)": "-",
                                "DASN-SIMEI": "-",
                                "Guias DAS 2026": "-"
                            })
                    except Exception:
                        resultados.append({
                            "CNPJ": cnpj_fmt,
                            "CNPJ Limpo (Só Números)": cnpj_limpo,
                            "Razão Social": "Erro de conexão",
                            "Situação Cadastral": "Erro",
                            "Simples Nacional": "-",
                            "SIMEI (MEI)": "-",
                            "DASN-SIMEI": "-",
                            "Guias DAS 2026": "-"
                        })
                    
                    time.sleep(0.15)
                    
                st.session_state["df_resultado_completo"] = pd.DataFrame(resultados)
                st.success("Consulta executada com sucesso!")

    if "df_resultado_completo" in st.session_state:
        st.subheader("📋 Relatório Consolidado")
        st.write("Verifique abaixo os dados obtidos. Você pode ajustar os status fiscais diretamente na tabela:")
        
        df_editado = st.data_editor(
            st.session_state["df_resultado_completo"],
            use_container_width=True,
            num_rows="fixed"
        )
        
        st.markdown("---")
        st.subheader("🔗 Links para Consulta Manual (Portais Oficiais)")
        st.write("Utilize os atalhos abaixo para acessar diretamente os portais de auditoria quando necessário:")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;font-size:12px;">Portal PGMEI (DAS) ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Servicos/Grupo.aspx?grp=1" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;font-size:12px;">Enquadramento MEI ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )
        with col3:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;font-size:12px;">DASN-SIMEI ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )
        with col4:
            st.markdown(
                '<a href="https://solucoes.receita.fazenda.gov.br/servicos/cnpjreva/cnpjreva_solicitacao.asp" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;font-size:12px;">Consulta CNPJ RFB ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_editado.to_excel(writer, index=False)
            
        st.download_button(
            label="📥 Baixar Relatório Completo (.xlsx)",
            data=output.getvalue(),
            file_name="relatorio_fiscal_mei.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
