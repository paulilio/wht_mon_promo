import os
import requests

BASE_URL = os.getenv('FIREBASE_BASE_URL')

if not BASE_URL:
    raise ValueError("Variável de ambiente 'FIREBASE_BASE_URL' não está definida.")

def carregar_base(nome_base):
    """
    Carrega a base no caminho: {BASE_URL}/{nome_base}.json
    Retorna sempre um dicionário (pode ser vazio).
    """
    url = f"{BASE_URL}/{nome_base}.json"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()

        if not isinstance(data, dict):
            print(f"[WARN] Base {nome_base} não retornou um dicionário. Tipo: {type(data)}. Conteúdo: {data}")
            return {}

        return data

    except requests.RequestException as e:
        print(f"[ERRO] Falha ao carregar base '{nome_base}': {e}")
        return {}
    except ValueError as e:
        print(f"[ERRO] JSON inválido na base '{nome_base}': {e}")
        return {}

def inserir_codigo(base, codigo, payload):
    """
    Insere ou atualiza um item na base Firebase no caminho {BASE_URL}/{base}/{codigo}.json
    """
    url = f"{BASE_URL}/{base}/{codigo}.json"
    try:
        response = requests.put(url, json=payload, timeout=10)
        response.raise_for_status()
        print(f"[OK] Código {codigo} inserido na base '{base}'.")
        return True
    except requests.RequestException as e:
        print(f"[ERRO] Falha ao inserir código '{codigo}' na base '{base}': {e}")
        return False