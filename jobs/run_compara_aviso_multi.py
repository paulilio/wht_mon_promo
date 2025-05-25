import sys, os, re, time
from datetime import datetime
from common import env
from common import log

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from mon import web_mon, comparador, cupons_aplicador
from notify import wht_send
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

comparacoes = [
    ["001", "Cupom 10%", "https://lista.mercadolivre.com.br/informatica/impressao/impressao-3d/_OrderId_PRICE*DESC_PriceRange_0-10000_Container_ce-3p-achadinhos_NoIndex_True", 0, "a1,p1p,p1s"],
    ["002", "BambuLab", "https://lista.mercadolivre.com.br/informatica/novo/_PriceRange_2100-8100_Installments_NoInterest_BestSellers_YES_BRAND_22935733_NoIndex_True", 0, "a1,p1p,p1a"],
    ["003", "NovBambu", "https://lista.mercadolivre.com.br/informatica/novo/_PublishedToday_YES_BRAND_22935733_NoIndex_True", 0, "a1,p1p,p1s"]
]

def contem_termo(nome, termos):
    if not termos:
        return True  # ✅ Se não há termos → sempre inclui
    for termo in termos.split(','):
        if termo.strip().lower() in nome.lower():
            return True
    return False

def gerar_link_curto(link):
    """
    Extrai o código MLB e gera link curto do Mercado Livre.
    """
    match = re.search(r'/([A-Z]{3}\d{8,})', link)
    if match:
        codigo = match.group(1)
        return f"https://produto.mercadolivre.com.br/{codigo}"
    return link  # Se não achar, retorna o link original

def get_ultimo_snapshot(pasta_snap, excluir_nome=None):
    arquivos = [f for f in os.listdir(pasta_snap) if f.startswith('coleta_') and f.endswith('.json')]
    if not arquivos:
        return None
    arquivos.sort(reverse=True)
    for arquivo in arquivos:
        if arquivo != excluir_nome:
            return arquivo
    return None

def enviar_mensagem_whatsapp(msg, phone, api_key, max_len=4000, delay=2):
    partes = [msg[i:i+max_len] for i in range(0, len(msg), max_len)]
    print(f"[INFO] Mensagem será enviada em {len(partes)} parte(s).")
    for idx, parte in enumerate(partes, start=1):
        print(f"[INFO] Enviando parte {idx}/{len(partes)}...")
        sucesso = wht_send.send_whatsapp_message(phone, api_key, parte)
        if sucesso:
            print(f"[INFO] Parte {idx} enviada com sucesso.")
        else:
            print(f"[ERRO] Falha ao enviar parte {idx}.")
        time.sleep(delay)

def formatar_produto(produto):
    nome = produto['produto'][:30]
    preco = produto['preco']
    fornecedor = produto['fornecedor'][:15]
    cupom = produto.get('cupom', '').strip()
    link_curto = gerar_link_curto(produto['link'])
    return f"- {nome} | {preco} | {cupom} | {fornecedor} | {link_curto}"

def processar_comparacao(comp_id, comp_nome, comp_url, enviar_sempre, termos, driver):
    log.info(comp_id, f"Iniciando comparação: [{comp_id}] {comp_nome}")

    produtos = web_mon.coletar_produtos(driver, comp_url, n_coletas=3)
    if not produtos:
        log.warn(comp_id, f"Nenhum produto coletado para [{comp_id}] {comp_nome}. Pulando.")
        return

    pasta_snap = os.path.join(os.path.dirname(__file__), '..', 'snapshots', comp_id)
    os.makedirs(pasta_snap, exist_ok=True)

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    nome_arquivo = f'coleta_{timestamp}.json'
    caminho_arquivo = os.path.join(pasta_snap, nome_arquivo)

    comparador.salvar_coleta(produtos, caminho_arquivo)

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
            preco_antigo = comparador.menor_valor(prod_antigo.get('preco'))
            preco_novo = comparador.menor_valor(prod_novo.get('preco'))
            if preco_antigo != preco_novo:
                alterados.append(prod_novo)

        msg = f"[{comp_id}] {comp_nome}\n"
        msg += f"🔗 Link monitorado: {comp_url}\n\n"
        msg += (f"📊 Monit:\n"
                f"IGUA: {len(mantidos) - len(alterados)} | ALTD: {len(alterados)} | NOVO: {len(novos)} | RMVD: {len(removidos)}\n\n")

        enviar = enviar_sempre == 1

        if novos:
            filtrados = []
            for chave in novos:
                produto = nova_dict[chave]
                if contem_termo(produto['produto'], termos):
                    filtrados.append(produto)

            if filtrados:
                msg += "🆕 Novos:\n"
                for produto in filtrados:
                    msg += formatar_produto(produto) + "\n"
                enviar = True

        if alterados:
            filtrados = []
            for produto in alterados:
                if contem_termo(produto['produto'], termos):
                    filtrados.append(produto)

            if filtrados:
                msg += "\n🔄 Alterados:\n"
                for produto in filtrados:
                    msg += formatar_produto(produto) + "\n"
                enviar = True

        if enviar:
            enviar_mensagem_whatsapp(msg, env.PHONE, env.API_KEY)
        else:
            log.info(comp_id, "Nenhuma alteração relevante. Não enviando mensagem.")

    else:
        msg = f"[{comp_id}] {comp_nome}\n"
        msg += f"🔗 Link monitorado: {comp_url}\n\n"
        msg += "[INFO] Nenhuma coleta anterior para comparar.\n"

        if enviar_sempre == 1:
            enviar_mensagem_whatsapp(msg, env.PHONE, env.API_KEY)

def main():
    log.info("run_compara_aviso_multi", "Iniciando execução...")

    options = Options()
    options.add_argument(r"--user-data-dir=C:\tools\SeleniumProfile")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    try:
        cupons_aplicador.aplicar_cupons(driver)

        for comp in comparacoes:
            comp_id, comp_nome, comp_url, enviar_sempre, termos = comp
            processar_comparacao(comp_id, comp_nome, comp_url, enviar_sempre, termos, driver)

    finally:
        driver.quit()
        log.info("run_compara_aviso_multi", "Navegador fechado após todas as comparações.")

if __name__ == "__main__":
    main()