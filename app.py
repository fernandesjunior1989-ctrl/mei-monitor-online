import io
import re
import time
from datetime import datetime

import pandas as pd
import requests
import streamlit as st
from bs4 import BeautifulSoup


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="MEI Monitor V2",
    page_icon="📊",
    layout="wide"
)

CONSOPT_URL = (
    "[https://consopt.www8.receita.fazenda.gov.br/](https://consopt.www8.receita.fazenda.gov.br/)"
    "consultaoptantes"
)

PGMEI_URL = (
    "[https://www8.receita.fazenda.gov.br/](https://www8.receita.fazenda.gov.br/)"
    "SimplesNacional/Aplicacoes/ATSPO/"
    "pgmei.app/Identificacao"
)

DASN_URL = (
    "[https://www8.receita.fazenda.gov.br/](https://www8.receita.fazenda.gov.br/)"
    "SimplesNacional/Aplicacoes/ATSPO/"
    "dasnsimei.app/Identificacao"
)

TIMEOUT = 20


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def limpar_cnpj(valor):
    """
    Remove caracteres não numéricos e valida o tamanho.
    """
    if pd.isna(valor):
        return ""

    cnpj = re.sub(r"\D", "", str(valor))

    if len(cnpj) != 14:
        return ""

    return cnpj


def formatar_cnpj(cnpj):
    if len(cnpj) != 14:
        return cnpj

    return (
        f"{cnpj[:2]}.{cnpj[2:5]}."
        f"{cnpj[5:8]}/{cnpj}-{cnpj[12:]}"
    )


def agora():
    return datetime.now().strftime("%d/%m/%Y %H:%M:%S")


def classificar_status(simei, das, dasn):

    valores = [
        str(simei).upper(),
        str(das).upper(),
        str(dasn).upper()
    ]

    texto = " ".join(valores)

    if "ERRO" in texto:
        return "🔵 ERRO NA CONSULTA"

    if "REQUER AUTENTICAÇÃO" in texto:
        return "⚫ NÃO ANALISADO"

    if "PENDENTE" in texto or "EM ABERTO" in texto:
        return "🔴 IRREGULAR"

    if (
        "CONFIRMADO" in str(simei).upper()
        and "OK" in str(das).upper()
        and "OK" in str(dasn).upper()
    ):
        return "🟢 REGULAR"

    if "NÃO OPTANTE" in str(simei).upper():
        return "🔴 IRREGULAR"

    return "🟡 ATENÇÃO"


# ============================================================
# CONSULTA OFICIAL — CONSULTA OPTANTES
# ============================================================

