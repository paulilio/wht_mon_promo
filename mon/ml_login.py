from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from time import sleep
from common import log

def verificar_login(driver, log_tag='ml_login'):
    """
    Verifica se o usuário está logado no Mercado Livre na página atual.

    Args:
        driver: Instância do Selenium WebDriver.
        log_tag: Tag para log.

    Returns:
        True se logado, False caso contrário.
    """
    try:
        # ✅ Tenta localizar um elemento típico de usuário logado
        driver.find_element(By.XPATH, "//a[contains(@href, 'logout')]")
        msg = "✅ Usuário já está logado no Mercado Livre."
        print(msg)
        log.write_log(log_tag, msg)
        return True
    except NoSuchElementException:
        msg = "⚠️ Usuário NÃO está logado no Mercado Livre."
        print(msg)
        log.write_log(log_tag, msg)
        return False

def aguardar_login(driver, timeout=300, log_tag='ml_login'):
    """
    Aguarda até que o usuário faça login no Mercado Livre na página atual.

    Args:
        driver: Instância do Selenium WebDriver.
        timeout: Tempo máximo de espera em segundos.
        log_tag: Tag para log.
    """
    tempo_esperado = 0
    intervalo = 5

    log.write_log(log_tag, f"⏳ Aguardando login no Mercado Livre por até {timeout} segundos...")

    while tempo_esperado < timeout:
        if verificar_login(driver, log_tag):
            msg = f"✅ Login detectado após {tempo_esperado} segundos."
            print(msg)
            log.write_log(log_tag, msg)
            return
        sleep(intervalo)
        tempo_esperado += intervalo

    msg = f"❌ Tempo esgotado ({timeout}s). Login não detectado."
    print(msg)
    log.write_log(log_tag, msg)
    raise TimeoutError("Login no Mercado Livre não detectado dentro do tempo limite.")
