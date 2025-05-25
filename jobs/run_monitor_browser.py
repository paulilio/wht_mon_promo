from mon import monitor_browser
from notify.wht_send import send_whatsapp_message
from common import log
from remote.rclone import upload_to_gdrive
from common import env

MODULE_NAME = 'run_monitor_browser'

def main():
    phone = env.PHONE
    api_key = env.API_KEY
    intervalo = 20

    monitors = [
        {'id': '001', 'nome_tela': 'cupom mercadolivre bambu - Google Search - Google Chrome', 'sempre': True}
    ]

    log.info(MODULE_NAME, "Job de monitoramento de múltiplas janelas iniciado.")

    for monitor in monitors:
        id_monitor = monitor['id']
        nome_tela = monitor['nome_tela']
        sempre_enviar = monitor['sempre']

        log.info(MODULE_NAME, f"Configurando monitoramento para: {nome_tela} (ID: {id_monitor})")

        monitor_gen = monitor_browser.monitor_browser(nome_tela, intervalo, sempre_enviar)

        for screenshot_file in monitor_gen:
            # ✅ Envia a imagem para o Google Drive e obtém link
            gdrive_link = upload_to_gdrive(screenshot_file)

            mensagem = (
                f"[Alerta] Monitoramento {id_monitor}: '{nome_tela}'. Atualização periódica.\n"
                f"Link: {gdrive_link}"
                if sempre_enviar else
                f"[Alerta] Monitoramento {id_monitor}: '{nome_tela}'. Mudança detectada!\n"
                f"Link: {gdrive_link}"
            )

            log.info(MODULE_NAME, f"Enviando mensagem para {phone}: {mensagem}")
            send_whatsapp_message(phone, api_key, mensagem)
            log.info(MODULE_NAME, f"Mensagem enviada para {phone} com sucesso.")

            if not sempre_enviar:
                break  # volta para verificar novamente a partir da próxima alteração

if __name__ == "__main__":
    main()