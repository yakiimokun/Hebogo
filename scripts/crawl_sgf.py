#!/usr/bin/env python3
"""OGS の対局者別公開棋譜を収集するコマンド。"""

from __future__ import annotations

import argparse
from datetime import date
import json
from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.sgf_crawler import CrawlConfig, CrawlError, OGS_ORIGIN, crawl_ogs  # noqa: E402


def _load_origin(path: Path | None) -> str:
    """設定から取得先を読み、既定ファイルやキーの未指定時は OGS を使う。"""
    config_path = path if path is not None else PROJECT_ROOT / "config.json"
    if path is None and not config_path.exists():
        return OGS_ORIGIN
    settings = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(settings, dict):
        raise ValueError("設定ファイルは JSON オブジェクトで指定してください")
    return settings.get("ogs_origin", OGS_ORIGIN)


def main(argv: list[str] | None = None) -> int:
    """引数に従って棋譜を収集し、結果と終了コードを返す。

    Args:
        argv: コマンドライン引数。None の場合は実行時の引数を使用する。

    Returns:
        正常終了時は0、通信・保存エラー時は1、中断時は130。
        引数が不正な場合は argparse が終了コード2で終了する。
    """
    parser = argparse.ArgumentParser(description="OGS の公開棋譜を検証して SGF として保存します。")
    parser.add_argument("--config", type=Path, help="設定ファイル（既定はリポジトリ直下の config.json）")
    parser.add_argument("--player-id", type=int, action="append", required=True,
                        help="OGS の対局者 ID（複数指定可）。プロフィール URL の数値")
    parser.add_argument("--output", type=Path, default=PROJECT_ROOT / "data/sgf/raw/ogs")
    parser.add_argument("--board-size", type=int, choices=(9, 13, 19))
    parser.add_argument("--max-games", type=int, default=100, help="SGF 取得試行上限（既定100）")
    parser.add_argument("--max-pages", type=int, default=20, help="全対局者合計の一覧ページ上限（既定20）")
    parser.add_argument("--start-page", type=int, default=1, help="各対局者の開始ページ（既定1）")
    parser.add_argument("--since", type=date.fromisoformat, help="UTC 終局日の下限 YYYY-MM-DD（当日を含む）")
    parser.add_argument("--until", type=date.fromisoformat, help="UTC 終局日の上限 YYYY-MM-DD（当日を含む）")
    parser.add_argument("--interval", type=float, default=2, help="取得間隔の下限秒数（既定2、最小1）")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--retries", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        config = CrawlConfig(player_ids=tuple(args.player_id), output=args.output,
                             board_size=args.board_size, max_games=args.max_games,
                             max_pages=args.max_pages, start_page=args.start_page,
                             since=args.since, until=args.until, interval=args.interval,
                             timeout=args.timeout, retries=args.retries,
                             ogs_origin=_load_origin(args.config))
    except (OSError, ValueError) as error:
        parser.error(str(error))
    print(f"OGS から収集します。保存先: {config.output}", flush=True)
    try:
        report = crawl_ogs(config)
    except (CrawlError, OSError) as error:
        print(f"エラー: {error}\n保存済みの棋譜は残っています。同じ引数で再実行できます。", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n収集を中断しました。保存済みの棋譜は残っています。", file=sys.stderr)
        return 130
    print(f"完了: 新規 {report.saved} / 重複 {report.duplicates} / 取得済み {report.resumed} / "
          f"不正SGF {report.rejected} / 条件外 {report.filtered} / 一覧 {report.pages}ページ")
    if report.pages >= config.max_pages:
        print("一覧ページ上限に達しました。さらに遡るには --max-pages または --start-page を調整してください。")
    if report.attempted >= config.max_games:
        print("SGF 取得上限に達しました。続きは同じ引数で再実行できます。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
