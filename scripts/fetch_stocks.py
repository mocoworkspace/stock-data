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
    # ── 株主優待銘柄（アプリ内静的データと対応） ─────────────────────────────
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
    # ── 日経225: テクノロジー・電機 ─────────────────────────────────────────
    "7203.T",  # トヨタ自動車
    "9984.T",  # ソフトバンクグループ
    "6758.T",  # ソニーグループ
    "6861.T",  # キーエンス
    "8035.T",  # 東京エレクトロン
    "9432.T",  # NTT
    "7974.T",  # 任天堂
    "4063.T",  # 信越化学工業
    "6098.T",  # リクルートHD
    "6954.T",  # ファナック
    "7741.T",  # HOYA
    "6857.T",  # アドバンテスト
    "6594.T",  # ニデック
    "6752.T",  # パナソニックHD
    "6501.T",  # 日立製作所
    "6702.T",  # 富士通
    "6701.T",  # NEC
    "6503.T",  # 三菱電機
    "6971.T",  # 京セラ
    "6645.T",  # オムロン
    "6762.T",  # TDK
    "7735.T",  # SCREENホールディングス
    "4901.T",  # 富士フイルムHD
    "7751.T",  # キヤノン
    "7832.T",  # バンダイナムコHD
    "9684.T",  # スクウェア・エニックスHD
    # ── 日経225: 金融 ────────────────────────────────────────────────────────
    "8306.T",  # 三菱UFJフィナンシャル・グループ
    "8316.T",  # 三井住友フィナンシャルグループ
    "8411.T",  # みずほフィナンシャルグループ
    "8309.T",  # 三井住友トラスト・HD
    "8766.T",  # 東京海上HD
    "8725.T",  # MS&ADインシュアランスグループ
    "8601.T",  # 大和証券グループ
    "8604.T",  # 野村HD
    "7182.T",  # ゆうちょ銀行
    "6178.T",  # 日本郵政
    # ── 日経225: 自動車・輸送機器 ────────────────────────────────────────────
    "7267.T",  # ホンダ
    "7201.T",  # 日産自動車
    "7269.T",  # スズキ
    "7270.T",  # SUBARU
    "7261.T",  # マツダ
    "6902.T",  # デンソー
    "7011.T",  # 三菱重工業
    "7012.T",  # 川崎重工業
    "7013.T",  # IHI
    "6301.T",  # コマツ
    "6326.T",  # クボタ
    "6367.T",  # ダイキン工業
    # ── 日経225: 製薬・ヘルスケア ────────────────────────────────────────────
    "4502.T",  # 武田薬品工業
    "4568.T",  # 第一三共
    "4519.T",  # 中外製薬
    "4543.T",  # テルモ
    "4507.T",  # 塩野義製薬
    "4523.T",  # エーザイ
    "4151.T",  # 協和キリン
    "4578.T",  # 大塚HD
    "4021.T",  # 日産化学
    # ── 日経225: 商社 ──────────────────────────────────────────────────────
    "8031.T",  # 三井物産
    "8053.T",  # 住友商事
    "8002.T",  # 丸紅
    "8015.T",  # 豊田通商
    # ── 日経225: 通信 ─────────────────────────────────────────────────────
    "9433.T",  # KDDI
    "9434.T",  # ソフトバンク
    "9613.T",  # NTTデータグループ
    "4689.T",  # LINEヤフー
    # ── 日経225: 素材・化学 ───────────────────────────────────────────────
    "3407.T",  # 旭化成
    "4005.T",  # 住友化学
    "4183.T",  # 三井化学
    "4042.T",  # 東ソー
    "5201.T",  # AGC
    "5401.T",  # 日本製鉄
    "5411.T",  # JFEホールディングス
    "5713.T",  # 住友金属鉱山
    "5802.T",  # 住友電気工業
    "3101.T",  # 東洋紡
    "3402.T",  # 東レ
    # ── 日経225: エネルギー・電力 ────────────────────────────────────────
    "5020.T",  # ENEOSホールディングス
    "9502.T",  # 中部電力
    "9503.T",  # 関西電力
    "9501.T",  # 東京電力HD
    # ── 日経225: 建設・不動産 ────────────────────────────────────────────
    "1801.T",  # 大成建設
    "1802.T",  # 大林組
    "1803.T",  # 清水建設
    "1812.T",  # 鹿島建設
    "1925.T",  # 大和ハウス工業
    "8801.T",  # 三井不動産
    "8802.T",  # 三菱地所
    "8830.T",  # 住友不動産
    # ── 日経225: 運輸・交通 ─────────────────────────────────────────────
    "9020.T",  # 東日本旅客鉄道(JR東)
    "9021.T",  # 西日本旅客鉄道(JR西)
    "9006.T",  # 京浜急行電鉄
    "9007.T",  # 小田急電鉄
    "9008.T",  # 東急
    # ── 日経225: 食品・飲料 ─────────────────────────────────────────────
    "2269.T",  # 明治HD
    "2002.T",  # 日清製粉グループ
    "2282.T",  # 日本ハム
    "2871.T",  # ニチレイ
    "1332.T",  # ニッスイ
    # ── 日経225: 小売・サービス ──────────────────────────────────────────
    "2651.T",  # ローソン
    "2778.T",  # マルイグループ
    "4324.T",  # 電通グループ
    "4307.T",  # 野村総合研究所
    "2413.T",  # エムスリー
    # ── 成長株・注目銘柄 ──────────────────────────────────────────────────
    "4755.T",  # 楽天グループ
    "4385.T",  # メルカリ
    "3659.T",  # ネクソン
    "3778.T",  # さくらインターネット
    "4480.T",  # メドレー
    "4565.T",  # そーせいグループ
    "6146.T",  # ディスコ
    "6723.T",  # ルネサスエレクトロニクス
    "9602.T",  # 東宝
    "2432.T",  # DeNA
]

