# Projeto wht_mon_promo
Gerado pelo script de inicialização: `setup/init.sh`

## Estrutura do Projeto

- `jobs/` → tarefas programadas e execução
- `mon/` → monitoramento de páginas web
- `notif/` → envio de mensagens via WhatsApp
- `main.py` → inicializador principal
- `requirements.txt` → dependências do projeto

## Descrição

Projeto para monitoramento automático de páginas web e envio de alertas via WhatsApp.

## Como rodar

1. Configure suas credenciais no módulo `notif/wht_send.py`.
2. Execute o monitoramento via:

  ```bash
  python main.py
  ```

ou agende via sistema operacional.
