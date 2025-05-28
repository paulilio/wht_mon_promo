import sys
import os
import re
from datetime import datetime
import time

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mon import web_mon, comparador, cupons_aplicador
from notify import wht_send
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from common import log, env
from mon.ml_seguinte import clique_pagina_seguinte


# ✅ Lista de comparações: ID, Nome, URL, Enviar Sempre (1/0), Termos
comparacoes = [
    ["001", "Produto P1S", "https://lista.mercadolivre.com.br/informatica/novo/_PriceRange_2100-9100_Installments_YES_BRAND_22935733_NoIndex_True", 0, "p1s"]
]

def contem_termo(nome, termos):
    if not termos:
        return True
    return any(termo.strip().lower() in nome.lower() for termo in termos.split(','))

def gerar_link_curto(link):
    match = re.search(r'/([A-Z]{3}\d{8,})', link)
    if match:
        codigo = match.group(1)
        return f"https://produto.mercadolivre.com.br/{codigo}"
    return link

def get_ultimo_snapshot(pasta_snap, excluir_nome=None):
    arquivos = [f for f in os.listdir(pasta_snap) if f.startswith('coleta_') and f.endswith('.json')]
    if not arquivos:
        return None
    arquivos.sort(reverse=True)
    for arquivo in arquivos:
        if arquivo != excluir_nome:
            return arquivo
    return None

def enviar_mensagem_whatsapp(msg, max_len=4000, delay=2):
    partes = [msg[i:i+max_len] for i in range(0, len(msg), max_len)]
    for idx, parte in enumerate(partes, start=1):
        log.info("whatsapp", f"Enviando parte {idx}/{len(partes)}...")
        sucesso = wht_send.send_whatsapp_message(env.PHONE, env.API_KEY, parte)
        if sucesso:
            log.info("whatsapp", f"Parte {idx} enviada com sucesso.")
        else:
            log.warn("whatsapp", f"Falha ao enviar parte {idx}.")
        time.sleep(delay)

def formatar_produto(produto):
    nome = produto['produto'][:30]
    preco = produto['preco']
    fornecedor = produto['fornecedor'][:15]
    cupom = produto.get('cupom', '').strip()
    link_curto = gerar_link_curto(produto['link'])
    return f"- {nome} | {preco} | {cupom} | {fornecedor} | {link_curto}"

def navegar_e_coletar_paginas(comp_id, driver, coletar_func, comp_url):
    total_paginas_navegadas = 1
    driver.get(comp_url)

    while True:
        log.info(comp_id, f"[Página {total_paginas_navegadas}] Coletando produtos...")
        coletar_func()

        try:
            # Sempre busque novamente o botão "Seguinte"
            link_seguinte = driver.find_element(By.XPATH, "//span[text()='Seguinte']/ancestor::a")

            if not link_seguinte.is_enabled():
                msg = f"🛑 Botão 'Seguinte' está desabilitado. Fim da execução após {total_paginas_navegadas} páginas."
                print(msg)
                log.write_log(comp_id, msg)
                break

            driver.execute_script("arguments[0].scrollIntoView(true);", link_seguinte)
            time.sleep(1)
            msg = f"➡️ Clicando em 'Seguinte' (página {total_paginas_navegadas + 1})..."
            print(msg)
            log.write_log(comp_id, msg)

            link_seguinte.click()
            total_paginas_navegadas += 1

            # ✅ Aguarda até que a nova página carregue completamente
            WebDriverWait(driver, 15).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-search-layout__item"))
            )
            time.sleep(1)

        except NoSuchElementException:
            msg = f"🛑 Botão 'Seguinte' não encontrado (última página). Fim após {total_paginas_navegadas} páginas."
            print(msg)
            log.write_log(comp_id, msg)
            break

        except StaleElementReferenceException:
            msg = "⚠️ Elemento stale após clique. Recarregando página e tentando novamente..."
            print(msg)
            log.write_log(comp_id, msg)
            # Pequeno sleep para garantir estabilidade
            time.sleep(2)
            driver.get(comp_url)
            continue

from mon.ml_seguinte import clique_pagina_seguinte

