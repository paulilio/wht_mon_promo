import os
import subprocess
from common import log
from common import env

MODULE_NAME = 'rclone'

def upload_to_gdrive(local_file: str, remote: str =env.RCLONE, remote_folder: str = "") -> str:
    """
    Faz upload para o Google Drive via rclone e retorna link público.
    """
    try:
        if remote_folder:
            remote_path = f"{remote}:{remote_folder}"
        else:
            remote_path = f"{remote}:"

        # ✅ Copia o arquivo
        subprocess.run(["rclone", "copy", local_file, remote_path], check=True)

        # ✅ Gera link
        remote_file = f"{remote_folder}/{os.path.basename(local_file)}" if remote_folder else os.path.basename(local_file)
        result = subprocess.run(
            ["rclone", "link", f"{remote}:{remote_file}"],
            capture_output=True, text=True, check=True
        )

        link = result.stdout.strip()
        log.info(MODULE_NAME, f"Arquivo enviado e link gerado: {link}")
        return link
    except subprocess.CalledProcessError as e:
        log.error(MODULE_NAME, f"Erro no upload ou link: {e}")
        return ""
