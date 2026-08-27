import io
import re
import time
import urllib.parse
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIGURAÇÃO DA PÁGINA & IDENTIDADE VISUAL (CLÁSSICO & REALISTA)
# ============================================================

st.set_page_config(
    page_title="MEI Monitor V2 — Auditoria Fiscal",
    page_icon="⚖️",
    layout="wide"
)

# Injeção de CSS Customizado (Tema Clássico / Bordô & Dourado Realista)
st.markdown(
    """
    <style>
    /* Estilização Geral do Fundo e Tipografia */
    .stApp {
        background-color: #F9F8F6;
        color: #2C2C2C;
        font-family: 'Georgia', serif;
    }
    
    /* Cabeçalho do Sistema / Banner */
    .main-header {
        background: linear-gradient(135deg, #4A2E35 0%, #2A191D 100%);
        padding: 30px;
        border-radius: 8px;
        border-left: 6px solid #C5A059;
        color: #F9F8F6;
        margin-bottom: 25px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .main-header h1 {
        font-family: 'Georgia', serif;
        color: #F9F8F6;
        margin: 0;
        font-size: 28px;
        letter-spacing: 0.5px;
    }
    .main-header p {
        color: #D4AF37;
        margin: 8px 0 0 0;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }

    /* Cartões de Métricas Estilizados */
    [data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2D9CD;
        padding: 15px;
        border-radius: 6px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.03);
        border-top: 4px solid #4A2E35;
    }
    [data-testid="stMetricLabel"] {
        font-family: 'Georgia', serif;
        color: #555555 !important;
        font-size: 13px !important;
    }
    [data-testid="stMetricValue"] {
        font-family: 'Georgia', serif;
        color: #4A2E35 !important;
        font-weight: bold;
    }

    /* Botões Principais */
    .stButton button[kind="primary"] {
        background-color: #4A2E35 !important;
        color: #FFFFFF !important;
        border: 1px solid #C5A059 !important;
        font-family: 'Georgia', serif;
        font-weight: bold;
        border-radius: 4px;
        padding: 0.5rem 1rem;
        transition: all 0.3s ease;
    }
    .stButton button[kind="primary"]:hover {
        background-color: #5A3841 !important;
        border-color: #D4AF37 !important;
        box-shadow: 0 4px 8px rgba(74, 46, 53, 0.2);
    }

    /* Expander e Divisores */
    .streamlit-expanderHeader {
        background-color: #FFFFFF;
        border: 1px solid #E2D9CD;
        border-radius: 4px;
        font-family: 'Georgia', serif;
    }
    hr {
        border-color: #E2D9CD;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ============================================================
# URLS DOS PORTAIS OFICIAIS
# ============================================================

CONSOPT_URL_BASE = "https://consopt.www8.receita.fazenda.gov.br/consultaoptantes/Resultado"
PGMEI_URL_BASE = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/EmissaoDocumento"
DASN_URL_BASE = "https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/dasnsimei.app/Declaracao"

TIMEOUT = 10

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def limpar_cnpj(valor):
    if pd.isna(valor): return ""
    cnpj = re.sub(r"\D", "", str(valor))
    return cnpj if len(cnpj) == 14 else ""

def formatar_cnpj_display(cnpj):
    if len(cnpj) != 14: return cnpj
    return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"

def gerar_links_receita(cnpj):
    cnpj_enc = urllib.parse.quote(cnpj)
    return {
        "Link Consulta Optantes": f"{CONSOPT_URL_BASE}?cnpj={cnpj_enc}",
        "Link PGMEI (Emitir DAS)": f"{PGMEI_URL_BASE}?cnpj={cnpj_enc}",
        "Link DASN-SIMEI": f"{DASN_URL_BASE}?cnpj={cnpj_enc}"
    }

# ============================================================
# MOTOR DE AUDITORIA (BRASILAPI + VALIDAÇÃO)
# ============================================================

def consultar_brasilapi_mei(cnpj_limpo):
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    
    base_resultado = {
        "Status SIMEI": "⚫ NÃO ANALISADO",
        "Detalhes SIMEI": "Erro na consulta",
        "Situação Cadastral": "Indeterminado",
        "Status Consolidado": "⚫ NÃO ANALISADO"
    }

    try:
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            dados = response.json()
            situacao = dados.get("descricao_situacao_cadastral", "").upper()
            base_resultado["Situação Cadastral"] = situacao
            
            optante_simei = dados.get("opcao_pelo_simei")
            data_exclusao = dados.get("data_exclusao_do_simei")
            
            if situacao != "ATIVA":
                base_resultado["Status SIMEI"] = "🔴 CNPJ INATIVO/BAIXADO"
                base_resultado["Detalhes SIMEI"] = f"Situação: {situacao}"
                base_resultado["Status Consolidado"] = "🔴 IRREGULAR"
                
            elif optante_simei is True:
                if data_exclusao:
                    base_resultado["Status SIMEI"] = f"⚠️ EXCLUÍDO EM {data_exclusao}"
                    base_resultado["Detalhes SIMEI"] = "Excluído do SIMEI"
                    base_resultado["Status Consolidado"] = "🔴 IRREGULAR"
                else:
                    base_resultado["Status SIMEI"] = "🟢 OPTANTE SIMEI (Confirmado)"
                    base_resultado["Detalhes SIMEI"] = "Regular na base pública oficial"
                    base_resultado["Status Consolidado"] = "🟢 REGULAR"
            
            elif optante_simei is False:
                base_resultado["Status SIMEI"] = "🔴 NÃO OPTANTE SIMEI"
                base_resultado["Detalhes SIMEI"] = "Empresa não enquadrada como MEI"
                base_resultado["Status Consolidado"] = "🔴 IRREGULAR"
            
            else:
                base_resultado["Status SIMEI"] = "🟡 STATUS DESCONHECIDO"
                base_resultado["Detalhes SIMEI"] = "Verificar manualmente"
                base_resultado["Status Consolidado"] = "🟡 ATENÇÃO"

            return base_resultado

        elif response.status_code == 404:
            base_resultado["Status SIMEI"] = "🔵 CNPJ NÃO LOCALIZADO"
            base_resultado["Detalhes SIMEI"] = "Verificar cadastro"
            base_resultado["Status Consolidado"] = "⚫ NÃO ANALISADO"
            return base_resultado
            
        else:
            base_resultado["Status SIMEI"] = f"🔵 ERRO API ({response.status_code})"
            base_resultado["Detalhes SIMEI"] = "Servidor instável"
            base_resultado["Status Consolidado"] = "⚫ NÃO ANALISADO"
            return base_resultado

    except requests.RequestException as e:
        base_resultado["Status SIMEI"] = "🔵 ERRO DE CONEXÃO"
        base_resultado["Detalhes SIMEI"] = str(e)
        base_resultado["Status Consolidado"] = "⚫ NÃO ANALISADO"
        return base_resultado


def consultar_lista_cnpj(df, coluna_cnpj):
    resultados = []
    total = len(df)
    progresso_bar = st.progress(0)
    
    for i, linha in df.iterrows():
        cnpj_raw = linha[coluna_cnpj]
        nome = linha.get("Razão Social", linha.get("Nome da Empresa", ""))
        
        cnpj_limpo = limpar_cnpj(cnpj_raw)
        
        if not cnpj_limpo:
            resultados.append({
                "CNPJ": str(cnpj_raw),
                "CNPJ Limpo": "",
                "Status SIMEI": "CNPJ INVÁLIDO",
                "Detalhes SIMEI": "Formato incorreto",
                "Situação Cadastral": "Inválido",
                "Status Consolidado": "⚫ NÃO ANALISADO",
                "Link Consulta Optantes": "#",
                "Link PGMEI (Emitir DAS)": "#",
                "Link DASN-SIMEI": "#"
            })
        else:
            dados = consultar_brasilapi_mei(cnpj_limpo)
            links = gerar_links_receita(cnpj_limpo)
            dados.update(links)
            
            final_data = {
                "CNPJ": formatar_cnpj_display(cnpj_limpo),
                "CNPJ Limpo": cnpj_limpo,
                "Nome / Razão Social": nome
            }
            final_data.update(dados)
            
            resultados.append(final_data)
            progresso_bar.progress(int(((i + 1) / total) * 100))
            time.sleep(0.15)
            
    return pd.DataFrame(resultados)


# ============================================================
# CABEÇALHO VISUAL
# ============================================================

st.markdown(
    """
    <div class="main-header">
        <h1>⚖️ MEI MONITOR V2</h1>
        <p>Relatório de Acompanhamento, Regularidade Fiscal e Emissão de Guias</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.write("Bem-vindo ao painel corporativo. Importe sua planilha contendo os CNPJs para realizar a auditoria de enquadramento e gerar os links oficiais de verificação e emissão de DAS.")

# ============================================================
# ENTRADA DE DADOS
# ============================================================

arquivo = st.file_uploader("Importar Planilha de CNPJs (.xlsx ou .xls)", type=["xlsx", "xls"])

if arquivo:
    df = pd.read_excel(arquivo, dtype=str)
    coluna_cnpj = None
    for coluna in df.columns:
        if "cnpj" in str(coluna).lower():
            coluna_cnpj = coluna
            break
            
    if coluna_cnpj is None:
        st.error("⚠️ Não foi encontrada uma coluna contendo a palavra 'CNPJ' na planilha.")
        st.stop()
        
    st.success(f"✅ Coluna de CNPJ identificada com sucesso: **{coluna_cnpj}**")
    
    if st.button("🔎 EXECUTAR AUDITORIA FISCAL EM LOTE", type="primary"):
        with st.spinner("Processando auditoria das empresas..."):
            df_resultado = consultar_lista_cnpj(df, coluna_cnpj)
            st.session_state["df_resultado"] = df_resultado
        st.success("Auditoria concluída com sucesso!")

# ============================================================
# PAINEL CONSOLIDADO & DASHBOARD
# ============================================================

if "df_resultado" in st.session_state:
    dados = st.session_state["df_resultado"]
    st.divider()
    st.subheader("📊 Painel Consolidado de Regularidade")

    total = len(dados)
    regulares = len(dados[dados["Status Consolidado"] == "🟢 REGULAR"])
    irregulares = len(dados[dados["Status Consolidado"] == "🔴 IRREGULAR"])
    nao_analisados = len(dados[dados["Status Consolidado"] == "⚫ NÃO ANALISADO"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total Analisado", total)
    c2.metric("🟢 Regulares (SIMEI)", regulares)
    c3.metric("🔴 Irregulares / Baixados", irregulares)
    c4.metric("⚫ Não Analisados", nao_analisados)

    st.divider()
    st.subheader("📋 Tabela de Empresas & Links Oficiais")
    st.info("💡 **Dica:** No relatório Excel baixado abaixo, você terá os links clicáveis diretos para abrir o PGMEI (emissão de DAS) e a DASN-SIMEI de cada empresa em 1 clique.")

    # Exibe a tabela ocultando os links longos para manter a interface limpa
    cols_to_show = [c for c in dados.columns if "Link" not in c]
    st.dataframe(dados[cols_to_show], width='stretch', hide_index=True)

    st.divider()

    # Botão de Exportação para Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dados.to_excel(writer, index=False, sheet_name="Auditoria_MEI")

    st.download_button(
        "📥 Baixar Relatório Consolidado em Excel (Com Links Diretos)",
        data=output.getvalue(),
        file_name="MEI_Monitor_Relatorio_" + datetime.now().strftime("%Y%m%d_%H%M") + ".xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ============================================================
# RODAPÉ E ATALHOS OFICIAIS
# ============================================================

st.divider()
st.subheader("🔗 Atalhos Oficiais da Receita Federal")
st.markdown(
    f"""
    - [Consulta de Optantes pelo SIMEI (CONSOPT)]({CONSOPT_URL_BASE})
    - [Emissão de Documento de Arrecadação - PGMEI (DAS)]({PGMEI_URL_BASE})
    - [Declaração Anual para o MEI (DASN-SIMEI)]({DASN_URL_BASE})
    """
)
st.caption("MEI Monitor V2 — Desenvolvido para suporte à rotina de Departamento Pessoal e Contábil.")