US_SYMBOLS = [
    # ── GAFAM + 主要テック ────────────────────────────────────────────────
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
    "AMD",    # Advanced Micro Devices
    "INTC",   # Intel
    "QCOM",   # Qualcomm
    "TXN",    # Texas Instruments
    "ADBE",   # Adobe
    "CRM",    # Salesforce
    "NOW",    # ServiceNow
    "IBM",    # IBM
    # ── 金融 ──────────────────────────────────────────────────────────────
    "BRK-B",  # Berkshire Hathaway
    "JPM",    # JPMorgan Chase
    "V",      # Visa
    "MA",     # Mastercard
    "BAC",    # Bank of America
    "WFC",    # Wells Fargo
    "GS",     # Goldman Sachs
    "MS",     # Morgan Stanley
    "AXP",    # American Express
    "PYPL",   # PayPal
    # ── ヘルスケア ────────────────────────────────────────────────────────
    "UNH",    # UnitedHealth
    "JNJ",    # Johnson & Johnson
    "LLY",    # Eli Lilly
    "ABBV",   # AbbVie
    "MRK",    # Merck
    "PFE",    # Pfizer
    "TMO",    # Thermo Fisher Scientific
    # ── 消費財・小売 ──────────────────────────────────────────────────────
    "PG",     # Procter & Gamble
    "KO",     # Coca-Cola
    "PEP",    # PepsiCo
    "WMT",    # Walmart
    "COST",   # Costco
    "MCD",    # McDonald's
    "SBUX",   # Starbucks
    "NKE",    # Nike
    "HD",     # Home Depot
    "DIS",    # Disney
    # ── エネルギー ────────────────────────────────────────────────────────
    "XOM",    # ExxonMobil
    "CVX",    # Chevron
    # ── 通信・インフラ ────────────────────────────────────────────────────
    "T",      # AT&T
    "VZ",     # Verizon
    # ── 重工業・素材 ──────────────────────────────────────────────────────
    "CAT",    # Caterpillar
    "BA",     # Boeing
    "GE",     # GE Aerospace
    "MMM",    # 3M
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
            # 配当利回り（小数 → % に変換して格納）
            "dy": round(
                float(
                    meta.get("dividendYield")
                    or meta.get("trailingAnnualDividendYield")
                    or 0
                ) * 100,
                4,
            ),
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
