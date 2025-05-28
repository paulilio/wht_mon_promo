import json
import os
import re
from common import log

def salvar_coleta(coleta, caminho_completo):
    """
    Salva uma coleta em formato JSON no caminho especificado.
    """
    os.makedirs(os.path.dirname(caminho_completo), exist_ok=True)
    with open(caminho_completo, 'w', encoding='utf-8') as f:
        json.dump(coleta, f, ensure_ascii=False, indent=4)
    msg = f"✅ Coleta salva em: {caminho_completo} com {len(coleta)} produtos."
    print(msg)
    log.write_log('comparador', msg)

def carregar_coleta(caminho_completo):
    """
    Carrega uma coleta JSON do caminho especificado.
    """
    with open(caminho_completo, 'r', encoding='utf-8') as f:
        coleta = json.load(f)
    msg = f"📥 Coleta carregada de: {caminho_completo} com {len(coleta)} produtos."
    print(msg)
    log.write_log('comparador', msg)
    return coleta

def menor_valor(preco_str):
    """
    Extrai e converte para float o menor valor monetário de uma string de preços.
    """
    if not preco_str:
        return None
    valores = re.findall(r'R\$?\s*\d{1,3}(?:\.\d{3})*,\d{2}', preco_str)
    menores = []
    for val in valores:
        num = val.replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        try:
            menores.append(float(num))
        except ValueError:
            continue
    return min(menores) if menores else None

def deduplicar_coleta(coleta):
    """
    Remove duplicatas de uma coleta com base na chave (produto, fornecedor).
    """
    vista = set()
    deduplicados = []
    for p in coleta:
        chave = (p['produto'], p['fornecedor'])
        if chave not in vista:
            vista.add(chave)
            deduplicados.append(p)
    msg = f"🔄 Deduplicado: {len(coleta)} → {len(deduplicados)} produtos."
    print(msg)
    log.write_log('comparador', msg)
    return deduplicados

def comparar_produtos(produtos, produtos_encontrados, tolerancia_perc=10):
    """
    Compara produtos encontrados com a lista de produtos esperados.

    Para cada produto esperado, verifica se:
    - O título encontrado contém todos os termos esperados.
    - O título NÃO contém o termo proibido.
    - O preço está dentro da faixa de tolerância.

    Args:
        produtos (list): Lista de produtos a comparar.
                         Cada item: [nome, termos_str, proibido, valor_medio]
        produtos_encontrados (list): Lista de dicionários com 'titulo' e 'preco'.
        tolerancia_perc (float): Porcentagem de tolerância no preço.

    Returns:
        list: Lista de dicionários com produtos que atenderam aos critérios.
    """
    resultados = []

    for nome, termos_str, proibido, valor_medio in produtos:
        termos = termos_str.lower().split()
        proibido = proibido.lower().strip()

        for prod in produtos_encontrados:
            titulo = prod['titulo'].lower()
            preco = prod['preco']

            # Verifica se contém "18x" no título
            if "18x" not in titulo:
                continue

            # Verifica se todos os termos esperados estão presentes no título
            if not all(t in titulo for t in termos):
                continue

            # Verifica se o termo proibido NÃO está no título
            if proibido and proibido in titulo:
                continue

            # Verifica se o preço está dentro da tolerância
            tolerancia = valor_medio * (tolerancia_perc / 100)
            if abs(preco - valor_medio) > tolerancia:
                continue

            # Produto atende a todas as condições
            resultado = {
                "produto": nome,
                "termos_encontrados": termos,
                "preco": preco,
                "parcela_18x": round(preco / 18, 2)
            }
            resultados.append(resultado)

    msg = f"✅ Comparação finalizada: {len(resultados)} produtos encontrados conforme critérios."
    print(msg)
    log.write_log('comparador', msg)

    return resultados
