import time
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def clique_pagina_seguinte(driver, log, label="ml_seguinte", espera=15, tentativas=3):
    """
    Tenta clicar na palavra 'Seguinte' e garante que houve mudança de conteúdo
    aguardando a lista sumir e reaparecer.
    """

    for tentativa in range(1, tentativas + 1):
        try:
            link_seguinte = driver.find_element(By.XPATH, "//span[text()='Seguinte']/ancestor::a")

            if not link_seguinte.is_enabled():
                msg = "🛑 Botão 'Seguinte' está desabilitado. Fim da execução."
                print(msg)
                log.write_log(label, msg)
                return False

            driver.execute_script("arguments[0].scrollIntoView(true);", link_seguinte)
            time.sleep(1)

            msg = f"➡️ Clicando em 'Seguinte'... (tentativa {tentativa})"
            print(msg)
            log.write_log(label, msg)

            # Pega quantidade de itens atuais
            lista_itens = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")
            qtd_anterior = len(lista_itens)

            driver.execute_script("arguments[0].click();", link_seguinte)

            # Aguarda a lista sumir
            WebDriverWait(driver, espera).until(
                EC.staleness_of(lista_itens[0])
            )

            # Aguarda nova lista aparecer
            WebDriverWait(driver, espera).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-search-layout__item"))
            )

            # Confere se a quantidade de itens mudou
            lista_nova = driver.find_elements(By.CSS_SELECTOR, ".ui-search-layout__item")
            qtd_nova = len(lista_nova)

            msg = f"✅ Avançou para a próxima página: de {qtd_anterior} para {qtd_nova} itens."
            print(msg)
            log.write_log(label, msg)

            return True

        except (StaleElementReferenceException, TimeoutException) as e:
            msg = f"⚠️ Problema na tentativa {tentativa}: {e}. Aguardando e tentando novamente..."
            print(msg)
            log.write_log(label, msg)
            time.sleep(2)

        except NoSuchElementException:
            msg = "🛑 Botão 'Seguinte' não encontrado. Fim da execução."
            print(msg)
            log.write_log(label, msg)
            return False

    msg = "❌ Não foi possível clicar em 'Seguinte' após múltiplas tentativas."
    print(msg)
    log.write_log(label, msg)
    return False
