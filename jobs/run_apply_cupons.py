import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

from services.ml import aplicar_cupons

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; rv:109.0) Gecko/20100101 Firefox/119.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
]

def get_random_user_agent():
    return random.choice(USER_AGENTS)

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

def main():
    print("[INFO] Iniciando driver.")
    driver = setup_driver()
    try:
        aplicar_cupons(driver)
    finally:
        print("[INFO] Fechando navegador.")
        driver.quit()

if __name__ == "__main__":
    main()
