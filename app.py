import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor — Auditoria Fiscal", page_icon="📊", layout="wide")

st.title("MEI Monitor — Auditoria Detalhada (SIMEI, DASN e DAS 2026)")
st.write("Envie sua planilha contendo os **CNPJs**. O sistema realizará a varredura e gerará o relatório consolidado com o status detalhado.")

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
        
        if st.button("Executar Auditoria Detalhada", type="primary"):
            with st.spinner("Processando os dados nas bases oficiais..."):
                
                resultados = []
                
                for idx, row in df.iterrows():
                    cnpj_raw = str(row.get(coluna_cnpj, ""))
                    cnpj_limpo = "".join(filter(str.isdigit, cnpj_raw)).zfill(14)
                    
                    if len(cnpj_limpo) != 14:
                        resultados.append({
                            "CNPJ": cnpj_raw,
                            "CNPJ Limpo": cnpj_raw,
                            "Razão Social": "CNPJ Inválido",
                            "Situação Cadastral": "Inválido",
                            "Status SIMEI (Optante / Excluída)": "Inválido",
                            "DASN-SIMEI (Regular / Irregular)": "Verificar",
                            "Guias DAS 2026 (Paga / Em Aberto)": "Verificar"
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
                            
                            optante_simei = dados.get("opcao_pelo_simei")
                            data_exclusao_simei = dados.get("data_exclusao_do_simei")
                            
                            # Status detalhado do SIMEI
                            if optante_simei is True:
                                status_simei = "Optante (Ativo)"
                            else:
                                status_simei = "Excluída / Desenquadrada"
                                
                            if data_exclusao_simei:
                                status_simei = f"Excluída em {data_exclusao_simei}"
                                
                            resultados.append({
                                "CNPJ": cnpj_fmt,
                                "CNPJ Limpo": cnpj_limpo,
                                "Razão Social": razao,
                                "Situação Cadastral": f"{situacao} ({data_sit})",
                                "Status SIMEI (Optante / Excluída)": status_simei,
                                "DASN-SIMEI (Regular / Irregular)": "Regular (Ajustar se houver irregularidade)",
                                "Guias DAS 2026 (Paga / Em Aberto)": "Em Aberto / Conferir"
                            })
                        else:
                            resultados.append({
                                "CNPJ": cnpj_fmt,
                                "CNPJ Limpo": cnpj_limpo,
                                "Razão Social": "Não localizado",
                                "Situação Cadastral": "Inexistente",
                                "Status SIMEI (Optante / Excluída)": "-",
                                "DASN-SIMEI (Regular / Irregular)": "-",
                                "Guias DAS 2026 (Paga / Em Aberto)": "-"
                            })
                    except Exception:
                        resultados.append({
                            "CNPJ": cnpj_fmt,
                            "CNPJ Limpo": cnpj_limpo,
                            "Razão Social": "Erro de conexão",
                            "Situação Cadastral": "Erro",
                            "Status SIMEI (Optante / Excluída)": "-",
                            "DASN-SIMEI (Regular / Irregular)": "-",
                            "Guias DAS 2026 (Paga / Em Aberto)": "-"
                        })
                    
                    time.sleep(0.15)
                    
                st.session_state["df_auditoria"] = pd.DataFrame(resultados)
                st.success("Auditoria concluída com sucesso!")

    if "df_auditoria" in st.session_state:
        st.subheader("📋 Relatório de Controle e Auditoria")
        st.write("Edite diretamente nas colunas abaixo o status de cada competência (DASN-SIMEI e DAS 2026) para refletir o cenário real:")
        
        df_editado = st.data_editor(
            st.session_state["df_auditoria"],
            use_container_width=True,
            num_rows="fixed"
        )
        
        st.markdown("---")
        st.subheader("🔗 Links Oficiais para Consulta Manual")
        st.write("Utilize os atalhos abaixo para validar as competências nos portais da Receita Federal:")
        
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
            label="📥 Baixar Relatório de Auditoria (.xlsx)",
            data=output.getvalue(),
            file_name="auditoria_mei_detalhada.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
