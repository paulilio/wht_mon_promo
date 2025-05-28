import json
from datetime import datetime
from tabulate import tabulate
from selenium import webdriver

from mon import comparador
from mon import web_mon
from mon.ml_seguinte import clicar_em_seguinte
from mon.ml_login import verificar_login, aguardar_login

from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Configuração
tolerancia_perc = 10  # % de tolerância
URL_INICIAL = "https://lista.mercadolivre.com.br/informatica/novo/_Desde_49_BRAND_22935733_NoIndex_True"

produtos = [
    ["A1 Combo", "A1 Ams Combo", "mini", 5400],
    ["A1 Combo Mini", "A1 mini ams combo", "", 3900],
    ["A1", "A1 sem", "mini", 3700],
    ["A1 Mini", "A1 mini sem", "", 3300],
    ["P1S Combo", "P1S Combo Ams", "sem", 9500],
    ["P1S", "P1S Sem AMS", "", 6500],
    ["P1P", "P1P", "", 5500],
]

def coletar_todas_paginas(driver, url):
    """
    Navega por todas as páginas clicando em 'Seguinte' e consolida a coleta de produtos.
    """
    todos_produtos = []
    total_paginas = 0

    while True:
        produtos_pagina = web_mon.coletar_produtos(driver, url, n_coletas=1)
        todos_produtos.extend(produtos_pagina)

        continuar, total_paginas = clicar_em_seguinte(
            driver, 
            total_paginas_navegadas=total_paginas, 
            log_tag='run_compara'
        )

        if not continuar:
            break

        url = driver.current_url

    # Deduplicação extra por garantia
    todos_produtos = {
        (p['produto'], p['preco'], p['link']): p for p in todos_produtos
    }.values()

    print(f"[INFO] Total de produtos coletados em todas as páginas: {len(todos_produtos)}")

    return list(todos_produtos)

def main():
    print("[INFO] Iniciando execução...")

    options = Options()
    options.add_argument(r"--user-data-dir=C:\tools\SeleniumProfile")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()), 
        options=options
    )

    try:
        # ✅ Vai diretamente para a URL de coleta
        driver.get(URL_INICIAL)

        # ✅ Verifica e aguarda login na página atual
        if not verificar_login(driver):
            aguardar_login(driver)

        produtos_encontrados = coletar_todas_paginas(driver, URL_INICIAL)

        # Ajuste: transformar preços para float usando menor_valor
        for prod in produtos_encontrados:
            preco_float = comparador.menor_valor(prod['preco'])
            prod['preco'] = preco_float if preco_float is not None else 0.0
            prod['titulo'] = prod['produto']  # compatibilidade com comparador

        resultado = comparador.comparar_produtos(
            produtos, 
            produtos_encontrados, 
            tolerancia_perc
        )

        print("\n[RESULTADO JSON]:")
        print(json.dumps(resultado, indent=4, ensure_ascii=False))

        print("\n[RESULTADO TABELA]:")
        tabela = [
            [item["produto"], item["preco"], item["parcela_18x"]]
            for item in resultado
        ]
        print(tabulate(tabela, headers=["Produto", "Preço", "Parcela (18x)"]))

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        arquivo_saida = f"resultado_{timestamp}.json"
        with open(arquivo_saida, "w", encoding="utf-8") as f:
            json.dump(resultado, f, indent=4, ensure_ascii=False)

        print(f"\n[INFO] Resultado salvo em: {arquivo_saida}")

    finally:
        driver.quit()
        print("[INFO] Navegador fechado após a execução.")

if __name__ == "__main__":
    main()
