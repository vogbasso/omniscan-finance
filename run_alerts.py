import os
os.environ["PYTHONWARNINGS"] = "ignore"
import warnings
warnings.filterwarnings("ignore")

import sys
from src.providers.crypto import BinanceCryptoProvider
from src.providers.stocks import USStocksProvider
from src.alerts.state_manager import StateManager
from src.alerts.notifier import Notifier

def run_alert_check():
    print("=" * 65)
    print("  OmniScan Finance - Vérification des Transitions Hebdo")
    print("  Auteur : Vogel Paolo BASSO")
    print("=" * 65)

    previous_states = StateManager.load_states()
    new_states = dict(previous_states)
    notifier = Notifier()

    total_alerts = 0

    # 1. Analyse Actions US
    print("[*] Scan des Actions US...")
    stocks = USStocksProvider()
    for item in stocks.get_sp500_tickers(limit=15):
        data = stocks.analyze_stock(item['symbol'], timeframe="1wk")
        if data:
            data['name'] = item['name']
            sym = item['symbol']
            
            # Vérifier si transition d'état
            alert = StateManager.detect_transition(sym, data, previous_states)
            if alert:
                notifier.send_alert(alert)
                total_alerts += 1
            
            new_states[sym] = data

    # 2. Analyse Crypto Top Binance
    print("[*] Scan des Cryptomonnaies...")
    crypto = BinanceCryptoProvider()
    for pair in crypto.fetch_top_pairs(limit=15):
        data = crypto.analyze_ticker(pair['symbol'], timeframe="1w")
        if data:
            data['name'] = pair['symbol'].split('/')[0]
            sym = pair['symbol']
            
            alert = StateManager.detect_transition(sym, data, previous_states)
            if alert:
                notifier.send_alert(alert)
                total_alerts += 1

            new_states[sym] = data

    # Sauvegarder la nouvelle photo de marché
    StateManager.save_states(new_states)
    
    print("-" * 65)
    print(f"[✓] Analyse terminée. {total_alerts} changement(s) d'état détecté(s).")
    print(f"[✓] État mémorisé dans data/state.json ({len(new_states)} actifs suivis).")

if __name__ == "__main__":
    run_alert_check()
