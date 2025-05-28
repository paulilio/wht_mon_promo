import os
import random
import re
import json
import time
import shutil
import hashlib
import subprocess
from datetime import datetime
from collections import defaultdict

import requests
import pandas as pd
from docx import Document
import pdfkit
from jinja2 import Template

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import NoSuchElementException, StaleElementReferenceException, TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

from mon import cupons_aplicador
from notify import wht_send
from common import log, env

# =================== CONSTANTES ===================

PAGINATION_LABEL = "ml_seguinte"
WAIT_TIME = 15
BASE_DIR = 'snapshots'
IMAGENS_DIR = os.path.join(BASE_DIR, 'images')
os.makedirs(IMAGENS_DIR, exist_ok=True)

CLASSIFICACAO = {
    "A1 Mini": {"combo_keywords": ["mini combo", "mini ams", "mini multicolor"],
                "sem_combo_keywords": ["mini sem ams", "mini sem combo", "pf002", "alta performance"]},
    "A1": {"combo_keywords": ["combo", "ams", "multicolor"],
           "sem_combo_keywords": ["sem ams", "sem combo", "fdm", "pf002", "pf001", "alta performance", "aberta"]},
    "P1S": {"combo_keywords": ["p1s combo", "p1s ams"], "sem_combo_keywords": ["p1s sem ams", "p1s -", "p1s"]},
    "P1P": {"keywords": ["p1p"]},
    "Outros": {"exclusoes": ["filamento", "sistema automático", "suporte", "curso", "brinde"]}
}

IGNORADOS = [
    {"produto": "Impressora 3d Bambu Lab A1 Mini (sem Ams) Cor Branco 127/220v", "preco": 2.499},
    {"produto": "Ams Sistema Automático De Materiais P1s - X1c", "preco": 4650.00},
    {"produto": "Bambu Lab Ams Sa001 Sistema Automático De Materiais P1s X1c", "preco": 4650.00}
]

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

# =================== MAIN ===================

def main():
    import argparse
    parser = argparse.ArgumentParser(description='Mercado Livre Scraper')
    parser.add_argument('--pegar_cupons', action='store_true')
    parser.add_argument('--apenas_cupons', action='store_true')
    parser.add_argument('--nowhats', action='store_true')
    parser.add_argument('--silent', action='store_true')
    parser.add_argument('--url', type=str, default='https://lista.mercadolivre.com.br/informatica/novo/_PriceRange_1200-14100_Installments_YES_BRAND_22935733_NoIndex_True')
    args = parser.parse_args()

    driver = setup_driver(silent=args.silent)
    #aguardar_login(driver)
    try:
        if args.apenas_cupons:
            cupons_aplicador.aplicar_cupons(driver)
            return
        if args.pegar_cupons:
            cupons_aplicador.aplicar_cupons(driver)

        produtos = coletar_produtos(driver, args.url)
        enriquecer_com_vl_desc(driver, produtos)
        caminho_json = salvar_json(produtos, nome_arquivo='mercadolivre_informatica')

        caminho_anterior = os.path.join(BASE_DIR, 'ml_scraper_v2', 'ultimo.json')
        if os.path.exists(caminho_anterior):
            json_atual = carregar_json(caminho_json)
            json_anterior = carregar_json(caminho_anterior)
            msg_comp = comparar_precos(json_atual, json_anterior)
            if not args.nowhats: wht_send.send_whatsapp_message(env.PHONE, env.API_KEY, msg_comp)

        shutil.copy(caminho_json, caminho_anterior)

        #if not args.nowhats: enviar_resumo_whatsapp_tabela(produtos)
        enviar_resumo_whatsapp_classificacoes(produtos)

        caminho_pdf = salvar_pdf(produtos, nome_arquivo='mercadolivre_informatica')
        if caminho_pdf:
            link_pdf = enviar_para_google_drive(caminho_pdf)
            if link_pdf:
                if not args.nowhats: enviar_link_whatsapp(link_pdf)

    finally:
        driver.quit()

# =================== UTILITÁRIOS ===================

