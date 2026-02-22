# VPS Deployment Guide

## 1. Подготовка безопасности

```gitignore
# Добавь в .gitignore СРАЗУ (до первого коммита с кредами):
*-credentials*.json
*.pem
.env
.env.*
```

> **CAUTION**: Google автоматически отзывает service account ключи если обнаружит их в публичном репозитории!

**Если ключ засветился:**
1. Google Cloud Console -> IAM -> Service Accounts
2. Найти аккаунт -> Keys -> Add Key -> Create new key (JSON)
3. Скачать новый, удалить старый из репо через `git filter-repo`

---

## 2. Systemd Service Template

```bash
sudo nano /etc/systemd/system/my-bot.service
```

```ini
[Unit]
Description=My Bot Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/my-bot
EnvironmentFile=/opt/my-bot/.env    # ВАЖНО! Без этого .env не читается
ExecStart=/opt/my-bot/.venv/bin/python -m src.bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable my-bot
sudo systemctl start my-bot
sudo systemctl status my-bot
```

---

## 3. Копирование файлов

> **WARNING**: НЕ используй heredoc (`cat << EOF`) для JSON — ломает переносы строк в private_key!

**Правильно — через SCP:**
```powershell
scp "local_file.json" root@IP:/opt/project/
```

**Альтернатива через base64:**
```bash
# Локально
cat file.json | base64 -w 0 > encoded.txt

# На сервере
echo "BASE64_STRING" | base64 -d > file.json
```

---

## 4. Windows -> Linux Fixes

**CRLF -> LF конвертация:**
```bash
sed -i 's/\r$//' filename.json
file filename.json  # проверка: должно быть ASCII/UTF-8, НЕ CRLF
```

---

## 5. JWT / OAuth Issues

Google OAuth требует точного времени на сервере:
```bash
timedatectl  # должно быть "NTP synchronized: yes"
```

Если нет:
```bash
sudo timedatectl set-ntp on
```

---

## 6. SSH Keys (для автодеплоя)

```bash
# Локально (Windows PowerShell)
ssh-keygen -t ed25519 -C "deploy@myproject"

# Копируем на сервер
type $env:USERPROFILE\.ssh\id_ed25519.pub | ssh root@IP "cat >> ~/.ssh/authorized_keys"
```

---

## 7. Скрипт автодеплоя на сервере

```bash
sudo nano /opt/my-bot/deploy.sh
```

```bash
#!/bin/bash
cd /opt/my-bot
git pull
source .venv/bin/activate
pip install -r requirements.txt
systemctl restart my-bot
echo "Deployed at $(date)"
```

```bash
chmod +x /opt/my-bot/deploy.sh
```

---

## Quick Commands Cheatsheet

```bash
# Логи в реальном времени
journalctl -u my-bot -f

# Перезапуск
sudo systemctl restart my-bot

# Статус
sudo systemctl status my-bot

# Проверка портов
ss -tulpn | grep LISTEN
```
