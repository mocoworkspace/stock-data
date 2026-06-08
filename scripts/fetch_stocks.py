"""
株価データ取得スクリプト
GitHub Actions から実行し、stocks.json を生成して GitHub Pages で配信する。

取得対象:
  - 日本株（東証）: JST 16:00 以降（東証終値確定後）
  - 米国株（NYSE/NASDAQ）: JST 07:00 以降（米国終値確定後）
"""

import json
import sys
import time
from datetime import datetime, timezone

import requests

# ── 取得対象シンボル ────────────────────────────────────────────────────────

JAPAN_SYMBOLS = [
    # 株主優待銘柄（アプリ内静的データと対応）
    "2914.T",  # 日本たばこ産業(JT)
    "2502.T",  # アサヒグループHD
    "2503.T",  # キリンHD
    "2802.T",  # 味の素
    "3197.T",  # すかいらーくHD
    "9861.T",  # 吉野家HD
    "7412.T",  # アトム
    "8267.T",  # イオン
    "3099.T",  # 三越伊勢丹HD
    "3086.T",  # J.フロント リテイリング
    "3048.T",  # ビックカメラ
    "3382.T",  # セブン&アイHD
    "9983.T",  # ファーストリテイリング
    "3092.T",  # ZOZO
    "9201.T",  # JAL
    "9202.T",  # ANA
    "9022.T",  # JR東海
    "4681.T",  # リゾートトラスト
    "9412.T",  # スカパーJSAT HD
    "8001.T",  # 伊藤忠商事
    "8058.T",  # 三菱商事
    # Nikkei 主要銘柄
    "7203.T",  # トヨタ自動車
    "9984.T",  # ソフトバンクグループ
    "6758.T",  # ソニーグループ
    "6861.T",  # キーエンス
    "8035.T",  # 東京エレクトロン
    "9432.T",  # NTT
    "7974.T",  # 任天堂
    "4063.T",  # 信越化学工業
    "6098.T",  # リクルートHD
    "8306.T",  # 三菱UFJフィナンシャル・グループ
    "8316.T",  # 三井住友フィナンシャルグループ
    "4502.T",  # 武田薬品工業
    "6501.T",  # 日立製作所
    "6702.T",  # 富士通
    "7267.T",  # ホンダ
    "7201.T",  # 日産自動車
    "4568.T",  # 第一三共
    "6367.T",  # ダイキン工業
    "4519.T",  # 中外製薬
    "2413.T",  # エムスリー
    "6954.T",  # ファナック
    "7741.T",  # HOYA
    "4543.T",  # テルモ
    "8031.T",  # 三井物産
    "8053.T",  # 住友商事
    "9433.T",  # KDDI
    "9434.T",  # ソフトバンク
    "6902.T",  # デンソー
    "7751.T",  # キヤノン
]

US_SYMBOLS = [
    # GAFAM + 主要テック
    "AAPL",   # Apple
    "MSFT",   # Microsoft
    "NVDA",   # NVIDIA
    "GOOGL",  # Alphabet
    "AMZN",   # Amazon
    "META",   # Meta
    "TSLA",   # Tesla
    "AVGO",   # Broadcom
    "NFLX",   # Netflix
    "ORCL",   # Oracle
    # 金融
    "BRK-B",  # Berkshire Hathaway
    "JPM",    # JPMorgan Chase
    "V",      # Visa
    "MA",     # Mastercard
    "BAC",    # Bank of America
    "WFC",    # Wells Fargo
    "GS",     # Goldman Sachs
    # ヘルスケア・消費財
    "UNH",    # UnitedHealth
    "JNJ",    # Johnson & Johnson
    "LLY",    # Eli Lilly
    "ABBV",   # AbbVie
    "MRK",    # Merck
    "PG",     # Procter & Gamble
    "KO",     # Coca-Cola
    "PEP",    # PepsiCo
    "WMT",    # Walmart
    "COST",   # Costco
    "MCD",    # McDonald's
    "HD",     # Home Depot
    "DIS",    # Disney
    # エネルギー
    "XOM",    # ExxonMobil
    "CVX",    # Chevron
]

ALL_SYMBOLS = JAPAN_SYMBOLS + US_SYMBOLS

# ── ユーティリティ ──────────────────────────────────────────────────────────

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StockDataBot/1.0)"}
REQUEST_TIMEOUT = 15
# GitHub Actions の IP 制限を避けるため控えめなレート
SLEEP_BETWEEN_REQUESTS = 0.8  # 秒


def fetch_stock(symbol: str) -> dict | None:
    """1銘柄の EOD データを Yahoo Finance から取得する"""
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        "?interval=1d&range=30d&includePrePost=false"
    )
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code != 200:
            print(f"  HTTP {resp.status_code}: {symbol}", file=sys.stderr)
            return None

        data = resp.json()
        results = data.get("chart", {}).get("result")
        if not results:
            print(f"  No result: {symbol}", file=sys.stderr)
            return None

        result = results[0]
        meta = result.get("meta", {})
        quotes = result.get("indicators", {}).get("quote", [{}])[0]
        timestamps = result.get("timestamp", [])
        close_prices = quotes.get("close", [])

        price = float(meta.get("regularMarketPrice", 0))
        prev_close = float(
            meta.get("chartPreviousClose")
            or meta.get("previousClose")
            or price
        )
        change = price - prev_close
        change_pct = (change / prev_close * 100) if prev_close else 0.0

        # 最新 30 日分の終値（None は 0.0 に変換）
        chart = [round(float(p), 4) if p is not None else 0.0 for p in close_prices[-30:]]

        return {
            "s": symbol,
            "n": meta.get("shortName") or meta.get("longName") or symbol,
            "p": round(price, 4),
            "c": round(change, 4),
            "cp": round(change_pct, 4),
            "cur": meta.get("currency", "JPY"),
            "pc": round(prev_close, 4),
            "o": round(float(meta.get("regularMarketOpen") or 0), 4),
            "h": round(float(meta.get("regularMarketDayHigh") or 0), 4),
            "l": round(float(meta.get("regularMarketDayLow") or 0), 4),
            "v": int(meta.get("regularMarketVolume") or 0),
            "ex": meta.get("exchangeName", ""),
            "ch": chart,
        }

    except Exception as e:
        print(f"  Exception for {symbol}: {e}", file=sys.stderr)
        return None


# ── メイン ──────────────────────────────────────────────────────────────────

def main() -> None:
    print(f"Fetching {len(ALL_SYMBOLS)} symbols...")
    stocks: dict[str, dict] = {}

    for i, symbol in enumerate(ALL_SYMBOLS, 1):
        print(f"[{i:3}/{len(ALL_SYMBOLS)}] {symbol}", end=" ... ")
        data = fetch_stock(symbol)
        if data:
            stocks[symbol] = data
            print(f"OK  ¥{data['p']:,.0f}" if data["cur"] == "JPY" else f"OK  ${data['p']:.2f}")
        else:
            print("SKIP")
        if i < len(ALL_SYMBOLS):
            time.sleep(SLEEP_BETWEEN_REQUESTS)

    output = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "count": len(stocks),
        "stocks": stocks,
    }

    with open("stocks.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False)  # インデントなし（ファイルサイズ削減）

    print(f"\nDone. {len(stocks)}/{len(ALL_SYMBOLS)} stocks saved to stocks.json")


if __name__ == "__main__":
    main()