def aguardar_login(driver):
    print("[INFO] Verificando se está logado no Mercado Livre...")
    driver.get("https://www.mercadolivre.com.br/")

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "a.nav-header-user-menu-trigger, a#nav-header-menu-switch"))
        )
        print("[OK] Usuário já está logado.")
    except TimeoutException:
        print("🔐 Login não detectado. Por favor, faça login manualmente na janela que foi aberta.")
        while True:
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "a.nav-header-user-menu-trigger, a#nav-header-menu-switch"))
                )
                print("[OK] Login realizado com sucesso.")
                break
            except TimeoutException:
                print("[AGUARDANDO] Ainda não logado... aguarde ou faça o login manualmente.")
                time.sleep(5)

def get_random_user_agent():
    return random.choice(USER_AGENTS)

def log_and_print(message, label='web_mon'):
    print(message)
    log.write_log(label, message)

def extrair_codigo_para_link(link):
    match = re.search(r"(MLB\d+)(?!\d)", link)
    return f"https://www.mercadolivre.com.br/p/{match.group(1)}" if match else ''

def deve_ignorar(titulo, preco):
    return any(item['produto'].lower() == titulo.lower() for item in IGNORADOS)

def classificar_produto(titulo):
    titulo_lower = titulo.lower()

    if 'mini' in titulo_lower:
        regras = CLASSIFICACAO["A1 Mini"]
        if any(kw in titulo_lower for kw in regras["sem_combo_keywords"]):
            return "A1 Mini Sem Combo"
        if any(kw in titulo_lower for kw in regras["combo_keywords"]):
            return "A1 Mini Combo"
        return "A1 Mini"

    for categoria in ["P1P", "P1S", "A1"]:
        regras = CLASSIFICACAO.get(categoria, {})
        if any(kw in titulo_lower for kw in regras.get("sem_combo_keywords", [])):
            return f"{categoria} Sem Combo"
        if any(kw in titulo_lower for kw in regras.get("combo_keywords", [])):
            return f"{categoria} Combo"
        if any(kw in titulo_lower for kw in regras.get("keywords", [])):
            return categoria

    if "a1" in titulo_lower:
        if any(kw in titulo_lower for kw in CLASSIFICACAO["A1"]["sem_combo_keywords"]):
            return "A1 Sem Combo"
        return "A1"

    if any(ex in titulo_lower for ex in CLASSIFICACAO["Outros"]["exclusoes"]):
        return "Outros"

    return "Não Classificado"

# =================== COLETA ===================

def setup_driver(silent=False):
    options = Options()

    # Lista de perfis Chrome disponíveis
    #perfis_dir_base = r"C:\tools\SeleniumProfiles"
    #perfis = [os.path.join(perfis_dir_base, d) for d in os.listdir(perfis_dir_base) if os.path.isdir(os.path.join(perfis_dir_base, d))]
    #perfil_escolhido = random.choice(perfis) if perfis else r"C:\tools\SeleniumProfile"
    perfil_escolhido = r"C:\tools\SeleniumProfile"

    options.add_argument(f"--user-data-dir={perfil_escolhido}")
    print(f"[INFO] Perfil: {perfil_escolhido}")

    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    # Aplica user-agent aleatório
    user_agent = get_random_user_agent()
    print(f"[INFO] User-Agent: {user_agent}")
    options.add_argument(f"user-agent={user_agent}")

    if silent:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    return webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

def find_seguinte_button(driver):
    try:
        link = driver.find_element(By.XPATH, "//span[text()='Seguinte']/ancestor::a")
        return link if link.is_displayed() and link.is_enabled() else None
    except (NoSuchElementException, StaleElementReferenceException):
        return None

def click_next_page(driver):
    for tentativa in range(3):
        link = find_seguinte_button(driver)
        if not link:
            log_and_print("🛑 Botão 'Seguinte' não encontrado.", PAGINATION_LABEL)
            return False
        try:
            driver.execute_script("arguments[0].scrollIntoView(true);", link)
            time.sleep(random.uniform(3, 4))  # Aleatoriza tempo de scroll até o botão
            log_and_print(f"➡️ Clicando em 'Seguinte'... tentativa {tentativa+1}", PAGINATION_LABEL)
            driver.execute_script("arguments[0].click();", link)
            time.sleep(random.uniform(3, 4.5))  # Aguarda carregamento inicial
            WebDriverWait(driver, WAIT_TIME).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-search-layout__item")))
            return True
        except (StaleElementReferenceException, TimeoutException, NoSuchElementException):
            time.sleep(random.uniform(2, 4))
    return False

