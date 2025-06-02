import time
import random
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from common import env

base_cupons = "cupons_telegram"

# 🔎 Buscar apenas cupons que ainda NÃO foram aplicados no Firebase
def buscar_cupons_nao_aplicados():
    url = f"{env.FIREBASE_BASE_URL}/{base_cupons}.json"
    print(f"[DEBUG] Buscando cupons em: {url}")

    try:
        response = requests.get(url)
        data = response.json()
        if not data or not isinstance(data, dict):
            print("[ERRO] Nenhum dado encontrado.")
            return []

        resultado = []

        for data_str, cupons_dia in data.items():
            if not isinstance(cupons_dia, dict):
                continue

            for codigo, info in cupons_dia.items():
                if not isinstance(info, dict):
                    continue

                aplicado = str(info.get("aplicado", "0")).strip()
                if aplicado != "1":
                    path = f"{base_cupons}/{data_str}/{codigo}"
                    resultado.append((path, codigo))

        print(f"[INFO] {len(resultado)} cupons pendentes encontrados.")
        return resultado

    except Exception as e:
        print(f"[ERRO] Erro ao acessar Firebase: {e}")
        return []

# ✅ Atualiza o status do cupom no Firebase como aplicado = 1 (com segurança)
def marcar_como_aplicado(path_completo):
    url = f"{env.FIREBASE_BASE_URL}/{path_completo}.json"
    try:
        # Recuperar o conteúdo atual do cupom
        resp = requests.get(url)
        if resp.status_code != 200:
            raise Exception(f"Erro ao ler dados existentes: {resp.status_code}")

        dados = resp.json() or {}
        dados["aplicado"] = 1  # sobrescreve o campo

        # Salva os dados completos de volta (garante consistência)
        resp_put = requests.put(url, json=dados)
        if resp_put.status_code == 200:
            print(f"[OK] Cupom marcado como aplicado: {path_completo}")
        else:
            raise Exception(f"Erro ao salvar dados: {resp_put.status_code}")

    except Exception as e:
        print(f"[ERRO] Falha ao marcar cupom como aplicado: {e}")

# 🧠 Aplicação automática dos cupons no Mercado Livre
def aplicar_cupons(driver):
    print("💡 Iniciando rotina de aplicação de cupons...")

    cupons_para_aplicar = buscar_cupons_nao_aplicados()
    if not cupons_para_aplicar:
        print("[INFO] Nenhum cupom novo para aplicar.")
        return

    for path_completo, codigo in cupons_para_aplicar:
        try:
            print(f"➡️ Aplicando cupom: {codigo}")

            driver.get("https://www.mercadolivre.com.br/cupons")
            time.sleep(random.uniform(1, 1.5))

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".input-code-modal button"))
            ).click()

            time.sleep(0.5)

            input_field = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".andes-modal input.andes-form-control__field"))
            )
            input_field.clear()
            input_field.send_keys(codigo)

            time.sleep(0.5)

            WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, ".button__container button"))
            ).click()

            time.sleep(random.uniform(1.5, 2))

            # ✅ Garante que será registrado como aplicado
            marcar_como_aplicado(path_completo)

        except Exception as e:
            print(f"[ERRO] Falha ao aplicar o cupom {codigo}: {e}")

    print("[OK] Finalizado o processo de aplicação de cupons.")
