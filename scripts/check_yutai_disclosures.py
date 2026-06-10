#!/usr/bin/env python3
"""TDnet（適時開示情報閲覧サービス）から株主優待関連の開示を検知するスクリプト。

仕組み:
  1. 過去 DAYS_BACK 日分の TDnet 開示一覧ページ（公式・公開）を取得
  2. 監視対象銘柄（yutai_codes.json）かつ表題に「株主優待」を含む開示を抽出
  3. ヒットがあれば yutai_report.md を出力（GitHub Actions が Issue 化する）

負荷について:
  - 公式 TDnet サイトは適時開示を広く伝達するための公開インフラ
  - 取得は週1回・1リクエスト/秒以下に制限（SLEEP 参照）
  - 404（休日等でページなし）は即スキップ
"""

import json
import re
import time
import urllib.error
import urllib.request
from datetime import date, timedelta
from pathlib import Path

BASE = "https://www.release.tdnet.info/inbs"
DAYS_BACK = 8  # 週1実行 + 1日の重複バッファ（取りこぼし防止）
SLEEP = 1.2  # リクエスト間隔（秒）: 相手サーバーへの負荷を抑える
MAX_PAGES_PER_DAY = 30  # 1日あたりの一覧ページ上限（暴走防止）
KEYWORD = "株主優待"
REPORT_PATH = Path("yutai_report.md")

# 一覧ページの1行から 時刻・コード・社名・表題・PDFリンク を抽出
# class 属性は "oddnew-L kjTime" のような複合クラスなので前方一致にしない
ROW_RE = re.compile(
    r'class="[^"]*kjTime"[^>]*>\s*([\d:]+)\s*<.*?'
    r'class="[^"]*kjCode"[^>]*>\s*(\d{4,5})\s*<.*?'
    r'class="[^"]*kjName"[^>]*>\s*(.*?)\s*<.*?'
    r'class="[^"]*kjTitle"[^>]*>.*?<a[^>]*href="([^"]+)"[^>]*>\s*(.*?)\s*</a>',
    re.DOTALL,
)


def load_watch_codes() -> dict:
    """監視対象の銘柄コード（4桁） → 銘柄名"""
    path = Path(__file__).parent / "yutai_codes.json"
    return json.loads(path.read_text(encoding="utf-8"))


def fetch(url: str) -> str | None:
    req = urllib.request.Request(
        url, headers={"User-Agent": "stock-data-yutai-checker/1.0"}
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None  # 休日・ページなし
        raise


def check_day(ymd: str, watch: dict) -> list[dict]:
    """1日分の開示一覧を全ページ走査して該当開示を返す"""
    hits = []
    for page in range(1, MAX_PAGES_PER_DAY + 1):
        url = f"{BASE}/I_list_{page:03d}_{ymd}.html"
        html = fetch(url)
        time.sleep(SLEEP)
        if html is None:
            break  # この日のページはここまで

        rows = ROW_RE.findall(html)
        if not rows:
            break

        for jiko, code5, name, href, title in rows:
            code4 = code5[:4]  # TDnet は5桁コード（4桁 + チェック桁）
            title_clean = re.sub(r"<[^>]+>", "", title)
            if code4 in watch and KEYWORD in title_clean:
                hits.append(
                    {
                        "date": ymd,
                        "time": jiko,
                        "code": code4,
                        "name": re.sub(r"<[^>]+>", "", name),
                        "title": title_clean,
                        "pdf": f"{BASE}/{href}",
                    }
                )
    return hits


def main() -> None:
    watch = load_watch_codes()
    print(f"監視対象: {len(watch)} 銘柄 / 過去 {DAYS_BACK} 日分をチェック")

    all_hits = []
    today = date.today()
    for delta in range(DAYS_BACK):
        d = today - timedelta(days=delta)
        ymd = d.strftime("%Y%m%d")
        hits = check_day(ymd, watch)
        if hits:
            print(f"  {ymd}: {len(hits)} 件ヒット")
        all_hits.extend(hits)

    if not all_hits:
        print("該当する開示はありませんでした。")
        return

    # Issue 本文（Markdown）を生成
    lines = [
        "TDnet で監視対象銘柄の株主優待関連の開示を検知しました。",
        "開示PDF（一次情報）を確認し、必要なら `stock_yutai_app` の",
        "`lib/data/yutai_data.dart` を更新してください。",
        "",
        "| 開示日時 | コード | 銘柄 | 表題 |",
        "|---|---|---|---|",
    ]
    for h in all_hits:
        lines.append(
            f"| {h['date']} {h['time']} | {h['code']} | {h['name']} "
            f"| [{h['title']}]({h['pdf']}) |"
        )
    lines += [
        "",
        "確認観点: 廃止か / 権利確定月の変更か / 内容・必要株数の変更か",
    ]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(all_hits)} 件を {REPORT_PATH} に出力しました。")


if __name__ == "__main__":
    main()