def wait_for_products(driver):
    try:
        WebDriverWait(driver, WAIT_TIME).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, ".ui-search-layout__item")))
        return True
    except TimeoutException:
        log_and_print("⚠️ Timeout ao esperar itens na página.")
        return False

def parse_products(driver, consolidado):
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    for item in soup.select('.ui-search-layout__item'):
        titulo_tag = item.select_one('.poly-component__title-wrapper .poly-component__title')
        preco_tag = item.select_one('.poly-price__current .andes-money-amount__fraction')
        link_tag = item.select_one('a')
        parcela_tag = item.select_one('.poly-price__installments')
        cupom_tag = item.select_one('.poly-component__coupons .poly-coupons__wrapper .poly-coupons__pill')

        if not all([titulo_tag, preco_tag, link_tag]):
            continue

        titulo = titulo_tag.get_text(strip=True)
        preco_str = preco_tag.get_text(strip=True).replace('.', '').replace(',', '.')
        link = link_tag.get('href')

        possui_18x = False
        valor_parcela = "-"

        if parcela_tag:
            parcela_text = parcela_tag.get_text(strip=True).lower()
            possui_18x = '18x' in parcela_text

            valor_parcela_tag = parcela_tag.select_one('.andes-money-amount .andes-money-amount__fraction')
            if valor_parcela_tag:
                valor_parcela_str = valor_parcela_tag.get_text(strip=True)
                valor_parcela = f"{valor_parcela_str}"

        cupom = "-"
        if cupom_tag:
            match = re.search(r'(\d+%)', cupom_tag.get_text(strip=True))
            if match:
                cupom = match.group(1)

        codigo = "-"
        link_reduzido = link

        title_wrapper = item.select_one('.poly-component__title-wrapper a')
        if title_wrapper:
            href = title_wrapper.get('href', '')
            # Caso 1: wid=MLB...
            match = re.search(r'wid=(MLB\d+)&?', href)
            if not match:
                # Caso 2: p/MLB...
                match = re.search(r'p/(MLB\d+)\?', href)
            if not match:
                # Caso 3: /MLB-123456...
                match = re.search(r'/((MLB-\d+))', href)
            if match:
                codigo = match.group(1)
                if '-' in codigo:
                    link_reduzido = f"https://produto.mercadolivre.com.br/{codigo}"
                else:
                    link_reduzido = f"https://www.mercadolivre.com.br/p/{codigo}"

        try:
            preco = float(preco_str)
            if deve_ignorar(titulo, preco):
                continue
            if titulo not in consolidado or preco < consolidado[titulo]['preco']:
                consolidado[titulo] = {
                    "preco": preco,
                    "classificacao": classificar_produto(titulo),
                    "possui_18x": possui_18x,
                    "valor_parcela": valor_parcela,
                    "cupom": cupom,
                    "codigo": codigo,
                    "link": link,
                    "link_reduzido": link_reduzido
                }
        except ValueError:
            continue
    time.sleep(random.uniform(3.5, 5.0))  # Leve atraso entre produtos


def coletar_produtos(driver, url):
    consolidado = {}
    driver.get(url)
    time.sleep(random.uniform(2.5, 4.5))  # Aguarda após carregamento inicial

    while True:
        time.sleep(random.uniform(2, 4))  # Aguarda antes de processar página
        if not wait_for_products(driver):
            break
        parse_products(driver, consolidado)
        time.sleep(random.uniform(1.5, 3.5))  # Aguarda entre a análise e clique
        if not find_seguinte_button(driver) or not click_next_page(driver):
            break

    log_and_print(f"[INFO] Total produtos coletados: {len(consolidado)}")
    return consolidado

