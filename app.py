import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor — Consulta Fiscal", page_icon="📊", layout="wide")

st.title("MEI Monitor — Consulta Automatizada e Ações Rápidas")
st.write("Envie sua planilha de **CNPJs** para consultar os dados e acessar atalhos diretos via botões para cada empresa.")

uploaded_file = st.file_uploader("Selecione sua planilha de CNPJs (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype=str)
    
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
            with st.spinner("Consultando dados e gerando links de acesso..."):
                resultados = []
                total_linhas = len(df)
                barra_progresso = st.progress(0)
                
                for idx, row in df.iterrows():
                    cnpj_raw = str(row.get(coluna_cnpj, ""))
                    cnpj_limpo = "".join(filter(str.isdigit, cnpj_raw)).zfill(14)
                    
                    link_pgmei = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/"
                    link_dasn = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/"
                    link_simples_consulta = f"https://www8.receita.fazenda.gov.br/SimplesNacional/aplicacoes/atspo/consultaoptantes.app/ConsultarOpcao.aspx?cnpj={cnpj_limpo}"
                    link_cartao_cnpj = "https://solucoes.receita.fazenda.gov.br/Servicos/cnpjreva/Cnpjreva_Solicitacao.asp"
                    
                    if len(cnpj_limpo) != 14:
                        resultados.append({
                            "CNPJ": cnpj_limpo,
                            "Razão Social": "CNPJ Inválido",
                            "Situação Cadastral": "Inválido",
                            "SITUAÇÃO SIMEI": "Inválido",
                            "GUIA DAS": "Pendência Manual",
                            "DEC ANUAL": "Pendência Manual",
                            "link_pgmei": link_pgmei,
                            "link_dasn": link_dasn,
                            "link_simples": link_simples_consulta,
                            "link_cartao": link_cartao_cnpj
                        })
                        barra_progresso.progress((idx + 1) / total_linhas)
                        continue
                    
                    try:
                        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                        resp = requests.get(url, timeout=10)
                        
                        if resp.status_code == 200:
                            dados = resp.json()
                            razao = dados.get("razao_social", "Não informada")
                            situacao = dados.get("descricao_situacao_cadastral", "Ativa")
                            data_sit = dados.get("data_situacao_cadastral", "")
                            
                            opcao_mei = dados.get("opcao_pelo_mei")
                            data_opcao_mei = dados.get("data_opcao_pelo_mei")
                            data_exclusao_mei = dados.get("data_exclusao_do_mei")
                            
                            if opcao_mei and data_exclusao_mei in [None, "", "None"]:
                                txt_simei = "Optante (Regular)"
                            elif data_exclusao_mei not in [None, "", "None"]:
                                txt_simei = f"Desenquadrada em {data_exclusao_mei}"
                            else:
                                txt_simei = "Não Optante pelo SIMEI"
                            
                            resultados.append({
                                "CNPJ": cnpj_limpo,
                                "Razão Social": razao,
                                "Situação Cadastral": f"{situacao} ({data_sit})" if data_sit else situacao,
                                "SITUAÇÃO SIMEI": txt_simei,
                                "GUIA DAS": "Conferir no PGMEI",
                                "DEC ANUAL": "Conferir no PGMEI",
                                "link_pgmei": link_pgmei,
                                "link_dasn": link_dasn,
                                "link_simples": link_simples_consulta,
                                "link_cartao": link_cartao_cnpj
                            })
                        else:
                            resultados.append({
                                "CNPJ": cnpj_limpo,
                                "Razão Social": "Não localizado",
                                "Situação Cadastral": "Erro/Inexistente",
                                "SITUAÇÃO SIMEI": "-",
                                "GUIA DAS": "-",
                                "DEC ANUAL": "-",
                                "link_pgmei": link_pgmei,
                                "link_dasn": link_dasn,
                                "link_simples": link_simples_consulta,
                                "link_cartao": link_cartao_cnpj
                            })
                    except Exception:
                        resultados.append({
                            "CNPJ": cnpj_limpo,
                            "Razão Social": "Erro de conexão",
                            "Situação Cadastral": "Falha Requisição",
                            "SITUAÇÃO SIMEI": "-",
                            "GUIA DAS": "-",
                            "DEC ANUAL": "-",
                            "link_pgmei": link_pgmei,
                            "link_dasn": link_dasn,
                            "link_simples": link_simples_consulta,
                            "link_cartao": link_cartao_cnpj
                        })
                    
                    time.sleep(0.2)
                    barra_progresso.progress((idx + 1) / total_linhas)
                    
                st.session_state["df_resultado_completo"] = pd.DataFrame(resultados)
                st.success("Consulta finalizada com sucesso!")

    if "df_resultado_completo" in st.session_state:
        df_full = st.session_state["df_resultado_completo"]
        
        st.subheader("📋 Relatório Consolidado")
        
        # Exibe tabela formatada sem expor URLs brutas
        colunas_exibicao = ["CNPJ", "Razão Social", "Situação Cadastral", "SITUAÇÃO SIMEI", "GUIA DAS", "DEC ANUAL"]
        
        df_editado = st.data_editor(
            df_full[colunas_exibicao],
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "GUIA DAS": st.column_config.SelectboxColumn("GUIA DAS", options=["Conferir no PGMEI", "Regular", "Em aberto", "Parcelado"]),
                "DEC ANUAL": st.column_config.SelectboxColumn("DEC ANUAL", options=["Conferir no PGMEI", "Entregue", "Pendente"])
            }
        )
        
        st.markdown("---")
        
        # Painel de Botões de Acesso Direto por Empresa
        st.subheader("🔗 Central de Acesso Rápido por CNPJ")
        st.caption("Selecione uma empresa da lista para liberar os botões diretos de consulta:")
        
        cnpjs_lista = df_full["CNPJ"].tolist()
        cnpj_selecionado = st.selectbox("Selecione o CNPJ para acessar os portais:", cnpjs_lista)
        
        if cnpj_selecionado:
            row_sel = df_full[df_full["CNPJ"] == cnpj_selecionado].iloc[0]
            
            st.markdown(f"**Empresa:** `{row_sel['Razão Social']}` | **CNPJ:** `{row_sel['CNPJ']}`")
            
            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.link_button("🌐 Emitir DAS (PGMEI)", row_sel["link_pgmei"], use_container_width=True)
            with c2:
                st.link_button("📄 Declaração Anual (DASN)", row_sel["link_dasn"], use_container_width=True)
            with c3:
                st.link_button("🔍 Comprovante SIMEI", row_sel["link_simples"], use_container_width=True)
            with c4:
                st.link_button("📜 Cartão CNPJ Receita", row_sel["link_cartao"], use_container_width=True)

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
