"""OGS の公開 API から学習に利用できる SGF を収集する。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from email.utils import parsedate_to_datetime
import hashlib
from http.client import HTTPException
import json
import math
import os
from pathlib import Path
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from .sgf_dataset import SGFError, samples_from_sgf


OGS_ORIGIN = "https://online-go.com"
USER_AGENT = "HebogoSGFCrawler/1.0"
MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class CrawlError(RuntimeError):
    """通信や API 応答の問題により収集を続行できないことを表す。"""


@dataclass(frozen=True)
class CrawlConfig:
    """収集対象と通信制限を保持する。

    Attributes:
        player_ids: OGS の対局者 ID。
        output: SGF と取得履歴を保存するディレクトリ。
        board_size: 対象の盤面サイズ。None は 9・13・19 路すべて。
        max_games: 1回の実行で取得を試みる SGF の上限。再取得不要の棋譜は除く。
        max_pages: 全対局者を通じた一覧ページ数の上限。
        start_page: 各対局者の一覧を読み始めるページ番号。
        interval: リクエスト間隔の下限（秒）。
        timeout: 1回の通信のタイムアウト（秒）。
        retries: 一時的な通信障害に対する追加試行回数。
        since: 終局日の下限（UTC、当日を含む）。None は制限なし。
        until: 終局日の上限（UTC、当日を含む）。None は制限なし。
        ogs_origin: OGS 互換 API の HTTPS オリジン。パスや認証情報は指定不可。
    """

    player_ids: tuple[int, ...]
    output: Path
    board_size: int | None = None
    max_games: int = 100
    max_pages: int = 20
    start_page: int = 1
    interval: float = 2.0
    timeout: float = 20.0
    retries: int = 3
    since: date | None = None
    until: date | None = None
    ogs_origin: str = OGS_ORIGIN

    def __post_init__(self) -> None:
        if not isinstance(self.ogs_origin, str) or any(c.isspace() for c in self.ogs_origin):
            raise ValueError("ogs_origin は HTTPS のオリジンを文字列で指定してください")
        origin = urlsplit(self.ogs_origin)
        if (origin.scheme != "https" or not origin.hostname or origin.username is not None
                or origin.password is not None or origin.path not in ("", "/")
                or origin.query or origin.fragment):
            raise ValueError("ogs_origin はパス・認証情報・クエリを含まない HTTPS URL にしてください")
        # 不正なポート指定も通信前に検出する。
        if origin.port == 0:
            raise ValueError("ogs_origin のポート番号は1以上にしてください")
        if not self.player_ids or any(type(p) is not int or p < 1 for p in self.player_ids):
            raise ValueError("対局者 ID は1以上の整数で指定してください")
        if self.board_size not in (None, 9, 13, 19):
            raise ValueError("盤面サイズは9・13・19のいずれかです")
        for name in ("max_games", "max_pages", "start_page"):
            if type(getattr(self, name)) is not int or getattr(self, name) < 1:
                raise ValueError(f"{name} は1以上の整数で指定してください")
        if not math.isfinite(self.interval) or self.interval < 1:
            raise ValueError("取得間隔は1秒以上で指定してください")
        if not math.isfinite(self.timeout) or self.timeout <= 0:
            raise ValueError("タイムアウトは正の有限値で指定してください")
        if type(self.retries) is not int or not 0 <= self.retries <= 10:
            raise ValueError("再試行回数は0〜10で指定してください")
        if self.since and self.until and self.since > self.until:
            raise ValueError("開始日は終了日以前にしてください")


@dataclass
class CrawlReport:
    """今回の実行件数を保持する。

    Attributes:
        pages: 読み込んだ一覧ページ数。
        attempted: SGF の取得を試みた件数。
        saved: 新規保存した件数。
        duplicates: 同一内容の保存済み SGF があった件数。
        resumed: 取得履歴とファイルを確認して再取得を省略した件数。
        rejected: 学習に使えない SGF の件数。
        filtered: 盤面サイズ・期間・対局状態による除外件数。
    """

    pages: int = 0
    attempted: int = 0
    saved: int = 0
    duplicates: int = 0
    resumed: int = 0
    rejected: int = 0
    filtered: int = 0


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # 認証画面や外部ホストへの転送を、自動的にたどらない。
        return None


class OGSClient:
    """取得間隔・再試行・robots.txt を考慮して OGS に接続する。"""

    def __init__(self, config: CrawlConfig):
        """通信設定を受け取り、接続前のクライアントを構築する。

        Args:
            config: 取得間隔、タイムアウト、再試行回数を含む設定。
        """
        self._config = config
        self._opener = build_opener(_NoRedirect())
        self._last_request: float | None = None
        self._robots: RobotFileParser | None = None
        self._interval = config.interval

    def fetch(self, url: str) -> bytes:
        """設定したオリジンの内容をサイズ制限付きで取得する。

        Args:
            url: 設定した OGS 互換 API の HTTPS URL。

        Returns:
            応答本文のバイト列。

        Raises:
            CrawlError: 対象外 URL、アクセス禁止、通信失敗、不正な応答の場合。
        """
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.netloc != urlsplit(self._config.ogs_origin).netloc:
            raise CrawlError(f"設定したオリジン以外の URL は取得しません: {url}")
        if self._robots is None:
            self._load_robots()
        if not self._robots.can_fetch(USER_AGENT, url):
            raise CrawlError(f"robots.txt により取得できません: {url}")
        try:
            return self._request(url)
        except HTTPError as error:
            raise CrawlError(f"HTTP {error.code}: {url}") from error

    def _load_robots(self) -> None:
        """robots.txt を確認し、明示された待機時間も採用する。"""
        url = self._config.ogs_origin.rstrip("/") + "/robots.txt"
        try:
            text = self._request(url).decode("utf-8")
        except HTTPError as error:
            if error.code != 404:
                raise CrawlError(f"robots.txt の取得失敗: HTTP {error.code}") from error
            text = "User-agent: *\nAllow: /"
        except UnicodeError as error:
            raise CrawlError("robots.txt の文字コードが不正です") from error
        robots = RobotFileParser(url)
        robots.parse(text.splitlines())
        delay = robots.crawl_delay(USER_AGENT)
        rate = robots.request_rate(USER_AGENT)
        self._interval = max(self._interval, delay or 0)
        if rate and rate.requests > 0:
            self._interval = max(self._interval, rate.seconds / rate.requests)
        self._robots = robots

    def _request(self, url: str) -> bytes:
        """一時エラーだけを再試行し、Retry-After を待機時間に反映する。"""
        for attempt in range(self._config.retries + 1):
            if self._last_request is not None:
                time.sleep(max(0, self._interval - (time.monotonic() - self._last_request)))
            self._last_request = time.monotonic()
            request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
            delay = 2 ** (attempt + 1)
            try:
                with self._opener.open(request, timeout=self._config.timeout) as response:
                    data = response.read(MAX_RESPONSE_BYTES + 1)
                if len(data) > MAX_RESPONSE_BYTES:
                    raise CrawlError("応答がサイズ上限（8 MiB）を超えています")
                return data
            except HTTPError as error:
                error.close()
                if error.code not in (429, 500, 502, 503, 504):
                    raise
                retry_after = error.headers.get("Retry-After")
                if retry_after:
                    try:
                        delay = max(delay, int(retry_after))
                    except ValueError:
                        try:
                            when = parsedate_to_datetime(retry_after)
                            delay = max(delay, when.timestamp() - time.time())
                        except (TypeError, ValueError, OverflowError):
                            pass
                # 長時間の制限中は次の棋譜にも進まず、実行全体を停止する。
                if error.code == 429 and (delay > 60 or attempt == self._config.retries):
                    raise CrawlError(f"アクセス制限中です。{delay:.0f}秒以上待って再実行してください") from error
                if attempt == self._config.retries:
                    raise CrawlError(f"再試行後も HTTP {error.code}: {url}") from error
            except (URLError, TimeoutError, OSError, HTTPException) as error:
                if attempt == self._config.retries:
                    raise CrawlError(f"通信失敗: {url}: {error}") from error
            if delay > 60:
                raise CrawlError(f"サーバーが {delay:.0f} 秒の待機を要求しています。後で再実行してください")
            time.sleep(delay)
        raise CrawlError("通信を完了できませんでした")


def _atomic_write(path: Path, data: bytes) -> None:
    """同じディレクトリの一時ファイルを置換し、不完全な保存を避ける。"""
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(data)
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def _load_manifest(path: Path) -> dict:
    """過去の取得履歴を読み、破損した履歴は上書きせずエラーにする。"""
    if not path.exists():
        return {"version": 1, "source": "ogs", "games": {}}
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(manifest, dict) or manifest.get("version") != 1
                or manifest.get("source") != "ogs" or not isinstance(manifest.get("games"), dict)
                or not all(isinstance(entry, dict) for entry in manifest["games"].values())):
            raise ValueError("履歴形式が不正です")
        return manifest
    except (ValueError, UnicodeError) as error:
        raise CrawlError(f"取得履歴を読み込めません: {path}: {error}") from error


def _matches(game: dict, config: CrawlConfig) -> bool:
    """完了済みの通常対局を、盤面サイズと UTC 終局日で絞り込む。"""
    size = game.get("width")
    if (not game.get("ended") or game.get("annulled") or game.get("rengo")
            or game.get("mode") != "game" or size not in (9, 13, 19)
            or size != game.get("height")
            or (config.board_size is not None and config.board_size != size)):
        return False
    try:
        ended = datetime.fromisoformat(game["ended"].replace("Z", "+00:00"))
        if ended.tzinfo is None:
            return False
        day = ended.astimezone(timezone.utc).date()
    except (TypeError, ValueError, AttributeError):
        return False
    return (config.since is None or day >= config.since) and (config.until is None or day <= config.until)


def crawl_ogs(config: CrawlConfig, client: OGSClient | None = None) -> CrawlReport:
    """対局者別に公開棋譜を取得し、検証済み SGF と取得履歴を保存する。

    同一バイト列の SGF は SHA-256 で重複を判定する。保存済みファイルを
    確認して取得を省略するため、同じ設定で再実行できる。同時実行は不可。

    Args:
        config: 収集対象、出力先、取得上限を指定した設定。
        client: 通信クライアント。None の場合は設定から生成する。

    Returns:
        今回の取得・保存・除外件数。

    Raises:
        CrawlError: API 形式、取得履歴、通信、アクセス制限に問題がある場合。
        OSError: ファイルの読み書きに失敗した場合。

    Example:
        crawl_ogs(CrawlConfig((12345,), Path("data/sgf/raw/ogs"), max_games=10))
    """
    config.output.mkdir(parents=True, exist_ok=True)
    lock = config.output / ".crawl.lock"
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise CrawlError(f"収集中か、前回のロックが残っています: {lock}") from error
    try:
        os.close(descriptor)
        return _crawl(config, client or OGSClient(config))
    finally:
        lock.unlink(missing_ok=True)


def _crawl(config: CrawlConfig, client: OGSClient) -> CrawlReport:
    """取得履歴を1局ずつ保存しながら、上限内で一覧を巡回する。"""
    manifest_path = config.output / "crawl_manifest.json"
    manifest = _load_manifest(manifest_path)
    origin = config.ogs_origin.rstrip("/")
    if manifest["games"] and manifest.get("origin", OGS_ORIGIN) != origin:
        raise CrawlError("取得履歴のオリジンが異なります。--output で別の保存先を指定してください")
    manifest["origin"] = origin
    hashes = {}
    for path in sorted(config.output.rglob("*")):
        if path.is_file() and path.suffix.lower() == ".sgf":
            hashes[hashlib.sha256(path.read_bytes()).hexdigest()] = path.relative_to(config.output).as_posix()
    report = CrawlReport()
    seen_games: set[int] = set()
    for player in dict.fromkeys(config.player_ids):
        query = urlencode({"page_size": 50, "page": config.start_page,
                           "ended__isnull": "false", "ordering": "-ended"})
        list_path = f"/api/v1/players/{player}/games/"
        url = origin + list_path + "?" + query
        seen_pages: set[str] = set()
        while url and report.pages < config.max_pages and report.attempted < config.max_games:
            parts = urlsplit(url)
            if (parts.scheme != "https" or parts.netloc != urlsplit(origin).netloc
                    or parts.path != list_path or url in seen_pages):
                raise CrawlError(f"一覧の次ページ URL が不正です: {url}")
            seen_pages.add(url)
            try:
                page = json.loads(client.fetch(url))
            except (ValueError, UnicodeError) as error:
                raise CrawlError("棋譜一覧が JSON ではありません") from error
            if (not isinstance(page, dict) or not isinstance(page.get("results"), list)
                    or not all(isinstance(game, dict) for game in page["results"])
                    or (page.get("next") is not None and not isinstance(page["next"], str))):
                raise CrawlError("棋譜一覧の API 形式が不正です")
            report.pages += 1
            for game in page["results"]:
                if report.attempted >= config.max_games:
                    break
                game_id = game.get("id")
                if type(game_id) is not int or game_id < 1:
                    raise CrawlError("棋譜一覧に不正な対局 ID があります")
                if game_id in seen_games:
                    continue
                seen_games.add(game_id)
                if not _matches(game, config):
                    report.filtered += 1
                    continue
                previous = manifest["games"].get(str(game_id), {})
                if previous.get("status") == "rejected":
                    report.rejected += 1
                    continue
                digest = previous.get("sha256")
                if (previous.get("status") in ("saved", "duplicate")
                        and isinstance(digest, str) and digest in hashes):
                    report.resumed += 1
                    continue
                report.attempted += 1
                source_url = f"{origin}/api/v1/games/{game_id}/sgf"
                entry = {"url": source_url, "retrieved_at": datetime.now(timezone.utc).isoformat(),
                         "metadata": {key: game.get(key) for key in
                                      ("width", "height", "komi", "rules", "ended", "ranked", "handicap")}}
                # 制限や通信障害ではアクセスを続けず、保存済み分を残して停止する。
                data = client.fetch(source_url)
                digest = hashlib.sha256(data).hexdigest()
                # SGF と誤認して HTML 等を保存しないよう、既存の学習処理で検証する。
                with tempfile.TemporaryDirectory(dir=config.output) as temporary:
                    # 強制終了で一時ファイルが残っても学習対象に混入させない。
                    candidate = Path(temporary) / "candidate.tmp"
                    candidate.write_bytes(data)
                    try:
                        size, samples = samples_from_sgf(candidate)
                        if size != game["width"]:
                            raise SGFError("一覧と SGF の盤面サイズが一致しません")
                    except (SGFError, RecursionError, ValueError) as error:
                        entry.update(status="rejected", reason=str(error), sha256=digest)
                        report.rejected += 1
                    else:
                        entry.update(sha256=digest, board_size=size, samples=len(samples))
                        if digest in hashes:
                            entry.update(status="duplicate", file=hashes[digest])
                            report.duplicates += 1
                        else:
                            filename = f"{digest}.sgf"
                            _atomic_write(config.output / filename, data)
                            hashes = {key: value for key, value in hashes.items() if value != filename}
                            hashes[digest] = filename
                            entry.update(status="saved", file=filename)
                            report.saved += 1
                manifest["games"][str(game_id)] = entry
                _atomic_write(manifest_path, (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
            url = urljoin(url, page["next"]) if page.get("next") else ""
    return report
