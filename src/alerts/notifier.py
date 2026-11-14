import requests
import yaml
import os
from typing import Dict, Any

CONFIG_FILE = "config/alerts.yaml"

class Notifier:
    def __init__(self):
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        if not os.path.exists(CONFIG_FILE):
            return {}
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return yaml.safe_load(f)
        except Exception:
            return {}

    def send_alert(self, alert_data: Dict[str, Any]):
        msg = f"📡 [OmniScan Finance - Alerte Hebdo]\n{alert_data['message']}"

        # 1. Envoi Telegram
        tg = self.config.get("telegram", {})
        if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
            try:
                url = f"https://api.telegram.org/bot{tg['bot_token']}/sendMessage"
                requests.post(url, json={"chat_id": tg["chat_id"], "text": msg, "parse_mode": "Markdown"}, timeout=10)
            except Exception as e:
                print(f"[Erreur Telegram] : {e}")

        # 2. Envoi Discord
        dc = self.config.get("discord", {})
        if dc.get("enabled") and dc.get("webhook_url"):
            try:
                requests.post(dc["webhook_url"], json={"content": msg}, timeout=10)
            except Exception as e:
                print(f"[Erreur Discord] : {e}")

        # 3. Affichage Console systématique
        print(f"\n📢 [ALERTE DÉCLENCHÉE] {msg}")
