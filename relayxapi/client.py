"""RelayX API client. Thin, dependency-light wrapper over the REST endpoints at api.relayxapi.com.

Every method returns the parsed JSON envelope. List methods return a page (the items plus
``has_next_page`` / ``next_cursor``); use :meth:`RelayX.paginate` to iterate across pages.
"""
from __future__ import annotations

import time
from typing import Any, Callable, Iterator
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
import json as _json

BASE_URL = "https://api.relayxapi.com"


class RelayXError(Exception):
    """An API or transport error. ``status`` is the HTTP status (0 for transport failures)."""

    def __init__(self, status: int, message: str):
        super().__init__(f"[{status}] {message}")
        self.status = status
        self.message = message


class RelayX:
    """Client for the RelayX X data API.

    Args:
        api_key: your RelayX key (sent as the ``X-API-Key`` header). Create one at
            https://relayxapi.com/app/.
        base_url: override the API base URL (for testing).
        timeout: per-request timeout in seconds.
        max_retries: retries on HTTP 429, honouring ``Retry-After``.
    """

    def __init__(self, api_key: str, *, base_url: str = BASE_URL, timeout: float = 30.0,
                 max_retries: int = 3):
        if not api_key:
            raise ValueError("api_key is required — get one at https://relayxapi.com/app/")
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.max_retries = max_retries
        #: credits remaining after the most recent call, from the ``X-Credits-Remaining`` header.
        self.credits_remaining: int | None = None
        #: credits the most recent call cost, from the ``X-Credits-Cost`` header.
        self.last_cost: int | None = None

    # ---- transport ----
    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        query = {k: v for k, v in (params or {}).items() if v is not None}
        # bools as lowercase strings (FastAPI query parsing), everything else as-is
        query = {k: ("true" if v is True else "false" if v is False else v) for k, v in query.items()}
        url = f"{self.base_url}{path}" + (f"?{urlencode(query)}" if query else "")
        req = Request(url, headers={"X-API-Key": self.api_key, "Accept": "application/json"})
        for attempt in range(self.max_retries + 1):
            try:
                with urlopen(req, timeout=self.timeout) as resp:
                    self._read_headers(resp)
                    return _json.loads(resp.read().decode("utf-8"))
            except HTTPError as e:
                if e.code == 429 and attempt < self.max_retries:
                    time.sleep(float(e.headers.get("Retry-After", "1") or 1))
                    continue
                self._read_headers(e)
                body = e.read().decode("utf-8", "replace")
                try:
                    msg = _json.loads(body).get("msg") or _json.loads(body).get("detail") or body
                except Exception:
                    msg = body
                raise RelayXError(e.code, str(msg)[:300]) from None
            except URLError as e:
                if attempt < self.max_retries:
                    time.sleep(1)
                    continue
                raise RelayXError(0, str(e.reason)) from None
        raise RelayXError(0, "unreachable")

    def _read_headers(self, resp) -> None:
        try:
            c = resp.headers.get("X-Credits-Cost")
            r = resp.headers.get("X-Credits-Remaining")
            self.last_cost = int(c) if c is not None else self.last_cost
            self.credits_remaining = int(r) if r is not None else self.credits_remaining
        except (TypeError, ValueError):
            pass

    # ---- pagination ----
    _ITEM_KEYS = ("tweets", "users", "followers", "followings", "replies", "members", "ids")

    def paginate(self, method: Callable[..., dict], *args, max_pages: int = 10,
                 item_key: str | None = None, **kwargs) -> Iterator[dict]:
        """Yield items across pages by following ``next_cursor``.

            for tweet in x.paginate(x.search, "from:nasa", max_pages=3):
                ...

        ``method`` is any list-returning method on this client. ``max_pages`` caps requests (each page
        is billed). ``item_key`` is auto-detected when omitted.
        """
        cursor = None
        for _ in range(max_pages):
            page = method(*args, cursor=cursor, **kwargs)
            key = item_key or next((k for k in self._ITEM_KEYS if isinstance(page.get(k), list)), None)
            if key:
                yield from page[key]
            if not page.get("has_next_page") or not page.get("next_cursor"):
                break
            cursor = page["next_cursor"]

    # ---- users ----
    def user_info(self, user_name: str) -> dict:
        return self._get("/twitter/user/info", {"userName": user_name})

    def user_about(self, user_name: str) -> dict:
        return self._get("/twitter/user_about", {"userName": user_name})

    def batch_user_info(self, user_ids: list[str] | str) -> dict:
        ids = user_ids if isinstance(user_ids, str) else ",".join(map(str, user_ids))
        return self._get("/twitter/user/batch_info_by_ids", {"userIds": ids})

    def followers(self, user_name: str, *, cursor: str | None = None, page_size: int | None = None) -> dict:
        return self._get("/twitter/user/followers",
                         {"userName": user_name, "cursor": cursor, "pageSize": page_size})

    def followings(self, user_name: str, *, cursor: str | None = None, page_size: int | None = None) -> dict:
        return self._get("/twitter/user/followings",
                         {"userName": user_name, "cursor": cursor, "pageSize": page_size})

    def verified_followers(self, user_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/user/verifiedFollowers", {"user_id": user_id, "cursor": cursor})

    def follower_ids(self, user_name: str | None = None, *, user_id: str | None = None,
                     count: int | None = None, cursor: int | None = None) -> dict:
        return self._get("/twitter/user/followers_ids",
                         {"userName": user_name, "userId": user_id, "count": count, "cursor": cursor})

    def mentions(self, user_name: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/user/mentions", {"userName": user_name, "cursor": cursor})

    def search_users(self, query: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/user/search", {"query": query, "cursor": cursor})

    def check_follow(self, source_user_name: str, target_user_name: str) -> dict:
        return self._get("/twitter/user/check_follow_relationship",
                         {"source_user_name": source_user_name, "target_user_name": target_user_name})

    def last_tweets(self, user_name: str | None = None, *, user_id: str | None = None,
                    cursor: str | None = None, include_replies: bool | None = None) -> dict:
        return self._get("/twitter/user/last_tweets",
                         {"userName": user_name, "userId": user_id, "cursor": cursor,
                          "includeReplies": include_replies})

    def tweet_timeline(self, user_id: str, *, cursor: str | None = None,
                       include_replies: bool | None = None, include_parent_tweet: bool | None = None) -> dict:
        return self._get("/twitter/user/tweet_timeline",
                         {"userId": user_id, "cursor": cursor, "includeReplies": include_replies,
                          "includeParentTweet": include_parent_tweet})

    # ---- tweets ----
    def tweets(self, tweet_ids: list[str] | str) -> dict:
        ids = tweet_ids if isinstance(tweet_ids, str) else ",".join(map(str, tweet_ids))
        return self._get("/twitter/tweets", {"tweet_ids": ids})

    def replies(self, tweet_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/tweet/replies", {"tweetId": tweet_id, "cursor": cursor})

    def quotes(self, tweet_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/tweet/quotes", {"tweetId": tweet_id, "cursor": cursor})

    def retweeters(self, tweet_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/tweet/retweeters", {"tweetId": tweet_id, "cursor": cursor})

    def thread_context(self, tweet_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/tweet/thread_context", {"tweetId": tweet_id, "cursor": cursor})

    def search(self, query: str, *, query_type: str = "Latest", cursor: str | None = None) -> dict:
        """Advanced tweet search. ``query_type`` is ``"Latest"`` or ``"Top"``. See
        https://relayxapi.com/docs/guides/search-syntax/ for operators."""
        return self._get("/twitter/tweet/advanced_search",
                         {"query": query, "queryType": query_type, "cursor": cursor})

    # ---- lists ----
    def list_tweets(self, list_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/list/tweets_timeline", {"listId": list_id, "cursor": cursor})

    def list_members(self, list_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/list/members", {"list_id": list_id, "cursor": cursor})

    def list_followers(self, list_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/list/followers", {"list_id": list_id, "cursor": cursor})

    # ---- communities / spaces / trends ----
    def community_info(self, community_id: str) -> dict:
        return self._get("/twitter/community/info", {"community_id": community_id})

    def community_tweets(self, community_id: str, *, cursor: str | None = None) -> dict:
        return self._get("/twitter/community/tweets", {"community_id": community_id, "cursor": cursor})

    def space(self, space_id: str) -> dict:
        return self._get("/twitter/spaces/detail", {"space_id": space_id})

    def trends(self, woeid: int = 1, *, count: int | None = None) -> dict:
        return self._get("/twitter/trends", {"woeid": woeid, "count": count})

    # ---- account ----
    def credits(self) -> int:
        """Remaining credits on the key. Free — never charged."""
        return self._get("/account/credits")["credits"]
