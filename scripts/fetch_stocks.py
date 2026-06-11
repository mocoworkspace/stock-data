"""
株価データ取得スクリプト
GitHub Actions から実行し、stocks.json を生成して GitHub Pages で配信する。

取得対象:
  - 日本株（東証）: JST 16:00 以降（東証終値確定後）
  - 米国株（NYSE/NASDAQ）: JST 07:00 以降（米国終値確定後）
"""

import json
import re
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
    "9984.T",  # ソフトバンクグループ
    "6758.T",  # ソニーグループ
    "6861.T",  # キーエンス
    "8035.T",  # 東京エレクトロン
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
    "7203.T",  # トヨタ自動車
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
    "9432.T",  # NTT
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
    # ── 株主優待 追加銘柄 ────────────────────────────────────────────────
    "4661.T",  # オリエンタルランド（ディズニー）
    "2702.T",  # 日本マクドナルドHD
    "9843.T",  # ニトリHD
    "2267.T",  # ヤクルト本社
    "3543.T",  # コメダHD
    "9887.T",  # 松屋フーズHD
    "7550.T",  # ゼンショーHD（すき家・はま寿司）
    "3397.T",  # トリドールHD（丸亀製麺）
    "8153.T",  # モスフードサービス
    "9873.T",  # 日本KFCホールディングス
    "9831.T",  # ヤマダHD
    "2730.T",  # エディオン
    "8233.T",  # 高島屋
    "9041.T",  # 近鉄グループHD
    "9042.T",  # 阪急阪神HD
    "2897.T",  # 日清食品HD
    "2229.T",  # カルビー
    "2695.T",  # くら寿司
    "9936.T",  # 王将フードサービス
    "7581.T",  # サイゼリヤ
    "3563.T",  # FOOD & LIFE COMPANIES（スシロー）
    "3141.T",  # ウエルシアHD
    "3391.T",  # ツルハHD
    "3088.T",  # マツキヨコクミンHD
    "9605.T",  # 東映
    "9601.T",  # 松竹
    "4680.T",  # ラウンドワン
    "2875.T",  # 東洋水産（マルちゃん）
    "2811.T",  # カゴメ
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
    # ── 国内ETF（上場投資信託） ───────────────────────────────────────────
    "1306.T",  # NEXT FUNDS TOPIX連動型
    "1321.T",  # NEXT FUNDS 日経225連動型
    "1343.T",  # NEXT FUNDS 東証REIT指数連動型
    "1489.T",  # NEXT FUNDS 日経高配当株50
    "1478.T",  # iシェアーズ MSCI ジャパン高配当利回り
    "1476.T",  # iシェアーズ・コア Jリート
    "1655.T",  # iシェアーズ S&P500 米国株
    "2558.T",  # MAXIS米国株式（S&P500）
    "2559.T",  # MAXIS全世界株式（オール・カントリー）
    "2631.T",  # MAXISナスダック100
    "1545.T",  # NEXT FUNDS NASDAQ-100連動型
    "1570.T",  # NEXT FUNDS 日経レバレッジ
    "1540.T",  # 純金上場信託（金の果実）
    "1698.T",  # 上場インデックスファンド日本高配当
    "2244.T",  # グローバルX US テック・トップ20
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
    # ── 米国ETF ───────────────────────────────────────────────────────────
    "VOO",    # Vanguard S&P500
    "VTI",    # Vanguard Total Stock Market
    "VT",     # Vanguard Total World Stock
    "QQQ",    # Invesco QQQ（NASDAQ100）
    "SPY",    # SPDR S&P500
    "VYM",    # Vanguard 高配当株
    "HDV",    # iShares 高配当株
    "SPYD",   # SPDR S&P500 高配当株
    "SCHD",   # Schwab 米国配当株
    "JEPI",   # JPMorgan カバードコール（毎月分配）
    "TLT",    # iShares 米国債20年超
    "GLD",    # SPDR ゴールド
]

# 主要株価指数（ウォッチリスト上部に表示）
INDEX_SYMBOLS = [
    "^N225",   # 日経225
    "^GSPC",   # S&P500
    "^IXIC",   # NASDAQ総合
]

ALL_SYMBOLS = INDEX_SYMBOLS + JAPAN_SYMBOLS + US_SYMBOLS

# ── 業種マッピング ──────────────────────────────────────────────────────────
# シンボルリストのセクションコメント（# ── 名前 ──）から業種を自動判定する。
# 優待銘柄ブロックは業種が混在するため SECTOR_OVERRIDES で個別に補完する。

