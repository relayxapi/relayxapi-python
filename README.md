# relayx — Python client for the RelayX X (Twitter) API

Read public X (Twitter) data — profiles, tweets, search, followers, lists, communities, Spaces and
trends — from Python. No X developer account. Pay per item. [Get a key](https://relayxapi.com/app/).

Standard library only, Python 3.8+.

## Install

```bash
pip install relayxapi
```

## Quickstart

```python
from relayxapi import RelayX

x = RelayX("YOUR_KEY")

# A profile
user = x.user_info("jack")
print(user["data"]["followers"])

# Search (see the operators cheatsheet in the docs)
for tweet in x.paginate(x.search, "from:nasa min_faves:1000", max_pages=3):
    print(tweet["createdAt"], tweet["text"][:80])

# What the last call cost
print(x.last_cost, "credits ·", x.credits_remaining, "left")
```

## Pagination

List methods return one page (items plus `has_next_page` / `next_cursor`). `paginate` follows the
cursor for you and caps the number of billed requests:

```python
followers = list(x.paginate(x.followers, "nasa", max_pages=5))
```

## What you can call

`user_info`, `user_about`, `batch_user_info`, `followers`, `followings`, `verified_followers`,
`follower_ids`, `mentions`, `search_users`, `check_follow`, `last_tweets`, `tweet_timeline`,
`tweets`, `replies`, `quotes`, `retweeters`, `thread_context`, `search`, `list_tweets`,
`list_members`, `list_followers`, `community_info`, `community_tweets`, `space`, `trends`, `credits`.

Full parameters and response shapes: <https://relayxapi.com/docs/>.

## Errors

Failed calls raise `RelayXError` with a `.status` (HTTP status; `0` for transport errors) and
`.message`. HTTP 429 is retried automatically, honouring `Retry-After`. Failed calls are not charged.

```python
from relayxapi import RelayX, RelayXError
try:
    x.user_info("jack")
except RelayXError as e:
    print(e.status, e.message)
```

## Links

- Docs: <https://relayxapi.com/docs/>
- Pricing: <https://relayxapi.com/twitter-api-pricing/>
- Get a key: <https://relayxapi.com/app/>

Not affiliated with X Corp.
