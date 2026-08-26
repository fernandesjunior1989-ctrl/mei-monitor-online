importação io
importação os
subprocesso de importação
tempo de importação
pandas de importação como pd
importação streamlit como st

# Baixa o navegador Chromium no servidor na execução primeira
@st.cache_resource
def prepara_navegador():
    subprocess.run(["dravejante", "instalar", "chromium"])

preparado_navegador()

de playwright.sync_api importação sync_playwright
de twocaptcha importação TwoCaptcha

st.set_page_config(page_title="MEI Monitor Online", page_icon="📊", layout="centrado")

st.title("MEI Monitor — Consulta Web")
st.write("Envie sua de CNPJs para consultar o status das guias no portal PGMEI.")

# Formulário Web
uploaded_file = st.file_uploader("Selecione o arquivo Excel (.xlsx)", type=["xlsx"])
api_key = st.text_input("Sua Chave API do 2Captcha", type="password")

if st.button("Iniciar Processamento", type="primary"):
    se não uploaded_file:
        st.error("Envie uma planilha Excel primeiro.")
    elif não api_key:
        st.error("Informe sua chave do 2Captcha.")
    mais:
        st.info("Robô iniciado! Aguarde o processamento das consultas...")
        
        df = pd.read_excel(uploaded_file, dtype={"CNPJ": str}) (em inglês)
        df["Status_Consulta"] = ""
        
        total = lente(df)
        barra_progresso = st.progress(0)
        status_texto = st.empty() Em inglês
        solver = TwoCaptcha(api_key)Tradução

        com sync_playwright() como p:
            browser = p.chromium.launch(
                headless=Verdadeiro,
                args=["--no-sandbox", "--disable-dev-shm-usage"]
            )
            página = browser.new_page()

            para idx, linha em df.iterrows():
                cnpj_limpo = "..join(filtro(str.isdigit, strow["CNPJ")))
                se não cnpj_limpo:
                    continuar

                status_texto.text(f"Consultando MEI {idx + 1} de {total}: {cnpj_limpo}")

                tentar:
                    page.goto(" https://www8.receita.fazenda.gov.br/SimplesNacional/Aplicacoes/ATSPO/pgmei.app/ ", wait_until="networkidle")
                    page.fill("#cnpj", cnpj_limpo)

                    captcha_elem = page.wait_for_selector("[data-sitekey]", timeout=10000)
                    sitekey = captcha_elem.get_attribute("data-sitekey")

                    res = solver.recaptcha(sitekey=sitekey, url=page.url) (em inglês)
                    token = res["code"]

                    page.evaluate(f"""
                        let el = document.getElementById('g-recaptcha-response') || document.querySelector('[name="g-recaptcha-response"]');
                        if (el) {{ el.value = '{token}'; el.innerHTML = '{token}'; }}
                    """)

                    page.click("button[type='submit']")
                    page.wait_for_selector("text=Emitrita Guia de Pagamento (DAS)", timeout=15000)
                    df.at[idx, "Status_Consulta"] = "Consulta Concluída"

                exceto Exceção como err:
                    df.at[idx, "Status_Consulta"] = f"Erro: {str(err)[:30]}"

                barra_progresso.progress((idx + 1) / total)
                time.sleep(1)

            browser.close()

        status_texto.text("Processamento finalizado!")
        st.success("Todas como foram concluídos consultas!")

        # Gera o download da final
        saída = io.BytesIO()
        com pd.ExcelWriter(output, engine="openpyxl") como escritor:
            df.to_excel(escritor, index=False)
        
        st.download_button(Tradução
            label="📥 Baixar Resultados da Planilha com",
            data=output.getvalue(),
            file_name="resultado_meis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
