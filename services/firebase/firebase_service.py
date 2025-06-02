import json
import requests
from datetime import datetime, timezone
from common import env

BASE_URL = env.FIREBASE_BASE_URL

if not BASE_URL:
    raise Exception("FIREBASE_BASE_URL não definido no .env")

def _firebase_get(path):
    url = f"{BASE_URL}/{path}.json"
    r = requests.get(url)
    if r.status_code != 200:
        raise Exception(f"Erro ao buscar '{path}': {r.status_code}")
    return r.json()

def _firebase_set(path, data):
    url = f"{BASE_URL}/{path}.json"
    r = requests.put(url, json=data)
    if r.status_code != 200:
        raise Exception(f"Erro ao salvar '{path}': {r.status_code}")

def _firebase_patch(path, data):
    url = f"{BASE_URL}/{path}.json"
    response = requests.patch(url, json=data)
    if response.status_code != 200:
        raise Exception(f"Erro ao atualizar '{path}': {response.status_code}")

def atualizar_produto_firebase(codigo, dados_atuais):
    agora = datetime.now().isoformat()
    caminho = f"produtos/{codigo}"
    snapshot = _firebase_get(caminho) or {}

    historico = snapshot.get("historico", [])
    historico.append({
        "data": agora,
        "preco": dados_atuais.get("preco"),
        "valor_parcela": dados_atuais.get("valor_parcela")
    })
    historico = historico[-10:]

    payload = {
        "produto": dados_atuais.get("produto"),
        "classificacao": dados_atuais.get("classificacao"),
        "preco": dados_atuais.get("preco"),
        "valor_parcela": dados_atuais.get("valor_parcela"),
        "valor_parc_real": dados_atuais.get("valor_parc_real"),
        "cupom": dados_atuais.get("cupom"),
        "valor_desc": dados_atuais.get("vl_desc"),
        "link": dados_atuais.get("link"),
        "link_reduzido": dados_atuais.get("link_reduzido"),
        "ultima_coleta": agora,
        "ativo": True,
        "historico": historico
    }
    _firebase_set(caminho, payload)

def obter_codigos_existentes():
    data = _firebase_get("produtos") or {}
    return set(data.keys())

def marcar_inativos(codigos_encontrados):
    codigos_existentes = obter_codigos_existentes()
    codigos_inativos = codigos_existentes - set(codigos_encontrados)

    for codigo in codigos_inativos:
        _firebase_patch(f"produtos/{codigo}", {"ativo": False})

def carregar_base(nome):
    data = _firebase_get(nome)
    if not data:
        raise Exception(f"Base '{nome}' não encontrada.")
    return data

def listar_cupons_existentes_hoje(base_nome="cupons_telegram"):
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    try:
        data = carregar_base(f"{base_nome}/{data_hoje}")
        return set(data.keys())
    except:
        return set()

def salvar_cupom_unico(codigo, dados, base_nome="cupons_telegram"):
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    path = f"{base_nome}/{data_hoje}/{codigo}"
    try:
        if _firebase_get(path):
            return False
    except:
        pass  # 404, ok

    payload = {
        "codigo": codigo,
        "mensagem": dados.get("mensagem"),
        "canal": dados.get("canal"),
        "capturado_em": datetime.now(timezone.utc).isoformat(),
        "aplicado": 0
    }
    _firebase_set(path, payload)
    return True

def obter_ultima_data_processada(base_nome="cupons_telegram"):
    base = _firebase_get(base_nome)
    if not base:
        return datetime.min.replace(tzinfo=timezone.utc)

    maior_data = None
    for dia, data_dia in base.items():
        if isinstance(data_dia, dict):
            for _, dados in data_dia.items():
                capturado_em = dados.get("capturado_em")
                if capturado_em:
                    try:
                        dt = datetime.fromisoformat(capturado_em)
                        if not maior_data or dt > maior_data:
                            maior_data = dt
                    except:
                        continue
    return maior_data or datetime.min.replace(tzinfo=timezone.utc)

def salvar_ultima_data_processada(base_nome, dt: datetime):
    _firebase_set(f"{base_nome}/ultima_mensagem_lida", dt.isoformat())
