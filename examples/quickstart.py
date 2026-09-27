"""Minimal RelayX example. Run: RELAYX_KEY=your_key python examples/quickstart.py"""
import os

from relayxapi import RelayX

x = RelayX(os.environ["RELAYX_KEY"])

# 1. A single profile
jack = x.user_info("jack")["data"]
print(f"@{jack['userName']} — {jack['followers']:,} followers")

# 2. Recent tweets from a search, across a few pages
print("\nRecent NASA posts with 1k+ likes:")
for tweet in x.paginate(x.search, "from:nasa min_faves:1000", max_pages=2):
    print(f"  {tweet['likeCount']:>7,}  {tweet['text'][:70]}")

# 3. Cost of the run
print(f"\nCredits remaining: {x.credits_remaining:,}")