_SECTION_TO_SECTOR = {
    "日経225: テクノロジー・電機": "テクノロジー",
    "日経225: 金融": "金融",
    "日経225: 自動車・輸送機器": "自動車・輸送",
    "日経225: 製薬・ヘルスケア": "製薬・ヘルスケア",
    "日経225: 商社": "商社",
    "日経225: 通信": "通信",
    "日経225: 素材・化学": "素材・化学",
    "日経225: エネルギー・電力": "エネルギー",
    "日経225: 建設・不動産": "建設・不動産",
    "日経225: 運輸・交通": "運輸・交通",
    "日経225: 食品・飲料": "食品・飲料",
    "日経225: 小売・サービス": "小売・サービス",
    "成長株・注目銘柄": "成長・新興",
    "国内ETF（上場投資信託）": "ETF",
    "GAFAM + 主要テック": "テクノロジー",
    "金融": "金融",
    "ヘルスケア": "製薬・ヘルスケア",
    "消費財・小売": "小売・サービス",
    "エネルギー": "エネルギー",
    "通信・インフラ": "通信",
    "重工業・素材": "素材・化学",
    "米国ETF": "ETF",
}

# 優待銘柄ブロック用（gen_sector_overrides.py で yutai_data.dart から生成）
# >>> SECTOR_OVERRIDES_START
SECTOR_OVERRIDES: dict[str, str] = {
    "2502.T": "食品・飲料",
    "2503.T": "食品・飲料",
    "2802.T": "食品・飲料",
    "3197.T": "外食",
    "9861.T": "外食",
    "7412.T": "外食",
    "8267.T": "小売・サービス",
    "3099.T": "小売・サービス",
    "3086.T": "小売・サービス",
    "3048.T": "小売・サービス",
    "3382.T": "小売・サービス",
    "9201.T": "運輸・交通",
    "9202.T": "運輸・交通",
    "9022.T": "運輸・交通",
    "4681.T": "娯楽・レジャー",
    "4661.T": "娯楽・レジャー",
    "2702.T": "外食",
    "3543.T": "外食",
    "9887.T": "外食",
    "9433.T": "通信",
    "9843.T": "小売・サービス",
    "2267.T": "食品・飲料",
    "7550.T": "外食",
    "3397.T": "外食",
    "8153.T": "外食",
    "9831.T": "小売・サービス",
    "2730.T": "小売・サービス",
    "8233.T": "小売・サービス",
    "9020.T": "運輸・交通",
    "9021.T": "運輸・交通",
    "9041.T": "運輸・交通",
    "9042.T": "運輸・交通",
    "2897.T": "食品・飲料",
    "2229.T": "食品・飲料",
    "2810.T": "食品・飲料",
    "9434.T": "通信",
    "2695.T": "外食",
    "9936.T": "外食",
    "3563.T": "外食",
    "3391.T": "小売・サービス",
    "3088.T": "小売・サービス",
    "9605.T": "娯楽・レジャー",
    "9601.T": "娯楽・レジャー",
    "4680.T": "娯楽・レジャー",
    "2875.T": "食品・飲料",
    "2811.T": "食品・飲料",
    "7616.T": "外食",
    "3387.T": "外食",
    "8200.T": "外食",
    "7611.T": "外食",
    "2705.T": "外食",
    "3193.T": "外食",
    "3097.T": "外食",
    "7630.T": "外食",
    "4665.T": "外食",
    "8179.T": "外食",
    "9828.T": "外食",
    "3399.T": "外食",
    "2801.T": "食品・飲料",
    "2593.T": "食品・飲料",
    "2212.T": "食品・飲料",
    "2201.T": "食品・飲料",
    "2206.T": "食品・飲料",
    "2264.T": "食品・飲料",
    "2282.T": "食品・飲料",
    "2809.T": "食品・飲料",
    "2220.T": "食品・飲料",
    "1332.T": "食品・飲料",
    "2579.T": "食品・飲料",
    "7532.T": "小売・サービス",
    "7545.T": "小売・サービス",
    "8227.T": "小売・サービス",
    "9989.T": "小売・サービス",
    "7649.T": "小売・サービス",
    "3038.T": "小売・サービス",
    "8194.T": "小売・サービス",
    "9948.T": "小売・サービス",
    "9001.T": "運輸・交通",
    "9005.T": "運輸・交通",
    "9007.T": "運輸・交通",
    "9008.T": "運輸・交通",
    "9006.T": "運輸・交通",
    "9009.T": "運輸・交通",
    "9003.T": "運輸・交通",
    "9024.T": "運輸・交通",
    "9142.T": "運輸・交通",
    "9603.T": "運輸・交通",
    "9722.T": "娯楽・レジャー",
    "9602.T": "娯楽・レジャー",
    "9633.T": "娯楽・レジャー",
    "4343.T": "娯楽・レジャー",
    "7458.T": "娯楽・レジャー",
    "9432.T": "通信",
    "4755.T": "通信",
    "9436.T": "通信",
    "8473.T": "金融",
    "4911.T": "化粧品・日用品",
    "4927.T": "化粧品・日用品",
}
# <<< SECTOR_OVERRIDES_END


