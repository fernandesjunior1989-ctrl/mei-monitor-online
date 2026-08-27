import io
import re
import time
import urllib.parse
from datetime import datetime

import pandas as pd
import requests
import streamlit as st

# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="MEI Monitor — Auditoria Gratuita e Links Rápidos",
    page_icon="📊",
    layout="wide"
)

# URLs dos Portais Oficiais (Para os links manuais)
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
    """Gera links com o CNPJ pré-preenchido para consulta manual."""
    cnpj_enc = urllib.parse.quote(cnpj)
    return {
        "Link Consulta Optantes": f"{CONSOPT_URL_BASE}?cnpj={cnpj_enc}",
        "Link PGMEI (DAS)": f"{PGMEI_URL_BASE}?cnpj={cnpj_enc}",
        "Link DASN-SIMEI": f"{DASN_URL_BASE}?cnpj={cnpj_enc}"
    }

# ============================================================
# CONSULTA GRATUITA E LEVE (Via BrasilAPI)
# ============================================================

def consultar_brasilapi_mei(cnpj_limpo):
    """
    Consulta a API pública da BrasilAPI para obter situação do CNPJ e SIMEI.
    Retorna um dicionário com o status interpretado.
    """
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
            
            # Interpretar Situação Cadastral
            situacao = dados.get("descricao_situacao_cadastral", "").upper()
            base_resultado["Situação Cadastral"] = situacao
            
            # Interpretar Optante pelo SIMEI
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
                    base_resultado["Detalhes SIMEI"] = "Empresa regular na base pública"
                    base_resultado["Status Consolidado"] = "🟢 REGULAR"
            
            elif optante_simei is False:
                base_resultado["Status SIMEI"] = "🔴 NÃO OPTANTE SIMEI"
                base_resultado["Detalhes SIMEI"] = "Empresa não é MEI"
                base_resultado["Status Consolidado"] = "🔴 IRREGULAR"
            
            else:
                # Caso o campo da API retorne null ou outro valor inesperado
                base_resultado["Status SIMEI"] = "🟡 STATUS SIMEI DESCONHECIDO"
                base_resultado["Detalhes SIMEI"] = "Verificar manualmente"
                base_resultado["Status Consolidado"] = "🟡 ATENÇÃO"

            return base_resultado

        elif response.status_code == 404:
            base_resultado["Status SIMEI"] = "🔵 CNPJ NÃO LOCALIZADO"
            base_resultado["Detalhes SIMEI"] = "Verificar CNPJ na Receita"
            base_resultado["Status Consolidado"] = "⚫ NÃO ANALISADO"
            return base_resultado
            
        else:
            # Erros 500, 502, etc. da BrasilAPI
            base_resultado["Status SIMEI"] = f"🔵 ERRO NA API ({response.status_code})"
            base_resultado["Detalhes SIMEI"] = "Servidor da BrasilAPI instável"
            base_resultado["Status Consolidado"] = "⚫ NÃO ANALISADO"
            return base_resultado

    except requests.RequestException as e:
        # Erro de conexão (Timeouts, DNS, etc.)
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
                "CNPJ": cnpj_raw,
                "CNPJ Limpo": "",
                "Status SIMEI": "CNPJ INVÁLIDO",
                "Detalhes SIMEI": "Formato incorreto",
                "Situação Cadastral": "Inválido",
                "Status Consolidado": "⚫ NÃO ANALISADO",
                "Link Consulta Optantes": "#",
                "Link PGMEI (DAS)": "#",
                "Link DASN-SIMEI": "#"
            })
        else:
            # Consulta a BrasilAPI (Livre de CAPTCHA)
            dados = consultar_brasilapi_mei(cnpj_limpo)
            
            # Adiciona os links diretos para consulta manual
            links = gerar_links_receita(cnpj_limpo)
            dados.update(links)
            
            # Adiciona CNPJ formatado e nome
            final_data = {
                "CNPJ": formatar_cnpj_display(cnpj_limpo),
                "CNPJ Limpo": cnpj_limpo,
                "Nome / Razão Social": nome
            }
            final_data.update(dados)
            
            resultados.append(final_data)
            progresso_bar.progress(int(((i + 1) / total) * 100))
            
            # Pausa leve para não sobrecarregar a API pública
            time.sleep(0.2)
            
    return pd.DataFrame(resultados)


# ============================================================
# INTERFACE
# ============================================================

st.title("MEI Monitor — Auditoria Gratuita e Links Rápidos")
st.caption("Consultas baseadas em bases públicas (BrasilAPI) e links diretos para os portais oficiais.")
st.warning("Esta versão utiliza auditoria leve e fornece os links para a verificação manual de DAS e DASN nos portais da Receita Federal.")

arquivo = st.file_uploader("Importe a planilha de CNPJs (coluna 'CNPJ')", type=["xlsx", "xls"])

if arquivo:
    df = pd.read_excel(arquivo, dtype=str)
    coluna_cnpj = None
    for coluna in df.columns:
        if "cnpj" in str(coluna).lower():
            coluna_cnpj = coluna
            break
    if coluna_cnpj is None:
        st.error("Não foi encontrada uma coluna contendo CNPJ.")
        st.stop()
    st.success(f"Coluna identificada: {coluna_cnpj}")
    
    # Botão de Execução
    if st.button("🔎 EXECUTAR AUDITORIA LEVE E GERAR LINKS", type="primary"):
        df_resultado = consultar_lista_cnpj(df, coluna_cnpj)
        st.session_state["df_resultado"] = df_resultado
        st.success("Auditoria leve concluída com sucesso!")

# ============================================================
# DASHBOARD
# ============================================================

if "df_resultado" in st.session_state:
    dados = st.session_state["df_resultado"]
    st.divider()
    st.subheader("Painel Consolidado")

    total = len(dados)
    regulares = len(dados[dados["Status Consolidado"] == "🟢 REGULAR"])
    irregulares = len(dados[dados["Status Consolidado"] == "🔴 IRREGULAR"])
    nao_analisados = len(dados[dados["Status Consolidado"] == "⚫ NÃO ANALISADO"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total", total)
    c2.metric("🟢 Regulares", regulares)
    c3.metric("🔴 Irregulares (Inativos/Não MEI)", irregulares)
    c4.metric("⚫ Não analisados (Erros de API)", nao_analisados)

    st.divider()
    st.subheader("Tabela de Resultado com Links")
    st.write("Role para a direita para ver os links de auditoria manual.")
    
    # Exibe o dataframe, mas esconde os links no st.dataframe principal para ficar limpo
    cols_to_show = [c for c in dados.columns if "Link" not in c]
    st.dataframe(dados[cols_to_show], use_container_width=True, hide_index=True)

    st.divider()

    # Exportação para Excel (Com os links)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dados.to_excel(writer, index=False, sheet_name="AuditoriaMEI")

    st.download_button(
        "📥 Baixar relatório Excel (Com Links Diretos p/ Portais Oficiais)",
        data=output.getvalue(),
        file_name="MEI_Auditoria_Gratuita_" + datetime.now().strftime("%Y%m%d_%H%M") + ".xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