def enriquecer_com_vl_desc(driver, produtos):
    for produto, info in produtos.items():
        if info.get('cupom', '-') == '-':
            produtos[produto]['vl_desc'] = "-"
            continue

        link = info.get('link')
        if not link:
            produtos[produto]['vl_desc'] = "-"
            continue

        try:
            driver.get(link)
            time.sleep(random.uniform(2.5, 4.5))  # Aguarda carregamento da página
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            label = soup.select_one('div.ui-vpp-coupons-awareness label')
            if label:
                vl_desc = label.get_text(strip=True)
            else:
                vl_desc = "-"
            produtos[produto]['vl_desc'] = vl_desc
            print(f"[INFO] vl_desc capturado para: {produto} → {vl_desc}")
        except Exception as e:
            print(f"[ERRO] Falha ao capturar vl_desc para: {produto} → {e}")
            produtos[produto]['vl_desc'] = "-"
        time.sleep(random.uniform(1.5, 3.5))  # Aguarda entre visitas aos produtos

# =================== SALVAMENTO ===================

def salvar_json(produtos, nome_arquivo='resultado'):
    pasta = os.path.join(BASE_DIR, 'ml_scraper_v2')
    os.makedirs(pasta, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    caminho = os.path.join(pasta, f"{nome_arquivo}_{timestamp}.json")
    produtos_ordenados = sorted([{
        "produto": k,
        "menor_preco": v['preco'],
        "classificacao": v['classificacao'],
        "possui_18x": v['possui_18x'],
        "link": v['link'],
        "link_reduzido": v['link_reduzido']
    } for k, v in produtos.items()], key=lambda x: (x['produto'], x['menor_preco']))
    with open(caminho, 'w', encoding='utf-8') as f:
        json.dump(produtos_ordenados, f, ensure_ascii=False, indent=4)
    print(f"Arquivo JSON salvo em: {caminho}")
    return caminho

def salvar_html(produtos, nome_arquivo='resultado'):
    from jinja2 import Template
    pasta = os.path.join(BASE_DIR, 'ml_scraper_v2')
    os.makedirs(pasta, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    caminho = os.path.join(pasta, f"{nome_arquivo}_{timestamp}.html")

    agrupado = defaultdict(list)
    for produto, info in produtos.items():
        valor_parcela_str = str(info.get('valor_parcela', '0.00')).replace('R$', '').replace(',', '.').strip()
        try:
            valor_parcela_num = float(valor_parcela_str)
        except ValueError:
            valor_parcela_num = 0.0

        agrupado[info.get('classificacao', 'Não Classificado')].append({
            "Produto": produto,
            "Código": info.get('codigo', '-'),
            "Menor Preço": f"{info.get('preco', 0):.2f}",
            "Valor Parcela": info.get('valor_parcela', '-'),
            "Valor Parcela Num": valor_parcela_num,
            "Desc.": info.get('cupom', '-'),
            "VL Desc": info.get('vl_desc', '-'),
            "Possui 18x": 'Sim' if info.get('possui_18x', False) else 'Não',
            "Link": f'<a href="{info.get("link", "#")}" target="_blank">Ver Produto</a>'
        })

    tabelas_html = ""
    for classe, itens in agrupado.items():
        if not itens:
            continue
        df = pd.DataFrame(itens)
        if 'Valor Parcela Num' in df.columns:
            df = df.sort_values(by=["Valor Parcela Num", "Produto"])
            df = df.drop(columns=["Valor Parcela Num"])
        else:
            df = df.sort_values(by=["Produto"])
        tabela_html = df.to_html(escape=False, index=False)
        tabelas_html += f"<h2>{classe}</h2>{tabela_html}"

    if not tabelas_html:
        tabelas_html = "<p>Nenhum produto encontrado.</p>"

    template = Template("""
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Resumo Mercado Livre</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 20px; }
            table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
            th, td { border: 1px solid #ddd; padding: 8px; }
            th { background-color: #f2f2f2; }
        </style>
    </head>
    <body>
        <h1>Tabelas por Classificação</h1>
        {{ tabelas | safe }}
    </body>
    </html>
    """)

    html_content = template.render(tabelas=tabelas_html)
    with open(caminho, 'w', encoding='utf-8') as f:
        f.write(html_content)

    print(f"Arquivo HTML salvo em: {caminho}")
    return caminho

def salvar_pdf(produtos, nome_arquivo='resultado'):
    caminho_html = salvar_html(produtos, nome_arquivo)
    caminho_pdf = caminho_html.replace('.html', '.pdf')
    try:
        pdfkit.from_file(caminho_html, caminho_pdf, options={'enable-local-file-access': ''})
        print(f"Arquivo PDF salvo em: {caminho_pdf}")
        return caminho_pdf
    except Exception as e:
        print(f"Erro ao gerar PDF: {e}")
        return None

# =================== COMUNICAÇÃO ===================

def enviar_para_google_drive(caminho_local, pasta_remota='WHTAutomacao'):
    nome_arquivo = os.path.basename(caminho_local)
    destino = f"{pasta_remota}:{nome_arquivo}"
    try:
        subprocess.run(["rclone", "copy", caminho_local, f"{pasta_remota}:"], check=True)
        resultado = subprocess.run(["rclone", "link", destino], capture_output=True, text=True, check=True)
        link_publico = resultado.stdout.strip()
        print(f"Link público: {link_publico}")
        return link_publico
    except subprocess.CalledProcessError as e:
        print(f"Erro ao enviar ou gerar link: {e}")
        return None

def enviar_link_whatsapp(link_arquivo):
    message = f"ML Scrapping realizado. Resultado: {link_arquivo}"
    wht_send.send_whatsapp_message(env.PHONE, env.API_KEY, message)

def enviar_resumo_whatsapp_tabela(produtos):
    resumo = defaultdict(list)
    for produto, info in produtos.items():
        resumo[info.get('classificacao', 'Não Classificado')].append({
            'produto': produto,
            'preco': info.get('preco', 0),
            'link_reduzido': info.get('link_reduzido', '#')
        })

    classes_desejadas = {"P1P", "P1S Sem Combo"}

    mensagens = []

    for classe in sorted(resumo.keys()):
        if classe not in classes_desejadas:
            continue
        mensagens.append("--------------")
        itens_ordenados = sorted(resumo[classe], key=lambda x: x['preco'])
        top3 = itens_ordenados[:3]
        for item in top3:
            preco = f"R$ {item['preco']:.2f}"
            link = item['link_reduzido']
            mensagens.append(f"{classe} {preco} {link}")

    mensagem_final = "\n".join(mensagens)

    wht_send.send_whatsapp_message(env.PHONE, env.API_KEY, mensagem_final)
    print("[INFO] Resumo filtrado com top 3 menores preços enviado via WhatsApp.")

def enviar_resumo_whatsapp_classificacoes(produtos, novos_produtos=None):
    resumo = defaultdict(list)
    novos_set = set(novos_produtos) if novos_produtos else set()

    for produto, info in produtos.items():
        resumo[info.get('classificacao', 'Não Classificado')].append({
            'produto': produto,
            'cupom': info.get('cupom', '-')
        })

    mensagens = []

    for classe in sorted(resumo.keys()):
        total = len(resumo[classe])
        novos_count = sum(1 for item in resumo[classe] if item['produto'] in novos_set)
        desconto_count = sum(1 for item in resumo[classe] if item.get('cupom', '-') != '-')
        mensagem = f"{classe}: {total} encontrados. {novos_count} novos. {desconto_count} com desconto."
        mensagens.append(mensagem)

    mensagem_final = "\n".join(mensagens)

    wht_send.send_whatsapp_message(env.PHONE, env.API_KEY, mensagem_final)
    print("[INFO] Resumo geral enviado via WhatsApp.")

# =================== COMPARAÇÃO ===================

def carregar_json(caminho_json):
    with open(caminho_json, 'r', encoding='utf-8') as f:
        return json.load(f)

def comparar_precos(json_atual, json_anterior):
    atual = defaultdict(list)
    anterior = defaultdict(list)
    mensagem = ""
    for item in json_atual:
        atual[item['classificacao']].append(item)
    for item in json_anterior:
        anterior[item['classificacao']].append(item)
    for classificacao in atual:
        if classificacao not in anterior:
            continue
        menor_atual = min(atual[classificacao], key=lambda x: x['menor_preco'])
        menor_anterior = min(anterior[classificacao], key=lambda x: x['menor_preco'])
        if menor_atual['menor_preco'] < menor_anterior['menor_preco']:
            mensagem = f"🔻 Queda de preço!\n{classificacao}: {menor_atual['produto']}\nNovo: {menor_atual['menor_preco']:.2f}\n{menor_atual['link_reduzido']}"
    return mensagem

if __name__ == '__main__':
    main()
