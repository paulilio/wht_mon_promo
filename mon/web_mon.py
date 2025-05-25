from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
from common import log

def coletar_produtos(driver, url, n_coletas=3):
    """
    Coleta produtos de uma página utilizando um driver Selenium já aberto.

    Args:
        driver: Instância de webdriver.
        url: URL da página para coleta.
        n_coletas: Número de repetições da coleta para consolidar resultados.

    Returns:
        Lista consolidada de produtos únicos.
    """
    consolidado = []
    conjunto_unico = set()

    for i in range(n_coletas):
        msg = f"[INFO] Coleta {i+1}/{n_coletas} - {url}"
        print(msg)
        log.write_log('web_mon', msg)

        driver.get(url)
        time.sleep(3)

        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-search-layout__item"))
        )

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        for item in soup.select('.ui-search-layout__item'):
            titulo_tag = item.select_one('.poly-component__title-wrapper .poly-component__title')
            preco_tag = item.select_one('.poly-price__current .andes-money-amount__fraction')
            desconto_tag = item.select_one('.andes-money-amount__discount')
            cupom_tag = item.select_one('.poly-component__coupons')
            fornecedor_tag = item.select_one('.poly-component__seller')
            link_tag = item.select_one('.poly-component__title-wrapper a')

            if not titulo_tag or not preco_tag or not link_tag:
                continue

            titulo = titulo_tag.get_text(strip=True)
            preco = f"R$ {preco_tag.get_text(strip=True)}"
            desconto = desconto_tag.get_text(strip=True) if desconto_tag else ""
            cupom = cupom_tag.get_text(strip=True) if cupom_tag else ""
            fornecedor = fornecedor_tag.get_text(strip=True) if fornecedor_tag else "Sem fornecedor"
            link = link_tag['href']

            chave = (titulo, preco, link, cupom)

            if chave not in conjunto_unico:
                conjunto_unico.add(chave)
                consolidado.append({
                    'produto': titulo,
                    'preco': preco,
                    'cupom': cupom or desconto,
                    'fornecedor': fornecedor,
                    'link': link
                })

    msg = f"[INFO] Total produtos coletados: {len(consolidado)}"
    print(msg)
    log.write_log('web_mon', msg)

    return consolidado
