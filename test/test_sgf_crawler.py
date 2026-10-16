"""棋譜収集の保存・再開・通信制限を外部通信なしで検証する。"""

from datetime import date
from email.message import Message
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from scripts.crawl_sgf import main
from src.sgf_crawler import (
    CrawlConfig, CrawlError, CrawlReport, MAX_RESPONSE_BYTES, OGSClient, OGS_ORIGIN, crawl_ogs,
)
from src.sgf_dataset import samples_from_sgf


SGF = b"(;GM[1]FF[4]SZ[9]RE[B+R];B[aa];W[bb];B[])"
SGF_OTHER = b"(;GM[1]FF[4]SZ[9]RE[W+R];B[cc];W[dd])"
LIST_URL = OGS_ORIGIN + "/api/v1/players/123/games/?page_size=50&page=1&ended__isnull=false&ordering=-ended"
NEXT_URL = OGS_ORIGIN + "/api/v1/players/123/games/?page=2"


def _game(game_id=1, **overrides):
    return dict({"id": game_id, "width": 9, "height": 9, "mode": "game",
                 "ended": "2026-01-02T10:00:00Z", "annulled": False,
                 "rules": "japanese", "komi": "6.50"}, **overrides)


def _page(games, next_url=None):
    return json.dumps({"results": games, "next": next_url}).encode()


def _client(responses):
    client = Mock()
    client.fetch.side_effect = lambda url: responses[url]
    return client


def _response(data):
    response = Mock()
    response.__enter__ = Mock(return_value=response)
    response.__exit__ = Mock(return_value=False)
    response.read.return_value = data
    return response


def _http_error(code, retry_after=None):
    headers = Message()
    if retry_after is not None:
        headers["Retry-After"] = retry_after
    return HTTPError(LIST_URL, code, "test", headers, io.BytesIO())


