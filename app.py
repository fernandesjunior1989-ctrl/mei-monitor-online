import io
import time
import pandas as pd
import requests
import streamlit as st

st.set_page_config(page_title="MEI Monitor — Painel de Acompanhamento e Regularidade", page_icon="📊", layout="wide")

st.title("MEI Monitor — Gestão e Fila de Pendências de MEIs")
st.write("Plataforma integrada de acompanhamento baseada nas consultas oficiais (**consopt**, **PGMEI** e **DASN-SIMEI**).")

uploaded_file = st.file_uploader("Envie sua planilha de controle contendo os **CNPJs** (.xlsx)", type=["xlsx"])

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
        st.success(f"Coluna de CNPJ identificada com sucesso: **{coluna_cnpj}**")
        
        if st.button("🔄 Executar Varredura e Consolidar Status", type="primary"):
            with st.spinner("Consultando bases federais e estruturando painel..."):
                
                resultados = []
                
                for idx, row in df.iterrows():
                    nome_empresa = row.get("Nome da Empresa", row.get("Razão Social", f"Empresa {idx + 1}"))
                    cnpj_raw = str(row.get(coluna_cnpj, ""))
                    cnpj_limpo = "".join(filter(str.isdigit, cnpj_raw)).zfill(14)
                    
                    if len(cnpj_limpo) != 14:
                        resultados.append({
                            "CNPJ": cnpj_raw,
                            "CNPJ Limpo": cnpj_raw,
                            "Nome / Razão Social": nome_empresa,
                            "Status SIMEI (consopt)": "CNPJ Inválido",
                            "DAS (PGMEI)": "Verificar",
                            "DASN-SIMEI": "Verificar",
                            "Status Consolidado": "⚫ NÃO ANALISADO"
                        })
                        continue
                    
                    cnpj_fmt = f"{cnpj_limpo[:2]}.{cnpj_limpo[2:5]}.{cnpj_limpo[5:8]}/{cnpj_limpo[8:12]}-{cnpj_limpo[12:]}"
                    
                    try:
                        url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
                        resp = requests.get(url, timeout=8)
                        
                        if resp.status_code == 200:
                            dados = resp.json()
                            razao = dados.get("razao_social", nome_empresa)
                            situacao = dados.get("descricao_situacao_cadastral", "Ativa")
                            
                            optante_simei = dados.get("opcao_pelo_simei")
                            data_exclusao_simei = dados.get("data_exclusao_do_simei")
                            
                            # Validação consopt / SIMEI
                            if optante_simei is True and situacao.upper() == "ATIVA":
                                status_simei = "SIMEI Confirmado (Optante)"
                                status_inicial_padrao = "🟢 REGULAR"
                            else:
                                status_simei = "⚠️ Não Optante / Desenquadrado"
                                status_inicial_padrao = "🔴 IRREGULAR"
                                
                            if data_exclusao_simei:
                                status_simei = f"Excluído em {data_exclusao_simei}"
                                status_inicial_padrao = "🔴 IRREGULAR"

                            resultados.append({
                                "CNPJ": cnpj_fmt,
                                "CNPJ Limpo": cnpj_limpo,
                                "Nome / Razão Social": razao,
                                "Status SIMEI (consopt)": status_simei,
                                "DAS (PGMEI)": "Em dia",
                                "DASN-SIMEI": "Entregue (OK)",
                                "Status Consolidado": status_inicial_padrao
                            })
                        else:
                            resultados.append({
                                "CNPJ": cnpj_fmt,
                                "CNPJ Limpo": cnpj_limpo,
                                "Nome / Razão Social": nome_empresa,
                                "Status SIMEI (consopt)": "Não localizado na base",
                                "DAS (PGMEI)": "Verificar",
                                "DASN-SIMEI": "Verificar",
                                "Status Consolidado": "⚫ NÃO ANALISADO"
                            })
                    except Exception:
                        resultados.append({
                            "CNPJ": cnpj_fmt,
                            "CNPJ Limpo": cnpj_limpo,
                            "Nome / Razão Social": nome_empresa,
                            "Status SIMEI (consopt)": "Erro de conexão",
                            "DAS (PGMEI)": "Verificar",
                            "DASN-SIMEI": "Verificar",
                            "Status Consolidado": "⚫ NÃO ANALISADO"
                        })
                    
                    time.sleep(0.15)
                    
                st.session_state["df_painel"] = pd.DataFrame(resultados)
                st.success("Varredura e consolidação concluídas com sucesso!")

    if "df_painel" in st.session_state:
        
        st.markdown("---")
        st.subheader("📋 Fila de Pendências e Tabela Editável")
        st.write("Ajuste os status abaixo conforme a auditoria realizada nos portais oficiais:")
        
        # Tabela interativa colocada ANTES para que o painel leia as alterações em tempo real
        df_editado = st.data_editor(
            st.session_state["df_painel"],
            use_container_width=True,
            num_rows="fixed",
            column_config={
                "Status Consolidado": st.column_config.SelectboxColumn(
                    "Status Consolidado",
                    options=["🟢 REGULAR", "🟡 ATENÇÃO", "🔴 IRREGULAR", "⚫ NÃO ANALISADO"],
                    required=True
                )
            }
        )
        
        # Painel Consolidado atualizado dinamicamente com base na tabela editada
        st.markdown("---")
        st.subheader("📊 Painel Consolidado de Acompanhamento")
        
        total_analisados = len(df_editado)
        regulares = len(df_editado[df_editado["Status Consolidado"] == "🟢 REGULAR"])
        atencao = len(df_editado[df_editado["Status Consolidado"] == "🟡 ATENÇÃO"])
        irregulares = len(df_editado[df_editado["Status Consolidado"] == "🔴 IRREGULAR"])
        nao_analisados = len(df_editado[df_editado["Status Consolidado"] == "⚫ NÃO ANALISADO"])
        
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        kpi1.metric("Total Analisados", total_analisados)
        kpi2.metric("🟢 Regulares", regulares)
        kpi3.metric("🟡 Atenção", atencao)
        kpi4.metric("🔴 Irregulares", irregulares)
        kpi5.metric("⚫ Não Analisados", nao_analisados)
        
        # Relatório Automático / Ação Necessária
        st.markdown("---")
        st.subheader("⚠️ Relatório Operacional — Ação Necessária")
        
        df_pendencias = df_editado[df_editado["Status Consolidado"].isin(["🟡 ATENÇÃO", "🔴 IRREGULAR"])]
        
        if not df_pendencias.empty:
            st.warning(f"Foram identificados **{len(df_pendencias)} MEIs** que exigem atuação do escritório:")
            for _, r in df_pendencias.iterrows():
                st.markdown(f"- **{r['CNPJ']}** | *{r['Nome / Razão Social']}* — Situação: **{r['Status Consolidado']}** (SIMEI: {r['Status SIMEI (consopt)']}, DAS: {r['DAS (PGMEI)']}, DASN: {r['DASN-SIMEI']})")
        else:
            st.success("Nenhum MEI com pendência crítica marcada na lista atual!")

        # Links Oficiais para Consulta Manual Rápida
        st.markdown("---")
        st.subheader("🔗 Atalhos Oficiais para Consulta Manual")
        st.write("Acesse diretamente os portais da Receita Federal citados no fluxo:")
        
        col_l1, col_l2, col_l3 = st.columns(3)
        with col_l1:
            st.markdown(
                '<a href="https://consopt.www8.receita.fazenda.gov.br/consultaoptantes" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:12px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;width:100%;font-size:13px;">1. Consulta Optantes (consopt) ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )
        with col_l2:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/Identificacao" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:12px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;width:100%;font-size:13px;">2. Portal PGMEI (DAS) ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )
        with col_l3:
            st.markdown(
                '<a href="https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/Identificacao" target="_blank">'
                '<button style="background-color:#004834;color:white;padding:12px;border:none;border-radius:6px;cursor:pointer;font-weight:bold;width:100%;font-size:13px;">3. Portal DASN-SIMEI ↗</button>'
                '</a>',
                unsafe_allow_html=True
            )

        st.markdown("---")
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df_editado.to_excel(writer, index=False)
            
        st.download_button(
            label="📥 Baixar Relatório Consolidado Completo (.xlsx)",
            data=output.getvalue(),
            file_name="relatorio_acompanhamento_mei.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
