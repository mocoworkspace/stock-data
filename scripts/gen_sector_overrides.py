"""優待銘柄の業種マッピングを yutai_data.dart から生成するスクリプト。

開発マシンで手動実行する（優待銘柄を追加・変更したとき）:
    python scripts/gen_sector_overrides.py

fetch_stocks.py の SECTOR_OVERRIDES マーカー間を書き換える。
"""

import pathlib
import re

YUTAI_DART = pathlib.Path(
    r"C:\workspace\stock_yutai_app\lib\data\yutai_data.dart")
FETCH_PY = pathlib.Path(__file__).parent / "fetch_stocks.py"

# 優待カテゴリ → 業種表示名
CATEGORY_TO_SECTOR = {
    "食品・飲料": "食品・飲料",
    "外食": "外食",
    "小売": "小売・サービス",
    "ドラッグストア": "小売・サービス",
    "百貨店": "小売・サービス",
    "交通・旅行": "運輸・交通",
    "娯楽・ホテル": "娯楽・レジャー",
    "娯楽・エンタメ": "娯楽・レジャー",
    "通信": "通信",
    "金融": "金融",
    "化粧品・日用品": "化粧品・日用品",
}


def main() -> None:
    src = YUTAI_DART.read_text(encoding="utf-8")
    items = re.findall(
        r"code: '(\d+)'.*?category: '([^']+)'", src, re.DOTALL)

    lines = ["SECTOR_OVERRIDES: dict[str, str] = {"]
    for code, cat in items:
        sector = CATEGORY_TO_SECTOR.get(cat, "その他")
        lines.append(f'    "{code}.T": "{sector}",')
    lines.append("}")
    block = "\n".join(lines)

    fetch_src = FETCH_PY.read_text(encoding="utf-8")
    new_src = re.sub(
        r"(# >>> SECTOR_OVERRIDES_START\n).*?(\n# <<< SECTOR_OVERRIDES_END)",
        lambda m: m.group(1) + block + m.group(2),
        fetch_src,
        flags=re.DOTALL,
    )
    FETCH_PY.write_text(new_src, encoding="utf-8")
    print(f"SECTOR_OVERRIDES を {len(items)} 銘柄分更新しました")


if __name__ == "__main__":
    main()
