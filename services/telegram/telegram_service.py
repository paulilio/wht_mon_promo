from datetime import datetime, timedelta, timezone
import re
from services.firebase import firebase_service as fb
from services.firebase.firebase_service import listar_cupons_existentes_hoje, obter_ultima_data_processada, salvar_cupom_unico, salvar_ultima_data_processada
from telethon.sync import TelegramClient

def extrair_cupons(texto):
    """
    Extrai possíveis cupons com letras e números, como HOJE9OFF ou DEZOFF
    """
    if not texto:
        return []

    ignorar = {
        "CUPOM", "MERCADO", "LIVRE", "LIMITE", "ATIVE", "AJUDAR",
        "GRUPO", "HTTPS", "MERCADOLIVRE", "WHATSAPP", "PEGOU", "LIMITADO", "ACIMA"
    }

    palavras = re.findall(r'\b[A-Z0-9]{5,15}\b', texto.upper())
    return [p for p in palavras if p not in ignorar]

def gerar_chave_data():
    return datetime.now().strftime("%Y-%m-%d")

def coletar_e_salvar_cupons(api_id, api_hash, channel, pegar_tudo=False, base_nome="cupons_telegram", limite_data=None):
    print(f"🔄 Coletando | Modo: {'TODOS' if pegar_tudo else 'DIÁRIO'} | Base: {base_nome}")

    cupons_existentes = set()
    if not pegar_tudo:
        cupons_existentes = listar_cupons_existentes_hoje(base_nome)

    if limite_data:
        data_inicio = limite_data
    elif not pegar_tudo:
        data_inicio = obter_ultima_data_processada(base_nome)
    else:
        data_inicio = datetime.now(timezone.utc) - timedelta(days=30)

    novos_cupons = {}
    maior_data_msg = None

    with TelegramClient("sessao_cupom", api_id, api_hash) as client:
        for msg in client.iter_messages(channel, limit=1000):
            if not msg.text or (msg.date and msg.date <= data_inicio):
                break

            for codigo in extrair_cupons(msg.text):
                if codigo in cupons_existentes or codigo in novos_cupons:
                    continue

                dados = {
                    "codigo": codigo,
                    "mensagem": msg.text,
                    "canal": channel,
                    "capturado_em": datetime.now(timezone.utc).isoformat()
                }
                novos_cupons[codigo] = dados
                if not maior_data_msg or msg.date > maior_data_msg:
                    maior_data_msg = msg.date

    if not novos_cupons:
        print("ℹ️ Nenhum novo cupom encontrado.")
        return False

    print(f"🎉 {len(novos_cupons)} novos cupons encontrados.")
    for codigo, dados in novos_cupons.items():
        salvar_cupom_unico(codigo, dados, base_nome)
        print(f"☁️ Salvo: {codigo}")

    if maior_data_msg:
        salvar_ultima_data_processada(base_nome, maior_data_msg)

    return True
