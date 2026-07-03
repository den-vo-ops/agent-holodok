# Holodok Agent

Личный Telegram-бот-помощник мастера по ремонту холодильников. См. [spec.md](spec.md) и план в `docs/superpowers/plans/`.

## Локальный запуск

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # заполнить TELEGRAM_BOT_TOKEN, OWNER_TELEGRAM_ID, ANTHROPIC_API_KEY
python -m pytest
python -m holodok_agent.bot.main
```

## Деплой на VPS (systemd)

```bash
sudo mkdir -p /opt/holodok-agent
sudo cp -r . /opt/holodok-agent
cd /opt/holodok-agent
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
cp .env.example .env  # заполнить реальные значения
sudo cp deploy/holodok-agent.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now holodok-agent
sudo systemctl status holodok-agent
```

Логи: `journalctl -u holodok-agent -f`