def processar_comparacao(comp_id, comp_nome, comp_url, enviar_sempre, termos, driver):
    log.info(comp_id, f"Iniciando comparação: {comp_nome}")

    all_produtos = []
    total_paginas_navegadas = 1

    driver.get(comp_url)
    time.sleep(2)

    while True:
        log.info(comp_id, f"[Página {total_paginas_navegadas}] Coletando produtos...")

        produtos = web_mon.coletar_produtos(driver, comp_url, n_coletas=1)

        if produtos:
            all_produtos.extend(produtos)
        else:
            log.warn(comp_id, f"Nenhum produto coletado na página {total_paginas_navegadas}.")

        if not clique_pagina_seguinte(driver, log, comp_id):
            break

        total_paginas_navegadas += 1

    if not all_produtos:
        log.warn(comp_id, f"Nenhum produto coletado para {comp_nome} em todas as páginas. Pulando.")
        return

    pasta_snap = os.path.join(os.path.dirname(__file__), '..', 'snapshots', comp_id)
    os.makedirs(pasta_snap, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo = f'coleta_{timestamp}.json'
    caminho_arquivo = os.path.join(pasta_snap, nome_arquivo)

    comparador.salvar_coleta(all_produtos, caminho_arquivo)

    ultimo = get_ultimo_snapshot(pasta_snap, excluir_nome=nome_arquivo)
    if ultimo:
        ultima_coleta = comparador.carregar_coleta(os.path.join(pasta_snap, ultimo))
        nova_coleta = comparador.carregar_coleta(caminho_arquivo)

        ultima_coleta = comparador.deduplicar_coleta(ultima_coleta)
        nova_coleta = comparador.deduplicar_coleta(nova_coleta)

        antiga_dict = {(p['produto'], p['fornecedor']): p for p in ultima_coleta}
        nova_dict = {(p['produto'], p['fornecedor']): p for p in nova_coleta}

        antigos_keys = set(antiga_dict.keys())
        novos_keys = set(nova_dict.keys())

        novos = novos_keys - antigos_keys
        removidos = antigos_keys - novos_keys
        mantidos = antigos_keys & novos_keys

        alterados = []
        for chave in mantidos:
            prod_antigo = antiga_dict[chave]
            prod_novo = nova_dict[chave]
            if comparador.menor_valor(prod_antigo.get('preco')) != comparador.menor_valor(prod_novo.get('preco')):
                alterados.append(prod_novo)

        msg = f"[{comp_id}] {comp_nome}\n"
        msg += f"🔗 Link monitorado: {comp_url}\n\n"
        msg += f"📊 Monit: IGUA: {len(mantidos)-len(alterados)} | ALTD: {len(alterados)} | NOVO: {len(novos)} | RMVD: {len(removidos)}\n\n"

        enviar = enviar_sempre == 1

        for categoria, chaves in [("🆕 Novos", novos), ("🔄 Alterados", alterados)]:
            filtrados = []
            for item in (nova_dict[ch] if categoria == "🆕 Novos" else item for ch in chaves):
                if contem_termo(item['produto'], termos):
                    filtrados.append(item)
            if filtrados:
                msg += f"{categoria}:\n"
                for produto in filtrados:
                    msg += formatar_produto(produto) + "\n"
                enviar = True

        if enviar:
            enviar_mensagem_whatsapp(msg)
        else:
            log.info(comp_id, "Nenhuma alteração relevante. Não enviando mensagem.")

    else:
        msg = f"[{comp_id}] {comp_nome}\n"
        msg += f"🔗 Link monitorado: {comp_url}\n\n"
        msg += "[INFO] Nenhuma coleta anterior para comparar.\n"
        if enviar_sempre == 1:
            enviar_mensagem_whatsapp(msg)

def main(pegar_cupons=True):
    log.info("run_compara_aviso_multi_v2", "Iniciando execução...")

    options = Options()
    options.add_argument(r"--user-data-dir=C:\tools\SeleniumProfile")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        if pegar_cupons:
            log.info("run_compara_aviso_multi_v2", "Executando aplicação de cupons...")
            cupons_aplicador.aplicar_cupons(driver)
        else:
            log.info("run_compara_aviso_multi_v2", "Pulando aplicação de cupons conforme parâmetro.")

        for comp in comparacoes:
            comp_id, comp_nome, comp_url, enviar_sempre, termos = comp
            processar_comparacao(comp_id, comp_nome, comp_url, enviar_sempre, termos, driver)

    finally:
        driver.quit()
        log.info("run_compara_aviso_multi_v2", "Navegador fechado após todas as comparações.")

if __name__ == "__main__":
    main(pegar_cupons=False)
