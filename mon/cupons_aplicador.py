from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    ElementNotInteractableException,
    NoSuchElementException,
)
from time import sleep, time
from common import log

def aplicar_cupons(driver, url="https://www.mercadolivre.com.br/cupons/filter?status=inactive&source_page=int_applied_filters"):
    """
    Aplica cupons automaticamente navegando pelas páginas e clicando nos botões.
    """
    driver.get(url)
    sleep(2)

    if "Entre" in driver.page_source or "Login" in driver.title:
        msg = "🟡 Parece que você não está logado. Faça login e pressione ENTER para continuar..."
        print(msg)
        log.write_log('cupons_aplicador', msg)
        input(msg)

    inicio = time()
    total_botoes_clicados = 0
    total_paginas_navegadas = 1  # já estamos na primeira página

    def aplicar_cupons_na_pagina():
        nonlocal total_botoes_clicados

        last_height = driver.execute_script("return document.body.scrollHeight")
        while True:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            sleep(2)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        botoes = driver.find_elements(By.XPATH, "//*[contains(text(),'Aplicar') and (self::button or self::a or self::span)]")
        msg = f"🔍 Encontrados {len(botoes)} botões com texto 'Aplicar'."
        print(msg)
        log.write_log('cupons_aplicador', msg)

        for i, botao in enumerate(botoes, start=1):
            try:
                driver.execute_script("arguments[0].scrollIntoView(true);", botao)
                sleep(1)
                try:
                    botao.click()
                except ElementNotInteractableException:
                    msg = f"⚠️ Botão {i} não clicável diretamente. Tentando via JavaScript..."
                    print(msg)
                    log.write_log('cupons_aplicador', msg)
                    try:
                        driver.execute_script("arguments[0].click();", botao)
                    except Exception as js_e:
                        msg = f"❌ Mesmo via JS, botão {i} não pôde ser clicado: {js_e}"
                        print(msg)
                        log.write_log('cupons_aplicador', msg)
                        continue
                msg = f"✅ Botão {i} clicado com sucesso."
                print(msg)
                log.write_log('cupons_aplicador', msg)
                sleep(2)
                total_botoes_clicados += 1
            except Exception as e:
                msg = f"❌ Erro inesperado no botão {i}: {e}"
                print(msg)
                log.write_log('cupons_aplicador', msg)

    while True:
        aplicar_cupons_na_pagina()

        try:
            link_seguinte = driver.find_element(By.XPATH, "//span[text()='Seguinte']/ancestor::a")
            if not link_seguinte.is_enabled():
                msg = "🛑 Botão 'Seguinte' está desabilitado. Fim da execução."
                print(msg)
                log.write_log('cupons_aplicador', msg)
                break
            driver.execute_script("arguments[0].scrollIntoView(true);", link_seguinte)
            sleep(1)
            msg = f"➡️ Clicando em 'Seguinte' (página {total_paginas_navegadas + 1})..."
            print(msg)
            log.write_log('cupons_aplicador', msg)
            link_seguinte.click()
            total_paginas_navegadas += 1
            sleep(2)
        except NoSuchElementException:
            msg = "🛑 Botão 'Seguinte' não encontrado (última página). Fim da execução."
            print(msg)
            log.write_log('cupons_aplicador', msg)
            break

    fim = time()
    duracao = fim - inicio

    resumo = (
        "\n📊 Resumo da execução:\n"
        f"➡️ Total de páginas navegadas: {total_paginas_navegadas}\n"
        f"✅ Total de botões 'Aplicar' clicados: {total_botoes_clicados}\n"
        f"⏱️ Tempo total de execução: {duracao:.2f} segundos\n"
    )
    print(resumo)
    log.write_log('cupons_aplicador', resumo)
