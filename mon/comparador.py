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
