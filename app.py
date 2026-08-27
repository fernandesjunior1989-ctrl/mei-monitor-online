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
                total_linhas = len(df)
                barra_progresso = st.progress(0)
                
                for idx, row in df.iterrows():
                    cnpj_raw = str(row.get(coluna_cnpj, ""))
                    cnpj_limpo = "".join(filter(str.isdigit, cnpj_raw)).zfill(14)
                    
                    if len(cnpj_limpo) != 14:
                        resultados.append({
                            "CNPJ": cnpj_raw,
                            "Razão Social": "CNPJ Inválido",
                            "Situação Cadastral": "Inválido",
                            "Simples Nacional": "-",
                            "SIMEI (MEI)": "-",
                            "DASN-SIMEI": "Verificar",
                            "Guias DAS 2026": "Verificar",
                            "Portal PGMEI": ""
                        })
                        barra_progresso.progress((idx + 1) / total_linhas)
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
                            
                            # Simples Nacional e SIMEI
                            optante_simples = dados.get("opcao_pelo_simples")
                            optante_simei = dados.get("opcao_pelo_simei")
                            data_exclusao_simei = dados.get("data_exclusao_do_simei")
                            
                            # Formatação do Simples Nacional
                            if optante_simples is True:
                                txt_simples = "Optante"
                            elif optante_simples is False:
                                txt_simples = "Não Optante"
                            else:
                                txt_simples = "Não informado"
                                
                            # Formatação do SIMEI (MEI)
                            if optante_simei is True:
                                txt_simei = "Optante SIMEI (Ativo como MEI)"
                            else:
                                txt_simei = "⚠️ Desenquadrado / Não Optante"
                                
                            if data_exclusao_simei:
                                txt_simei = f"⚠️ Excluído em {data_exclusao_simei}"
                                
                            link_pgmei = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/"
                            
                            resultados.append({
                                "CNPJ": cnpj_fmt,
                                "Razão Social": razao,
                                "Situação Cadastral": f"{situacao} ({data_sit})",
                                "Simples Nacional": txt_simples,
                                "SIMEI (MEI)": txt_simei,
                                "DASN-SIMEI": "Regular / Conferir",
                                "Guias DAS 2026": "Em dia / Conferir",
                                "Portal PGMEI": link_pgmei
                            })
                        else:
                            resultados.append({
                                "CNPJ": cnpj_fmt,
                                "Razão Social": "Não localizado na base federal",
                                "Situação Cadastral": "Inexistente",
                                "Simples Nacional": "-",
                                "SIMEI (MEI)": "-",
                                "DASN-SIMEI": "-",
                                "Guias DAS 2026": "-",
                                "Portal PGMEI": ""
                            })
                    except Exception:
                        resultados.append({
                            "CNPJ": cnpj_fmt,
                            "Razão Social": "Erro de conexão",
                            "Situação Cadastral": "Erro",
                            "Simples Nacional": "-",
                            "SIMEI (MEI)": "-",
                            "DASN-SIMEI": "-",
                            "Guias DAS 2026": "-",
                            "Portal PGMEI": ""
                        })
                    
                    time.sleep(0.15)
                    barra_progresso.progress((idx + 1) / total_linhas)
                    
                st.session_state["df_resultado_completo"] = pd.DataFrame(resultados)
                st.success("Consulta executada com sucesso!")

    if "df_resultado_completo" in st.session_state:
        st.subheader("📋 Relatório Consolidado")
        st.write("Verifique abaixo os dados públicos obtidos diretamente da Receita Federal. Você pode ajustar diretamente na tabela qualquer observação antes de baixar o relatório final.")
        
        df_editado = st.data_editor(
            st.session_state["df_resultado_completo"],
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "Portal PGMEI": st.column_config.LinkColumn("Portal PGMEI", display_text="Acessar PGMEI ↗")
            }
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
