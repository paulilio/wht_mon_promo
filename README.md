# Mercado Livre Scraper

Automação para coleta de preços de produtos no Mercado Livre, com comparação de históricos e envio de alertas via WhatsApp e Google Drive.

## 🎯 Funcionalidades

- Coleta automática de produtos com parcela de 18x.
- Classificação automática de produtos.
- Comparação de preços atual x anterior.
- Geração de relatórios em JSON, HTML e PDF.
- Envio automático para Google Drive.
- Notificações via WhatsApp.

---

## 🚀 Como executar

### **Pré-requisitos:**
- Python 3.8+
- Google Chrome instalado
- Ferramenta `rclone` configurada para acesso ao Google Drive
- Configurar variáveis no `.env` (exemplo abaixo)

### **Instalação de dependências:**

```bash
pip install -r requirements.txt
