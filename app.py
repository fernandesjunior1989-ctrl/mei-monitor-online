import io
import os
import subprocess
import time
import pandas as pd
import streamlit as st

# Tenta garantir a instalação do binário do navegador na primeira execução em nuvem
try:
    import playwright
    subprocess.run(["playwright", "install", "chromium"], capture_output=True)
except Exception:
    pass

from playwright.sync_api import sync_playwright
from twocaptcha import TwoCaptcha

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="wide")

st.title("MEI Monitor — Consulta Automatizada de DAS, DASN-SIMEI e CNPJ")
st.write("Envie sua planilha contendo os CNPJs e informe sua chave do 2Captcha para realizar a varredura automática.")

uploaded_file = st.file_uploader("Selecione a planilha de CNPJs (.xlsx)", type=["xlsx"])
api_key = st.text_input("Chave API do 2Captcha", type="password")

if st.button("Iniciar Varredura Automatizada", type="primary"):
    if not uploaded_file:
        st.error("Envie uma planilha Excel com os CNPJs.")
    elif not api_key:
        st.error("Informe a chave do 2Captcha para contornar o captcha do portal.")
    else:
        st.info("Iniciando robô de automação no portal do Simples Nacional...")
        
        df = pd.read_excel(uploaded_file, dtype={"CNPJ": str})
        
        # Garante as colunas de resposta
        colunas_retorno = ["Status Execução", "Situação do CNPJ", "Situação das DAS (Aberto/Em dia)", "DASN-SIMEI (Entregue/Pendente)"]
        for col in colunas_retorno:
            if col not in df.columns:
                df[col] = ""

        total = len(df)
        barra_progresso = st.progress(0)
        status_texto = st.empty()
        solver = TwoCaptcha(api_key)

        with sync_playwright() as p:
            # Inicializa o navegador em modo headless otimizado para servidores
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            page = browser.new_page()

            for idx, row in df.iterrows():
                cnpj_limpo = "".join(filter(str.isdigit, str(row.get("CNPJ", "")))).zfill(14)
                
                if len(cnpj_limpo) != 14:
                    df.at[idx, "Status Execução"] = "CNPJ Inválido"
                    continue

                status_texto.text(f"Consultando CNPJ {idx + 1} de {total}: {cnpj_limpo}")

                try:
                    # Acessa o portal PGMEI oficial
                    page.goto("https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/", wait_until="domcontentloaded", timeout=60000)
                    
                    # Preenche o CNPJ
                    page.wait_for_selector("#cnpj, input[name='cnpj']", timeout=15000)
                    page.fill("#cnpj, input[name='cnpj']", cnpj_limpo)

                    # Resolução automática do reCAPTCHA via 2Captcha
                    captcha_elem = page.wait_for_selector("[data-sitekey]", timeout=15000)
                    sitekey = captcha_elem.get_attribute("data-sitekey")

                    res = solver.recaptcha(sitekey=sitekey, url=page.url)
                    token = res["code"]

                    # Injeta o token do captcha na página
                    page.evaluate(f"""
                        let el = document.getElementById('g-recaptcha-response') || document.querySelector('[name="g-recaptcha-response"]');
                        if (el) {{ el.value = '{token}'; el.innerHTML = '{token}'; }}
                    """)

                    # Avança na consulta
                    page.click("button[type='submit'], input[type='submit'], #btnContinuar")
                    
                    # Aguarda carregar o painel interno do CNPJ
                    page.wait_for_selector("text=Emitir Guia de Pagamento (DAS), text=Consulta, text=Extrato", timeout=20000)
                    
                    conteudo_pagina = page.inner_text("body").lower()
                    
                    # Extração automática dos estados solicitados
                    df.at[idx, "Situação do CNPJ"] = "Ativo / Regular" if "ativo" in conteudo_pagina or "emitir guia" in conteudo_pagina else "Verificar Situação"
                    
                    if "débito" in conteudo_pagina or "pendência" in conteudo_pagina or "em aberto" in conteudo_pagina:
                        df.at[idx, "Situação das DAS (Aberto/Em dia)"] = "⚠️ Possui DAS em Aberto / Pendências"
                    else:
                        df.at[idx, "Situação das DAS (Aberto/Em dia)"] = "Em dia (Sem débitos aparentes)"
                        
                    if "dasn" in conteudo_pagina and ("pendente" in conteudo_pagina or "em falta" in conteudo_pagina):
                        df.at[idx, "DASN-SIMEI (Entregue/Pendente)"] = "⚠️ DASN-SIMEI Pendente"
                    else:
                        df.at[idx, "DASN-SIMEI (Entregue/Pendente)"] = "Regular / Entregue"

                    df.at[idx, "Status Execução"] = "Sucesso"

                except Exception as err:
                    df.at[idx, "Status Execução"] = f"Erro na automação: {str(err)[:40]}"

                barra_progresso.progress((idx + 1) / total)
                time.sleep(1)

            browser.close()

        status_texto.text("Varredura automatizada concluída!")
        st.success("Todas as consultas de DAS, DASN-SIMEI e situação foram finalizadas!")

        # Disponibiliza o relatório em Excel para download
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Baixar Relatório Automatizado Completo (.xlsx)",
            data=output.getvalue(),
            file_name="resultado_automacao_mei.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
