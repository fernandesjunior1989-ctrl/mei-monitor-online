import io
import os
import subprocess
import time
import pandas as pd
import streamlit as st

# Garante a instalação do navegador Chromium no servidor Streamlit
@st.cache_resource
def preparar_navegador():
    subprocess.run(["playwright", "install", "chromium"])

preparar_navegador()

from playwright.sync_api import sync_playwright
from twocaptcha import TwoCaptcha

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="centered")

st.title("MEI Monitor — Consulta de DAS e Declarações por CNPJ")
st.write("Envie sua planilha de CNPJs e informe sua chave do 2Captcha para auditar guias em aberto e DASN-SIMEI.")

# Formulário Web
uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])
api_key = st.text_input("Sua Chave API do 2Captcha", type="password")

if st.button("Iniciar Auditoria Completa", type="primary"):
    if not uploaded_file:
        st.error("Envie uma planilha Excel primeiro.")
    elif not api_key:
        st.error("Informe sua chave do 2Captcha para resolver o captcha da Receita.")
    else:
        st.info("Robô iniciado! Realizando consultas no portal PGMEI...")
        
        df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
        
        # Garante as colunas no DataFrame
        for col in ["Status_Consulta", "Situação DAS", "Declaração DASN-SIMEI"]:
            if col not in df.columns:
                df[col] = ""
        
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
                # Trata o CNPJ garantindo 14 dígitos (com zero à esquerda se houver)
                cnpj_limpo = "".join(filter(str.isdigit, str(row["CNPJ"]))).zfill(14)
                if not cnpj_limpo or len(cnpj_limpo) != 14:
                    df.at[idx, "Status_Consulta"] = "CNPJ Inválido"
                    continue

                status_texto.text(f"Consultando MEI {idx + 1} de {total}: {cnpj_limpo}")

                try:
                    # Acessa o Portal PGMEI
                    page.goto("https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/", wait_until="domcontentloaded", timeout=60000)
                    
                    # Preenche o CNPJ
                    page.wait_for_selector("#cnpj, input[name='cnpj']", timeout=15000)
                    page.fill("#cnpj, input[name='cnpj']", cnpj_limpo)

                    # Resolve o reCAPTCHA automaticamente via 2Captcha
                    captcha_elem = page.wait_for_selector("[data-sitekey]", timeout=15000)
                    sitekey = captcha_elem.get_attribute("data-sitekey")

                    res = solver.recaptcha(sitekey=sitekey, url=page.url)
                    token = res["code"]

                    # Insere o token resolvido na página
                    page.evaluate(f"""
                        let el = document.getElementById('g-recaptcha-response') || document.querySelector('[name="g-recaptcha-response"]');
                        if (el) {{ el.value = '{token}'; el.innerHTML = '{token}'; }}
                    """)

                    # Clica para prosseguir
                    page.click("button[type='submit'], input[type='submit'], #btnContinuar")
                    
                    # Aguarda a tela interna de opções do MEI carregar
                    page.wait_for_selector("text=Emitir Guia de Pagamento (DAS), text=Consulta, text=Extrato", timeout=20000)
                    
                    # Captura o texto da página para identificar guias e declarações
                    conteudo_pagina = page.inner_text("body")
                    
                    # Análise básica do conteúdo retornado pelo portal
                    if "pendência" in conteudo_pagina.lower() or "débito" in conteudo_pagina.lower():
                        df.at[idx, "Situação DAS"] = "Possui Guias em Aberto / Pendências"
                    else:
                        df.at[idx, "Situação DAS"] = "Regular (Sem débitos aparentes)"
                        
                    if "declaração" in conteudo_pagina.lower() or "dasn" in conteudo_pagina.lower():
                        df.at[idx, "Declaração DASN-SIMEI"] = "Verificar extrato de declarações"
                    else:
                        df.at[idx, "Declaração DASN-SIMEI"] = "Regular"

                    df.at[idx, "Status_Consulta"] = "Sucesso"

                except Exception as err:
                    df.at[idx, "Status_Consulta"] = f"Erro: {str(err)[:45]}"

                barra_progresso.progress((idx + 1) / total)
                time.sleep(1)

            browser.close()

        status_texto.text("Processamento finalizado!")
        st.success("Todas as consultas de DAS e declarações foram concluídas!")

        # Gera o relatório final para download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Baixar Planilha Completa de Auditoria MEI",
            data=output.getvalue(),
            file_name="resultado_auditoria_completa.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
