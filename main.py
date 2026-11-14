import sys
import json
import warnings
warnings.filterwarnings("ignore")

from src.providers.crypto import BinanceCryptoProvider
from src.providers.stocks import USStocksProvider

def load_locale(lang: str = "fr"):
    with open(f"config/locales/{lang}.json", "r", encoding="utf-8") as f:
        return json.load(f)

def run_screener(market_choice: str = "1", lang: str = "fr", timeframe: str = "1w"):
    t = load_locale(lang)
    tf_label = "Hebdomadaire (Weekly - 1w)" if lang == "fr" else "Weekly (1w)"
    
    print("\n" + "=" * 84)
    print(f"  {t['app_title']}")
    print(f"  {t['author']} | {tf_label}")
    print("=" * 84)

    results = []
    
    if market_choice in ["1", "crypto"]:
        market_name = "Cryptomonnaies (Top Binance)"
        print(f"\n[*] {t['scanning'].format(count=15, market=market_name)}")
        provider = BinanceCryptoProvider()
        pairs = provider.fetch_top_pairs(limit=15)
        for p in pairs:
            data = provider.analyze_ticker(p['symbol'], timeframe=timeframe)
            if data:
                data['name'] = p['symbol'].split('/')[0]
                results.append(data)
                
    elif market_choice in ["2", "stocks"]:
        market_name = "Actions US (S&P 500)"
        stocks_provider = USStocksProvider()
        stock_list = stocks_provider.get_sp500_tickers(limit=15)
        print(f"\n[*] {t['scanning'].format(count=len(stock_list), market=market_name)}")
        for item in stock_list:
            data = stocks_provider.analyze_stock(item['symbol'], timeframe="1wk")
            if data:
                data['name'] = item['name']
                results.append(data)
    else:
        print("Marché non encore configuré ou choix invalide.")
        return

    # Tableau des résultats
    header = f"{t['col_symbol']:<8} | {t['col_name']:<20} | {t['col_price']:<10} | {t['col_regime']:<18} | {t['col_state']}"
    print("\n" + header)
    print("-" * 84)
    for r in results:
        regime_label = t.get(r['regime'], r['regime'])
        state_label = t.get(r['state'], r['state'])
        print(f"{r['symbol']:<8} | {r['name']:<20} | ${r['price']:<9} | {regime_label:<18} | {state_label}")

    print("-" * 84)
    print(t['scan_completed'].format(found=len(results)))

if __name__ == "__main__":
    lang_choice = sys.argv[1] if len(sys.argv) > 1 else "fr"
    
    if len(sys.argv) > 2:
        market = sys.argv[2]
        run_screener(market_choice=market, lang=lang_choice)
    else:
        t = load_locale(lang_choice)
        print("\n--- " + t['menu_prompt'] + " ---")
        print(t['menu_crypto'])
        print(t['menu_stocks'])
        print(t['menu_forex'] + " (bientôt)")
        print(t['menu_commodities'] + " (bientôt)")
        print(t['menu_indices'] + " (bientôt)")
        print(t['menu_etf'] + " (bientôt)")
        
        choice = input("\nVotre choix (1 ou 2) [Défaut: 1]: ").strip()
        if not choice:
            choice = "1"
        run_screener(market_choice=choice, lang=lang_choice)
