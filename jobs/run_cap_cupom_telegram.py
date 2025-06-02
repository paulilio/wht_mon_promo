import argparse
import sys
import re
import requests
from datetime import datetime, timedelta, timezone
from services.telegram.telegram_service import coletar_e_salvar_cupons
from common import env

BASE_URL = env.FIREBASE_BASE_URL
if not BASE_URL:
    raise Exception("FIREBASE_BASE_URL não definido no .env")

if __name__ == "__main__":
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--tudo", action="store_true", help="Coletar todos os cupons desde o mês passado")
        args = parser.parse_args()

        api_id = int(env.TG_API_ID)
        api_hash = env.TG_API_HASH
        channel = env.TG_CHANNEL or "cupombr"
        base_nome = "cupons_telegram"

        limite_data = None
        if not args.tudo:
            hoje = datetime.now(timezone.utc).date()
            limite_data = datetime(hoje.year, hoje.month, hoje.day, tzinfo=timezone.utc) - timedelta(days=2)

        teve_novos = coletar_e_salvar_cupons(api_id, api_hash, channel, pegar_tudo=args.tudo, base_nome=base_nome, limite_data=limite_data)

        sys.exit(0 if teve_novos else 10)

    except Exception as e:
        print(f"[ERRO] Ocorreu uma exceção: {e}")
        sys.exit(1)
