import time
import hashlib
import mss
import mss.tools
import pyautogui
import pygetwindow as gw
import os
from common import log

MODULE_NAME = 'monitor_browser'

def capture_screenshot(output_file: str, region=None):
    """
    Captura a screenshot de uma região específica ou da tela inteira usando MSS.
    """
    with mss.mss() as sct:
        if region:
            monitor = {"top": region[1], "left": region[0], "width": region[2], "height": region[3]}
        else:
            monitor = sct.monitors[1]  # Monitor principal

        sct_img = sct.grab(monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=output_file)
        log.info(MODULE_NAME, f"Screenshot salva em {output_file}")

def hash_image(file_path: str):
    """
    Calcula o hash MD5 da imagem para verificar mudanças.
    """
    with open(file_path, "rb") as f:
        img_data = f.read()
    return hashlib.md5(img_data).hexdigest()

def find_window(title: str):
    """
    Procura a janela pelo nome exato.
    """
    windows = gw.getAllWindows()
    for win in windows:
        if title == win.title:
            return win
    return None

def refresh_window(window):
    """
    Ativa a janela e envia comando de hard refresh (Ctrl + F5).
    """
    try:
        window.activate()
        log.info(MODULE_NAME, f"Janela '{window.title}' ativada.")
        time.sleep(0.5)
        pyautogui.hotkey('ctrl', 'f5')
        log.info(MODULE_NAME, "Comando de hard refresh (Ctrl + F5) enviado.")
    except Exception as e:
        log.error(MODULE_NAME, f"Erro ao ativar ou refrescar a janela: {e}")

def sanitize_filename(name: str) -> str:
    """
    Remove caracteres inválidos para nomes de arquivos.
    """
    return ''.join(c for c in name if c.isalnum() or c in (' ', '_', '-')).rstrip().replace(' ', '_')

def monitor_browser(window_title: str, interval: int = 10, sempre_enviar: bool = False):
    """
    Monitora uma janela com nome EXATO informado.
    
    :param window_title: Nome exato da janela a ser monitorada.
    :param interval: Intervalo em segundos entre as verificações.
    :param sempre_enviar: Se True, envia a cada ciclo; se False, só quando houver mudança.
    """
    log.info(MODULE_NAME, f"Procurando janela com nome exato: '{window_title}'...")

    window = find_window(window_title)
    if not window:
        log.error(MODULE_NAME, f"Nenhuma janela encontrada com o nome: '{window_title}'.")
        return

    log.info(MODULE_NAME, f"Janela encontrada: {window.title}")
    region = (window.left, window.top, window.width, window.height)
    log.info(MODULE_NAME, f"Região da captura: {region}")

    snapshot_dir = os.path.join('snapshot', 'screens')
    os.makedirs(snapshot_dir, exist_ok=True)

    sanitized_name = sanitize_filename(window_title)
    screenshot_file = os.path.join(snapshot_dir, f"ultima_captura_{sanitized_name}.png")

    last_hash = None

    while True:
        try:
            refresh_window(window)
            time.sleep(2)

            capture_screenshot(screenshot_file, region)
            current_hash = hash_image(screenshot_file)

            if sempre_enviar:
                log.info(MODULE_NAME, "Envio configurado para sempre.")
                yield screenshot_file
            elif last_hash and current_hash != last_hash:
                log.info(MODULE_NAME, "Mudança detectada na janela monitorada.")
                yield screenshot_file
            else:
                log.info(MODULE_NAME, "Nenhuma mudança detectada.")

            last_hash = current_hash
            time.sleep(interval)

        except KeyboardInterrupt:
            log.info(MODULE_NAME, "Monitoramento interrompido pelo usuário.")
            break
        except Exception as e:
            log.error(MODULE_NAME, f"Erro durante o monitoramento: {e}")
            break
