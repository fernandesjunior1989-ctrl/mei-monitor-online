import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor — DP", page_icon="📊", layout="wide")

st.title("MEI Monitor — Auditoria e Controle para DP")
st.write("Auditoria de CNPJs, verificação de desenquadramento SIMEI e acesso rápido aos portais de DAS e DASN.")

uploaded_file = st.file_uploader("Selecione sua planilha de CNPJs (.xlsx)", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
    
    if st.button("Executar Auditoria de CNPJs", type="primary"):
        with st.spinner("Analisando dados cadastrais e de desenquadramento..."):
            
            # Inicializa colunas de controle se não existirem
            colunas = ["CNPJ Limpo", "Razão Social / Empresa", "Situação Cadastral", "Optante SIMEI", "Alerta Desenquadramento", "Link PGMEI"]
            
            resultados = []
            
            for idx, row in df.iterrows():
                # Tenta pegar o nome da empresa se existir na planilha
                nome_empresa = row.get("Nome da Empresa", f"Empresa {idx + 1}")
                cnpj_raw = str(row.get("CNPJ", ""))
                
                # Trata o CNPJ corrigindo zeros à esquerda
                cnpj_limpo = "".join(filter(str.isdigit, cnpj_raw)).zfill(14)
                
                if len(cnpj_limpo) != 14:
                    resultados.append({
                        "Nome da Empresa": nome_empresa,
                        "CNPJ": cnpj_raw,
                        "Situação Cadastral": "CNPJ Inválido",
                        "Optante SIMEI": "-",
                        "Alerta Desenquadramento": "Verificar formato do CNPJ",
                        "Link PGMEI": ""
                    })
                    continue
                
                # Formatação visual do CNPJ
                cnpj_fmt = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
                
                # Consulta na API pública de CNPJ e SIMEI
                try:
                    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                    resp = requests.get(url, timeout=8)
                    
                    if resp.status_code == 200:
                        dados = resp.json()
                        situacao = dados.get("descricao_situacao_cadastral", "Ativa")
                        data_sit = dados.get("data_situacao_cadastral", "")
                        opcao_simei = dados.get("opcao_pelo_simei")
                        data_exclusao = dados.get("data_exclusao_do_simei")
                        
                        # Define status do SIMEI
                        if opcao_simei is True:
                            status_simei = "SIM (Enquadrado)"
                            alerta = "Regular como MEI"
                        else:
                            status_simei = "NÃO"
                            alerta = "⚠️ ATENÇÃO: DESENQUADRADO do SIMEI!"
                            
                        if data_exclusao:
                            alerta = f"⚠️ Desenquadrado em {data_exclusao}"
                            
                        link_pgmei = f"https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/"
                        
                        resultados.append({
                            "Nome da Empresa": nome_empresa,
                            "CNPJ": cnpj_fmt,
                            "Situação Cadastral": f"{situacao} ({data_sit})",
                            "Optante SIMEI": status_simei,
                            "Alerta Desenquadramento": alerta,
                            "Link PGMEI": link_pgmei
                        })
                    else:
                        resultados.append({
                            "Nome da Empresa": nome_empresa,
                            "CNPJ": cnpj_fmt,
                            "Situação Cadastral": "Não encontrada na base federal",
                            "Optante SIMEI": "-",
                            "Alerta Desenquadramento": "Erro na consulta",
                            "Link PGMEI": ""
                        })
                except Exception:
                    resultados.append({
                        "Nome da Empresa": nome_empresa,
                        "CNPJ": cnpj_fmt,
                        "Situação Cadastral": "Erro de conexão",
                        "Optante SIMEI": "-",
                        "Alerta Desenquadramento": "Erro",
                        "Link PGMEI": ""
                    })
                
                time.sleep(0.2)
                
            df_resultado = pd.DataFrame(resultados)
            st.session_state["df_resultado"] = df_resultado
            st.success("Auditoria concluída com sucesso!")

    # Se já houver resultado processado, exibe na tela com opções de conferência e download
    if "df_resultado" in st.session_state:
        st.subheader("📋 Painel de Auditoria e Status")
        st.dataframe(st.session_state["df_resultado"], use_container_width=True)
        
        st.markdown("---")
        st.subheader("🔗 Links Rápidos para Conferência de DAS e DASN-SIMEI")
        st.write("Abra o portal oficial com 1 clique para verificar guias em aberto ou declarações pendentes de cada CNPJ:")
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;">Abrir Portal PGMEI (DAS) ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )
        with col2:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:10px 20px;border:none;border-radius:5px;cursor:pointer;font-weight:bold;width:100%;">Abrir Declaração DASN-SIMEI ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        
        # Botão para baixar a planilha auditada
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            st.session_state["df_resultado"].to_excel(writer, index=False)
            
        st.download_button(
            label="📥 Baixar Relatório Completo em Excel",
            data=output.getvalue(),
            file_name="relatorio_dp_mei.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