def consultar_consopt(cnpj):
    """
    Consulta a página oficial do Simples Nacional.

    IMPORTANTE:
    Não utiliza BrasilAPI como fonte principal.

    A estrutura HTML do portal da Receita pode mudar.
    Por isso a função procura textos relevantes no HTML
    em vez de depender de um único seletor.
    """

    resultado = {
        "status": "⚫ NÃO ANALISADO",
        "detalhes": "",
        "fonte": CONSOPT_URL
    }

    session = requests.Session()

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/151 Safari/537.36"
        )
    }

    try:

        response = session.get(
            CONSOPT_URL,
            headers=headers,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        texto = soup.get_text(
            " ",
            strip=True
        ).upper()

        if "CAPTCHA" in texto:
            resultado["status"] = (
                "🔵 ERRO NA CONSULTA — CAPTCHA"
            )
            resultado["detalhes"] = (
                "A Receita solicitou validação humana."
            )
            return resultado

        if "SIMEI" in texto:

            if (
                "OPTANTE PELO SIMEI" in texto
                or "OPTANTE PELO SIMEI DESDE" in texto
            ):
                resultado["status"] = (
                    "🟢 SIMEI CONFIRMADO"
                )
                resultado["detalhes"] = (
                    "Resultado localizado no portal oficial."
                )

            elif (
                "NÃO OPTANTE PELO SIMEI" in texto
                or "NAO OPTANTE PELO SIMEI" in texto
            ):
                resultado["status"] = (
                    "🔴 NÃO OPTANTE / DESENQUADRADO"
                )
                resultado["detalhes"] = (
                    "Resultado localizado no portal oficial."
                )

            else:
                resultado["status"] = (
                    "🟡 ATENÇÃO — RESULTADO NÃO INTERPRETADO"
                )
                resultado["detalhes"] = (
                    "A página foi acessada, mas "
                    "o resultado precisa ser interpretado."
                )

        else:
            resultado["status"] = (
                "🟡 ATENÇÃO — RESULTADO NÃO LOCALIZADO"
            )

    except requests.RequestException as e:

        resultado["status"] = "🔵 ERRO NA CONSULTA"
        resultado["detalhes"] = str(e)

    return resultado


# ============================================================
# PGMEI
# ============================================================

def consultar_pgmei(cnpj, cpf=None, codigo_acesso=None):
    if not cpf or not codigo_acesso:
        return {
            "status": "⚫ REQUER AUTENTICAÇÃO",
            "detalhes": (
                "Consulta de pendências/extratos requer "
                "acesso ao serviço da Receita."
            ),
            "fonte": PGMEI_URL
        }

    return {
        "status": "🟡 CONSULTA AUTENTICADA PENDENTE",
        "detalhes": (
            "Credenciais informadas. "
            "Conector Playwright deve executar "
            "a consulta no PGMEI oficial."
        ),
        "fonte": PGMEI_URL
    }


# ============================================================
# DASN-SIMEI
# ============================================================

def consultar_dasn(cnpj, cpf=None, codigo_acesso=None):
    if not cpf or not codigo_acesso:
        return {
            "status": "⚫ REQUER AUTENTICAÇÃO",
            "detalhes": (
                "A consulta autenticada da DASN-SIMEI "
                "requer dados de acesso."
            ),
            "fonte": DASN_URL
        }

    return {
        "status": "🟡 CONSULTA AUTENTICADA PENDENTE",
        "detalhes": (
            "Credenciais informadas. "
            "Conector Playwright deve consultar "
            "as declarações no portal oficial."
        ),
        "fonte": DASN_URL
    }


# ============================================================
# CONSULTA COMPLETA
# ============================================================

def consultar_mei(cnpj, cpf=None, codigo_acesso=None):

    cnpj_limpo = limpar_cnpj(cnpj)

    if not cnpj_limpo:

        return {
            "CNPJ": str(cnpj),
            "CNPJ Limpo": "",
            "Status SIMEI": "CNPJ INVÁLIDO",
            "DAS": "NÃO ANALISADO",
            "DASN-SIMEI": "NÃO ANALISADO",
            "Status Consolidado": "⚫ NÃO ANALISADO",
            "Última Consulta": agora()
        }

    consopt = consultar_consopt(cnpj_limpo)

    pgmei = consultar_pgmei(
        cnpj_limpo,
        cpf,
        codigo_acesso
    )

    dasn = consultar_dasn(
        cnpj_limpo,
        cpf,
        codigo_acesso
    )

    status = classificar_status(
        consopt["status"],
        pgmei["status"],
        dasn["status"]
    )

    return {
        "CNPJ": formatar_cnpj(cnpj_limpo),
        "CNPJ Limpo": cnpj_limpo,
        "Status SIMEI": consopt["status"],
        "Detalhes SIMEI": consopt["detalhes"],
        "DAS": pgmei["status"],
        "Detalhes DAS": pgmei["detalhes"],
        "DASN-SIMEI": dasn["status"],
        "Detalhes DASN": dasn["detalhes"],
        "Status Consolidado": status,
        "Última Consulta": agora()
    }


# ============================================================
# INTERFACE
# ============================================================

st.title("MEI Monitor V2 — Consulta e Regularidade")

st.caption("Consultas baseadas nos portais oficiais do Simples Nacional / Receita Federal.")

st.warning("A aplicação nunca marcará DAS ou DASN como regular sem confirmação da fonte oficial.")


# ============================================================
# CREDENCIAIS
# ============================================================

with st.expander("Dados de acesso para consultas autenticadas", expanded=False):
    st.write("Utilize somente credenciais autorizadas pelo responsável pelo CNPJ.")

    cpf_padrao = st.text_input("CPF do responsável", type="password")
    codigo_padrao = st.text_input("Código de acesso", type="password")

    st.info("Esses dados não devem ser armazenados em planilhas de saída.")


# ============================================================
# EXCEL
# ============================================================

arquivo = st.file_uploader("Importe a planilha de CNPJs", type=["xlsx", "xls"])

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

    st.dataframe(df.head(20), use_container_width='stretch')

    if st.button("🔎 CONSULTAR MEIs AGORA", type="primary"):

        resultados = []
        progresso = st.progress(0)
        total = len(df)

        for i, linha in df.iterrows():
            cnpj = linha[coluna_cnpj]
            nome = linha.get("Razão Social", linha.get("Nome da Empresa", ""))

            resultado = consultar_mei(cnpj, cpf_padrao, codigo_padrao)
            resultado["Nome / Razão Social"] = nome
            resultados.append(resultado)

            progresso.progress(int(((i + 1) / total) * 100))
            time.sleep(0.3)

        df_resultado = pd.DataFrame(resultados)
        st.session_state["df_resultado"] = df_resultado
        st.success("Consulta concluída.")


# ============================================================
# DASHBOARD
# ============================================================

if "df_resultado" in st.session_state:

    dados = st.session_state["df_resultado"]

    st.divider()
    st.subheader("Painel Consolidado")

    total = len(dados)
    regulares = len(dados[dados["Status Consolidado"] == "🟢 REGULAR"])
    atencao = len(dados[dados["Status Consolidado"] == "🟡 ATENÇÃO"])
    irregulares = len(dados[dados["Status Consolidado"] == "🔴 IRREGULAR"])
    nao_analisados = len(dados[dados["Status Consolidado"] == "⚫ NÃO ANALISADO"])
    erros = len(dados[dados["Status Consolidado"] == "🔵 ERRO NA CONSULTA"])

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Total", total)
    c2.metric("🟢 Regulares", regulares)
    c3.metric("🟡 Atenção", atencao)
    c4.metric("🔴 Irregulares", irregulares)
    c5.metric("⚫ Não analisados", nao_analisados)
    c6.metric("🔵 Erros", erros)

    st.divider()

    filtro = st.selectbox(
        "Filtrar situação",
        [
            "TODOS",
            "🟢 REGULAR",
            "🟡 ATENÇÃO",
            "🔴 IRREGULAR",
            "⚫ NÃO ANALISADO",
            "🔵 ERRO NA CONSULTA"
        ]
    )

    exibicao = dados.copy()
    if filtro != "TODOS":
        exibicao = exibicao[exibicao["Status Consolidado"] == filtro]

    st.dataframe(exibicao, use_container_width='stretch', hide_index=True)

    st.divider()

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dados.to_excel(writer, index=False, sheet_name="Resultado")

    st.download_button(
        "📥 Baixar relatório Excel",
        data=output.getvalue(),
        file_name="MEI_Monitor_" + datetime.now().strftime("%Y%m%d_%H%M") + ".xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ============================================================
# PORTAIS OFICIAIS
# ============================================================

st.divider()
st.subheader("Portais oficiais")
st.markdown(
    f"""
    - [Consulta Optantes]({CONSOPT_URL})
    - [PGMEI]({PGMEI_URL})
    - [DASN-SIMEI]({DASN_URL})
    """
)
st.caption("Os resultados apresentados devem sempre identificar a fonte, data e hora da última consulta.")
