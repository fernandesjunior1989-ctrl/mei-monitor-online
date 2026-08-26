import io
import os
import subprocess
import time
import pandas as pd
import streamlit as st

# Baixa o navegador Chromium no servidor na primeira execução
@st.cache_resource
def preparar_navegador():
    subprocess.run(["playwright", "install", "chromium"])

preparar_navegador()

from playwright.sync_api import sync_playwright
from twocaptcha import TwoCaptcha

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="centered")

st.title("MEI Monitor — Consulta Web")
st.write("Envie sua planilha de CNPJs para consultar o status das guias no portal PGMEI.")

# Formulário Web
uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])
api_key = st.text_input("Sua Chave API do 2Captcha", type="password")

if st.button("Iniciar Processamento", type="primary"):
    if not uploaded_file:
        st.error("Envie uma planilha Excel primeiro.")
    elif not api_key:
        st.error("Informe sua chave do 2Captcha.")
    else:
        st.info("Robô iniciado! Aguarde o processamento das consultas...")
        
        df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
        df["Status_Consulta"] = ""
        
        total = len(df)
        barra_progresso = st.progress(0)
        status_texto = st.empty()
        solver = TwoCaptcha(api_key)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            page = browser.new_page()

            for idx, row in df.iterrows():
                cnpj_limpo = "".join(filter(str.isdigit, str(row["CNPJ"])))
                if not cnpj_limpo:
                    continue

                status_texto.text(f"Consultando MEI {idx + 1} de {total}: {cnpj_limpo}")

                try:
                    page.goto("https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/", wait_until="networkidle")
                    page.fill("#cnpj", cnpj_limpo)

                    captcha_elem = page.wait_for_selector("[data-sitekey]", timeout=10000)
                    sitekey = captcha_elem.get_attribute("data-sitekey")

                    res = solver.recaptcha(sitekey=sitekey, url=page.url)
                    token = res["code"]

                    page.evaluate(f"""
                        let el = document.getElementById('g-recaptcha-response') || document.querySelector('[name="g-recaptcha-response"]');
                        if (el) {{ el.value = '{token}'; el.innerHTML = '{token}'; }}
                    """)

                    page.click("button[type='submit']")
                    page.wait_for_selector("text=Emitir Guia de Pagamento (DAS)", timeout=15000)
                    df.at[idx, "Status_Consulta"] = "Consulta Concluída"

                except Exception as err:
                    df.at[idx, "Status_Consulta"] = f"Erro: {str(err)[:30]}"

                barra_progresso.progress((idx + 1) / total)
                time.sleep(1)

            browser.close()

        status_texto.text("Processamento finalizado!")
        st.success("Todas as consultas foram concluídas!")

        # Gera o download da planilha final
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Baixar Planilha com Resultados",
            data=output.getvalue(),
            file_name="resultado_meis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
