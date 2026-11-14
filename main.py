import sys
import json
from src.providers.crypto import BinanceCryptoProvider

def load_locale(lang: str = "fr"):
    with open(f"config/locales/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)

def run_crypto_scan(lang: str = "fr", limit: int = 15, timeframe: str = "1w"):
    t = load_locale(lang)
    tf_label = "Hebdomadaire (Weekly - 1w)" if lang == "fr" else "Weekly (1w)"
    
    print("=" * 84)
    print(f"  {t['app_title']}")
    print(f"  {t['author']} | {tf_label}")
    print("=" * 84)
    print(f"\n[*] {t['scanning'].format(count=limit)}")
    
    provider = BinanceCryptoProvider()
    top_pairs = provider.fetch_top_pairs(limit=limit)
    
    results = []
    for pair in top_pairs:
        sym = pair['symbol']
        data = provider.analyze_ticker(sym, timeframe=timeframe)
        if data:
            results.append(data)
            
    header = f"{t['col_symbol']:<12} | {t['col_price']:<12} | {t['col_regime']:<20} | {t['col_state']}"
    print("\n" + header)
    print("-" * 84)
    for r in results:
        regime_label = t.get(r['regime'], r['regime'])
        state_label = t.get(r['state'], r['state'])
        print(f"{r['symbol']:<12} | {r['price']:<12} | {regime_label:<20} | {state_label}")

    print("-" * 84)
    print(t['scan_completed'].format(found=len(results)))

if __name__ == "__main__":
    lang_choice = sys.argv[1] if len(sys.argv) > 1 else "fr"
    tf_choice = sys.argv[2] if len(sys.argv) > 2 else "1w"
    run_crypto_scan(lang=lang_choice, limit=15, timeframe=tf_choice)
