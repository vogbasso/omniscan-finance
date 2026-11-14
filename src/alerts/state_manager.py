import json
import os
from typing import Dict, Any, List, Optional

STATE_FILE = "data/state.json"

class StateManager:
    @staticmethod
    def load_states() -> Dict[str, Any]:
        if not os.path.exists(STATE_FILE):
            return {}
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    @staticmethod
    def save_states(states: Dict[str, Any]):
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(states, f, indent=2, ensure_ascii=False)

    @staticmethod
    def detect_transition(symbol: str, new_data: Dict[str, Any], previous_states: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        prev = previous_states.get(symbol)
        
        # Premier enregistrement pour cet actif
        if not prev:
            return None

        old_state = prev.get("state")
        new_state = new_data.get("state")
        old_regime = prev.get("regime")
        new_regime = new_data.get("regime")

        # Pas de changement
        if old_state == new_state and old_regime == new_regime:
            return None

        # Détection du type d'événement
        event_type = None
        message = ""

        # 1. Alerte Niveau 1 : Rupture / Nouveau Signal
        if new_state == "state_new_buy" or (old_regime == "regime_bear" and new_regime == "regime_bull"):
            event_type = "BUY_SIGNAL"
            message = f"🔥 NOUVEAU SIGNAL ACHAT sur {symbol} (${new_data['price']}) - La tendance de fond bascule ACHETEUR 🟢"
        
        elif new_state == "state_new_sell" or (old_regime == "regime_bull" and new_regime == "regime_bear"):
            event_type = "SELL_SIGNAL"
            message = f"🚨 NOUVEAU SIGNAL VENTE sur {symbol} (${new_data['price']}) - La tendance de fond bascule VENDEUR 🔴"

        # 2. Alerte Niveau 2 : Ralentissement (Prise de bénéfices / Remontée du Stop)
        elif old_state == "state_strong_bull" and new_state == "state_slowdown_bull":
            event_type = "SLOWDOWN_BULL"
            message = f"⚠️ ESSOUFFLEMENT HAUSSIER sur {symbol} (${new_data['price']}) - La MM5 faiblit sous la MM20. Relevez vos stops de protection."

        # 3. Alerte Niveau 3 : Décollage hors de la consolidation
        elif old_state == "state_consolidation" and new_state == "state_strong_bull":
            event_type = "BREAKOUT_BULL"
            message = f"🚀 SORTIE DE CONSOLIDATION sur {symbol} (${new_data['price']}) - Reprise de tendance forte haussière."

        if event_type:
            return {
                "symbol": symbol,
                "name": new_data.get("name", symbol),
                "price": new_data["price"],
                "event_type": event_type,
                "message": message,
                "old_state": old_state,
                "new_state": new_state
            }
        return None