# 優待ブロックにあるが yutai_data に存在しない銘柄の業種（手動指定）
_EXTRA_SECTORS = {
    "2914.T": "食品・飲料",      # JT
    "9983.T": "小売・サービス",  # ファーストリテイリング
    "3092.T": "小売・サービス",  # ZOZO
    "9412.T": "通信",            # スカパーJSAT
    "8001.T": "商社",            # 伊藤忠商事
    "8058.T": "商社",            # 三菱商事
    "9873.T": "外食",            # 日本KFC（上場廃止・取得失敗想定）
    "7581.T": "外食",            # サイゼリヤ
    "3141.T": "小売・サービス",  # ウエルシアHD
}


def _build_sectors() -> dict[str, str]:
    """自ファイルのセクションコメントを解析して symbol → 業種 を作る"""
    import pathlib

    src = pathlib.Path(__file__).read_text(encoding="utf-8")
    header_re = re.compile(r"#\s*──\s*(.+?)\s*─")
    symbol_re = re.compile(r'^\s*"([^"]+)",')

    sectors: dict[str, str] = {}
    current: str | None = None
    for line in src.splitlines():
        if line.startswith("INDEX_SYMBOLS"):
            break
        m = header_re.search(line)
        if m:
            current = _SECTION_TO_SECTOR.get(m.group(1))
            continue
        m = symbol_re.match(line)
        if m and current:
            sectors[m.group(1)] = current
    sectors.update(_EXTRA_SECTORS)
    sectors.update(SECTOR_OVERRIDES)
    return sectors


SECTORS = _build_sectors()

# Yahoo の銘柄名が分かりにくい国内ETFは日本語名で上書き（検索性向上）
NAME_OVERRIDES = {
    "1306.T": "TOPIX連動型ETF（NF）",
    "1321.T": "日経225連動型ETF（NF）",
    "1343.T": "東証REIT指数ETF（NF）",
    "1489.T": "日経高配当株50 ETF（NF）",
    "1478.T": "MSCIジャパン高配当ETF（iシェアーズ）",
    "1476.T": "JリートETF（iシェアーズ・コア）",
    "1655.T": "S&P500米国株ETF（iシェアーズ）",
    "2558.T": "米国株式S&P500 ETF（MAXIS）",
    "2559.T": "全世界株式オルカンETF（MAXIS）",
    "2631.T": "ナスダック100 ETF（MAXIS）",
    "1545.T": "NASDAQ-100連動型ETF（NF）",
    "1570.T": "日経レバレッジETF（NF）",
    "1540.T": "純金上場信託（金の果実）",
    "1698.T": "日本高配当ETF（上場インデックス）",
    "2244.T": "USテック・トップ20 ETF（グローバルX）",
}

# ── ユーティリティ ──────────────────────────────────────────────────────────

HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; StockDataBot/1.0)"}
REQUEST_TIMEOUT = 15
# GitHub Actions の IP 制限を避けるため控えめなレート
SLEEP_BETWEEN_REQUESTS = 0.8  # 秒


def fetch_stock(symbol: str) -> dict | None:
    """1銘柄の EOD データを Yahoo Finance から取得する

    range=1y + events=div で過去1年の配当履歴も取得し、
    実績ベースの年間1株配当（dps）を算出する。
    """
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
        "?interval=1d&range=1y&includePrePost=false&events=div"
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

        # 過去1年の配当イベント合計 = 実績ベースの年間1株配当（DPS）
        div_events = result.get("events", {}).get("dividends", {})
        one_year_ago = time.time() - 365 * 24 * 3600
        dps = sum(
            float(d.get("amount", 0))
            for d in div_events.values()
            if float(d.get("date", 0)) >= one_year_ago
        )

        return {
            "s": symbol,
            "n": NAME_OVERRIDES.get(symbol)
            or meta.get("shortName")
            or meta.get("longName")
            or symbol,
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
            # 年間1株配当（過去1年の配当実績の合計）
            "dps": round(dps, 4),
            # 業種（セクションコメント + 優待カテゴリから判定）
            "sec": SECTORS.get(symbol, "その他"),
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
