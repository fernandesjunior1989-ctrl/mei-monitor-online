import io
import re
import time
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIGURAÇÃO DA PÁGINA & IDENTIDADE VISUAL (CLÁSSICO & REALISTA)
# ============================================================

st.set_page_config(
    page_title="MEI Monitor V2 — Automação Fiscal",
    page_icon="⚖️",
    layout="wide"
)

# Injeção de CSS Customizado (Tema Clássico / Bordô & Dourado Realista)
st.markdown(
    """
    <style>
    .stApp {
        background-color: #F9F8F6;
        color: #2C2C2C;
        font-family: 'Georgia', serif;
    }
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
    </style>
    """,
    unsafe_allow_html=True
)

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

def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")

# ============================================================
# MOTOR DE CONSULTA AUTOMATIZADA EM LOTE (BACKEND)
# ============================================================

def consultar_cnpj_automatico(cnpj_limpo):
    """
    Executa a consulta automatizada na base oficial integrada via API de alta performance,
    retornando o enquadramento SIMEI e Situação Cadastral em tempo real.
    """
    url = f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}"
    
    resultado = {
        "Status SIMEI": "⚫ NÃO ANALISADO",
        "Detalhes SIMEI": "",
        "Situação Cadastral": "Indeterminado",
        "Status Consolidado": "⚫ NÃO ANALISADO"
    }

    try:
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            dados = response.json()
            situacao = dados.get("descricao_situacao_cadastral", "").upper()
            resultado["Situação Cadastral"] = situacao
            
            optante_simei = dados.get("opcao_pelo_simei")
            data_exclusao = dados.get("data_exclusao_do_simei")
            
            if situacao != "ATIVA":
                resultado["Status SIMEI"] = "🔴 CNPJ INATIVO / BAIXADO"
                resultado["Detalhes SIMEI"] = f"Situação cadastral: {situacao}"
                resultado["Status Consolidado"] = "🔴 IRREGULAR"
                
            elif optante_simei is True:
                if data_exclusao:
                    resultado["Status SIMEI"] = f"⚠️ EXCLUÍDO EM {data_exclusao}"
                    resultado["Detalhes SIMEI"] = "Empresa com exclusão registrada no SIMEI"
                    resultado["Status Consolidado"] = "🔴 IRREGULAR"
                else:
                    resultado["Status SIMEI"] = "🟢 OPTANTE SIMEI (Ativo)"
                    resultado["Detalhes SIMEI"] = "Enquadramento MEI confirmado na base oficial"
                    resultado["Status Consolidado"] = "🟢 REGULAR"
            
            elif optante_simei is False:
                resultado["Status SIMEI"] = "🔴 NÃO OPTANTE SIMEI"
                resultado["Detalhes SIMEI"] = "A empresa não está enquadrada como MEI"
                resultado["Status Consolidado"] = "🔴 IRREGULAR"
            
            else:
                resultado["Status SIMEI"] = "🟡 SITUAÇÃO INDEFINIDA"
                resultado["Detalhes SIMEI"] = "Requer verificação complementar"
                resultado["Status Consolidado"] = "🟡 ATENÇÃO"

            return resultado

        elif response.status_code == 404:
            resultado["Status SIMEI"] = "🔵 CNPJ NÃO LOCALIZADO"
            resultado["Detalhes SIMEI"] = "Verifique o número digitado"
            resultado["Status Consolidado"] = "⚫ NÃO ANALISADO"
            return resultado
            
        else:
            resultado["Status SIMEI"] = f"🔵 ERRO NA CONSULTA ({response.status_code})"
            resultado["Detalhes SIMEI"] = "Servidor instável temporariamente"
            resultado["Status Consolidado"] = "⚫ NÃO ANALISADO"
            return resultado

    except requests.RequestException as e:
        resultado["Status SIMEI"] = "🔵 ERRO DE CONEXÃO"
        resultado["Detalhes SIMEI"] = str(e)
        resultado["Status Consolidado"] = "⚫ NÃO ANALISADO"
        return resultado


def processar_lote_automatico(df, coluna_cnpj):
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
                "Nome / Razão Social": nome,
                "Status SIMEI": "CNPJ INVÁLIDO",
                "Detalhes SIMEI": "Formato de CNPJ incorreto",
                "Situação Cadastral": "Inválido",
                "Status Consolidado": "⚫ NÃO ANALISADO",
                "Última Consulta": agora()
            })
        else:
            dados_consulta = consultar_cnpj_automatico(cnpj_limpo)
            
            registro = {
                "CNPJ": formatar_cnpj_display(cnpj_limpo),
                "CNPJ Limpo": cnpj_limpo,
                "Nome / Razão Social": nome,
            }
            registro.update(dados_consulta)
            registro["Última Consulta"] = agora()
            
            resultados.append(registro)
            progresso_bar.progress(int(((i + 1) / total) * 100))
            time.sleep(0.1)
            
    return pd.DataFrame(resultados)


# ============================================================
# CABEÇALHO VISUAL
# ============================================================

st.markdown(
    """
    <div class="main-header">
        <h1>⚖️ MEI MONITOR V2</h1>
        <p>Painel Automatizado de Auditoria e Regularidade Fiscal</p>
    </div>
    """,
    unsafe_allow_html=True
)

st.write("Importe sua planilha contendo os CNPJs para que o sistema execute as consultas automatizadas em lote de forma instantânea e segura.")

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
    
    if st.button("🔎 EXECUTAR CONSULTAS AUTOMATIZADAS EM LOTE", type="primary"):
        with st.spinner("Executando varredura automatizada das empresas..."):
            df_resultado = processar_lote_automatico(df, coluna_cnpj)
            st.session_state["df_resultado"] = df_resultado
        st.success("Consultas automatizadas concluídas com sucesso!")

# ============================================================
# PAINEL CONSOLIDADO & DASHBOARD
# ============================================================

if "df_resultado" in st.session_state:
    dados = st.session_state["df_resultado"]
    st.divider()
    st.subheader("📊 Painel Consolidado da Automação")

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
    st.subheader("📋 Resultados Detalhados da Auditoria")
    
    st.dataframe(dados, width='stretch', hide_index=True)

    st.divider()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dados.to_excel(writer, index=False, sheet_name="Auditoria_Automatizada_MEI")

    st.download_button(
        "📥 Baixar Relatório Completo em Excel",
        data=output.getvalue(),
        file_name="MEI_Monitor_Automacao_" + datetime.now().strftime("%Y%m%d_%H%M") + ".xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# ============================================================
# RODAPÉ
# ============================================================

st.divider()
st.caption("MEI Monitor V2 — Módulo de Automação de Processos Contábeis.")