class SGFCrawlerTest(unittest.TestCase):
    """公開棋譜を取得して学習用ファイルへ保存する流れを検証する。"""

    def test_config_file_origin_and_defaults(self):
        """既定・明示設定ファイルから読み込み、未指定時は既定値を使う。"""
        with tempfile.TemporaryDirectory() as directory, \
                patch("scripts.crawl_sgf.PROJECT_ROOT", Path(directory)), \
                patch("scripts.crawl_sgf.crawl_ogs", return_value=CrawlReport()) as crawl, \
                patch("sys.stdout", new_callable=io.StringIO):
            path = Path(directory) / "config.json"
            cases = [(None, [], OGS_ORIGIN), ({}, [], OGS_ORIGIN),
                     ({"ogs_origin": "https://ogs.example:8443"}, [], "https://ogs.example:8443"),
                     ({"ogs_origin": "https://other.example"}, ["--config", str(path)], "https://other.example")]
            for settings, args, expected in cases:
                if settings is not None:
                    path.write_text(json.dumps(settings), encoding="utf-8")
                self.assertEqual(main(["--player-id", "123", *args]), 0)
                self.assertEqual(crawl.call_args.args[0].ogs_origin, expected)

    def test_bad_config_is_rejected_before_crawling(self):
        """指定ファイルの欠落・不正形式・不正 URL は通信前に拒否する。"""
        with tempfile.TemporaryDirectory() as directory, \
                patch("scripts.crawl_sgf.crawl_ogs") as crawl, \
                patch("sys.stderr", new_callable=io.StringIO):
            path = Path(directory) / "config.json"
            for content in (None, "{broken", "[]", '{"ogs_origin": null}',
                            '{"ogs_origin": "https://example.com/api"}'):
                if content is not None:
                    path.write_text(content, encoding="utf-8")
                with self.subTest(content=content), self.assertRaises(SystemExit) as error:
                    main(["--player-id", "123", "--config", str(path)])
                self.assertEqual(error.exception.code, 2)
            crawl.assert_not_called()

    def test_custom_origin_applies_to_robots_pagination_and_sgf(self):
        """設定した取得先で通信を統一し、別の取得先の履歴は混在させない。"""
        origin = "https://ogs.example:8443"
        with tempfile.TemporaryDirectory() as directory, \
                patch("src.sgf_crawler.build_opener") as opener, \
                patch("src.sgf_crawler.time.sleep"):
            opener.return_value.open.side_effect = [
                _response(b"User-agent: *\nAllow: /"),
                _response(_page([], NEXT_URL.replace(OGS_ORIGIN, origin))),
                _response(_page([_game(1)])), _response(SGF)]
            config = CrawlConfig((123,), Path(directory), ogs_origin=origin + "/")
            self.assertEqual(crawl_ogs(config).saved, 1)
            urls = [call.args[0].full_url for call in opener.return_value.open.call_args_list]
            self.assertEqual(urls, [origin + "/robots.txt", LIST_URL.replace(OGS_ORIGIN, origin),
                                    NEXT_URL.replace(OGS_ORIGIN, origin), origin + "/api/v1/games/1/sgf"])
            client = Mock()
            with self.assertRaisesRegex(CrawlError, "オリジンが異なります"):
                crawl_ogs(CrawlConfig((123,), Path(directory)), client)
            client.fetch.assert_not_called()

    def test_origin_validation(self):
        """HTTPS オリジン以外の値と不正なポートを拒否する。"""
        for origin in (None, "", "http://example.com", "https://user:pass@example.com",
                       "https://example.com/api", "https://example.com?x=1",
                       "https://example.com#part", "https://example.com:bad", "https://example.com:0",
                       "https://example.com:99999", "https://example.com\n"):
            with self.subTest(origin=origin), self.assertRaises(ValueError):
                CrawlConfig((123,), Path("unused"), ogs_origin=origin)

    def test_pagination_duplicates_and_resume(self):
        """ページをまたぐ重複を除去し、再実行時には SGF を再取得しない。"""
        with tempfile.TemporaryDirectory() as directory:
            config = CrawlConfig((123,), Path(directory))
            responses = {
                LIST_URL: _page([_game(1), _game(2)], NEXT_URL),
                NEXT_URL: _page([_game(1), _game(3)]),
                OGS_ORIGIN + "/api/v1/games/1/sgf": SGF,
                OGS_ORIGIN + "/api/v1/games/2/sgf": SGF,
                OGS_ORIGIN + "/api/v1/games/3/sgf": SGF_OTHER,
            }
            report = crawl_ogs(config, _client(responses))
            self.assertEqual((report.saved, report.duplicates, report.pages), (2, 1, 2))
            files = list(Path(directory).glob("*.sgf"))
            self.assertEqual(len(files), 2)
            self.assertTrue(all(samples_from_sgf(path)[0] == 9 for path in files))
            resume_client = _client({LIST_URL: responses[LIST_URL], NEXT_URL: responses[NEXT_URL]})
            report = crawl_ogs(config, resume_client)
            self.assertEqual(report.resumed, 3)
            self.assertEqual(resume_client.fetch.call_count, 2)
            manifest = json.loads((Path(directory) / "crawl_manifest.json").read_text())
            self.assertEqual(manifest["games"]["2"]["status"], "duplicate")
            self.assertEqual(manifest["games"]["1"]["metadata"]["komi"], "6.50")

    def test_filters_and_rejects_invalid_sgf(self):
        """対象外対局を取得せず、HTML・不正棋譜・サイズ不一致を保存しない。"""
        with tempfile.TemporaryDirectory() as directory:
            config = CrawlConfig((123,), Path(directory), board_size=9,
                                 since=date(2026, 1, 2), until=date(2026, 1, 2))
            games = [_game(1, width=19, height=19), _game(2, ended=None),
                     _game(3, annulled=True), _game(4, ended="2026-01-01T00:00:00Z"),
                     _game(5), _game(6), _game(7), _game(8, rengo=True)]
            client = _client({
                LIST_URL: _page(games),
                OGS_ORIGIN + "/api/v1/games/5/sgf": b"<html>Login required</html>",
                OGS_ORIGIN + "/api/v1/games/6/sgf": b"(;SZ[9]RE[?];B[aa])",
                OGS_ORIGIN + "/api/v1/games/7/sgf": SGF.replace(b"SZ[9]", b"SZ[19]"),
            })
            report = crawl_ogs(config, client)
            self.assertEqual((report.filtered, report.rejected, report.saved), (5, 3, 0))
            self.assertFalse(list(Path(directory).glob("*.sgf")))
            self.assertEqual(client.fetch.call_count, 4)
            resumed = _client({LIST_URL: _page(games)})
            self.assertEqual(crawl_ogs(config, resumed).rejected, 3)
            self.assertEqual(resumed.fetch.call_count, 1)

    def test_bounds_requests_and_repairs_missing_file(self):
        """SGF 件数を制限し、履歴だけ残った棋譜は再取得する。"""
        with tempfile.TemporaryDirectory() as directory:
            config = CrawlConfig((123,), Path(directory), max_games=1)
            client = _client({LIST_URL: _page([_game(1), _game(2)], NEXT_URL),
                              OGS_ORIGIN + "/api/v1/games/1/sgf": SGF})
            self.assertEqual(crawl_ogs(config, client).attempted, 1)
            self.assertEqual(client.fetch.call_count, 2)
            next(Path(directory).glob("*.sgf")).unlink()
            self.assertEqual(crawl_ogs(config, client).saved, 1)

    def test_page_limit_bounds_multiple_players(self):
        """対象外の対局ばかりでも全対局者合計のページ上限で停止する。"""
        with tempfile.TemporaryDirectory() as directory:
            config = CrawlConfig((123, 456), Path(directory), max_pages=1)
            client = _client({LIST_URL: _page([_game(1, ended=None)], NEXT_URL)})
            self.assertEqual(crawl_ogs(config, client).pages, 1)
            self.assertEqual(client.fetch.call_count, 1)

    def test_corrupt_saved_file_is_replaced(self):
        """保存済みファイルの内容が壊れた場合は再取得して修復する。"""
        with tempfile.TemporaryDirectory() as directory:
            config = CrawlConfig((123,), Path(directory))
            client = _client({LIST_URL: _page([_game(1)]),
                              OGS_ORIGIN + "/api/v1/games/1/sgf": SGF})
            crawl_ogs(config, client)
            path = next(Path(directory).glob("*.sgf"))
            path.write_bytes(SGF_OTHER)
            repair = _client({LIST_URL: _page([_game(1), _game(2)]),
                              OGS_ORIGIN + "/api/v1/games/1/sgf": SGF,
                              OGS_ORIGIN + "/api/v1/games/2/sgf": SGF_OTHER})
            self.assertEqual(crawl_ogs(config, repair).saved, 2)
            self.assertEqual(path.read_bytes(), SGF)
            self.assertEqual(len(list(Path(directory).glob("*.sgf"))), 2)

    def test_interrupt_preserves_progress_and_releases_lock(self):
        """途中で中断しても保存済み棋譜と取得履歴を保持する。"""
        with tempfile.TemporaryDirectory() as directory:
            config = CrawlConfig((123,), Path(directory))
            client = Mock()
            client.fetch.side_effect = [_page([_game(1), _game(2)]), SGF, KeyboardInterrupt]
            with self.assertRaises(KeyboardInterrupt):
                crawl_ogs(config, client)
            self.assertEqual(len(list(Path(directory).glob("*.sgf"))), 1)
            self.assertFalse((Path(directory) / ".crawl.lock").exists())
            manifest = json.loads((Path(directory) / "crawl_manifest.json").read_text())
            self.assertEqual(set(manifest["games"]), {"1"})

    def test_untrusted_next_and_invalid_json(self):
        """外部の次ページ URL と不正な API 応答で停止する。"""
        cases = [b"<html>error</html>", b"[]", b'{"results": [null]}',
                 _page([], "https://example.com/private"), _page([], LIST_URL)]
        for body in cases:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                client = _client({LIST_URL: body})
                with self.assertRaises(CrawlError):
                    crawl_ogs(CrawlConfig((123,), Path(directory)), client)
                self.assertEqual(client.fetch.call_count, 1)

    def test_corrupt_manifest_and_existing_lock_are_preserved(self):
        """壊れた取得履歴や別の収集処理のロックを上書きしない。"""
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            config = CrawlConfig((123,), output)
            manifest = output / "crawl_manifest.json"
            manifest.write_text("broken")
            with self.assertRaises(CrawlError):
                crawl_ogs(config, Mock())
            self.assertEqual(manifest.read_text(), "broken")
            lock = output / ".crawl.lock"
            lock.touch()
            with self.assertRaises(CrawlError):
                crawl_ogs(config, Mock())
            self.assertTrue(lock.exists())

    def test_invalid_arguments(self):
        """無限待機や無制限取得につながる設定を拒否する。"""
        for overrides in ({"max_games": 0}, {"max_pages": 0}, {"interval": float("nan")},
                          {"timeout": float("inf")}, {"retries": -1}, {"board_size": 7},
                          {"since": date(2026, 2, 1), "until": date(2026, 1, 1)}):
            with self.subTest(overrides=overrides), self.assertRaises(ValueError):
                CrawlConfig((123,), Path("unused"), **overrides)

    def test_cli_reports_network_failure(self):
        """通信失敗を終了コード1で呼び出し元に伝える。"""
        with patch("scripts.crawl_sgf.crawl_ogs", side_effect=CrawlError("offline")), \
                patch("sys.stdout", new_callable=io.StringIO), \
                patch("sys.stderr", new_callable=io.StringIO) as errors:
            self.assertEqual(main(["--player-id", "123"]), 1)
            self.assertIn("offline", errors.getvalue())


class OGSClientTest(unittest.TestCase):
    """ネットワークの代わりに応答を注入し、通信制御を検証する。"""

    def test_robots_delay_and_retry_after(self):
        """robots の間隔と HTTP 429 の待機指示を守って再試行する。"""
        with patch("src.sgf_crawler.build_opener") as opener, \
                patch("src.sgf_crawler.time.sleep") as sleep, \
                patch("src.sgf_crawler.time.monotonic", return_value=0):
            opener.return_value.open.side_effect = [
                _response(b"User-agent: *\nCrawl-delay: 4\nDisallow: /bad-robots"),
                _http_error(429, "5"), _response(SGF),
            ]
            client = OGSClient(CrawlConfig((123,), Path("unused")))
            self.assertEqual(client.fetch(LIST_URL), SGF)
            waits = [call.args[0] for call in sleep.call_args_list]
            self.assertIn(4, waits)
            self.assertIn(5, waits)
            self.assertEqual(opener.return_value.open.call_count, 3)

    def test_robots_denial_and_foreign_host(self):
        """禁止 URL や別ホストへ通信しない。"""
        with patch("src.sgf_crawler.build_opener") as opener:
            opener.return_value.open.return_value = _response(b"User-agent: *\nDisallow: /")
            client = OGSClient(CrawlConfig((123,), Path("unused")))
            with self.assertRaises(CrawlError):
                client.fetch("https://example.com/game.sgf")
            opener.return_value.open.assert_not_called()
            with self.assertRaises(CrawlError):
                client.fetch(LIST_URL)
            self.assertEqual(opener.return_value.open.call_count, 1)

    def test_long_rate_limit_stops_without_waiting_or_retrying(self):
        """長いアクセス制限を受けたら取得を停止する。"""
        with patch("src.sgf_crawler.build_opener") as opener, \
                patch("src.sgf_crawler.time.sleep") as sleep:
            opener.return_value.open.side_effect = [
                _response(b"User-agent: *\nAllow: /"), _http_error(429, "3600")]
            client = OGSClient(CrawlConfig((123,), Path("unused")))
            with self.assertRaisesRegex(CrawlError, "アクセス制限"):
                client.fetch(LIST_URL)
            self.assertEqual(opener.return_value.open.call_count, 2)
            self.assertTrue(all(call.args[0] < 3 for call in sleep.call_args_list))

    def test_network_failure_is_bounded_and_size_is_limited(self):
        """再試行を有限回に制限し、過大なレスポンスを拒否する。"""
        with patch("src.sgf_crawler.build_opener") as opener, patch("src.sgf_crawler.time.sleep"):
            opener.return_value.open.side_effect = URLError("offline")
            client = OGSClient(CrawlConfig((123,), Path("unused"), retries=1))
            with self.assertRaisesRegex(CrawlError, "通信失敗"):
                client.fetch(LIST_URL)
            self.assertEqual(opener.return_value.open.call_count, 2)
            opener.return_value.open.side_effect = None
            opener.return_value.open.return_value = _response(b"x" * (MAX_RESPONSE_BYTES + 1))
            with self.assertRaisesRegex(CrawlError, "サイズ上限"):
                client.fetch(LIST_URL)

    def test_missing_robots_allows_fetch_but_sgf_404_stops(self):
        """robots.txt の404のみ許容し、棋譜の404は再試行しない。"""
        with patch("src.sgf_crawler.build_opener") as opener, patch("src.sgf_crawler.time.sleep"):
            opener.return_value.open.side_effect = [_http_error(404), _http_error(404)]
            client = OGSClient(CrawlConfig((123,), Path("unused")))
            with self.assertRaisesRegex(CrawlError, "HTTP 404"):
                client.fetch(LIST_URL)
            self.assertEqual(opener.return_value.open.call_count, 2)


if __name__ == "__main__":
    unittest.main()
