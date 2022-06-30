"""Maintains feed cache (blogs + reblogs)"""

import logging
import time
from worth.db.adapter import Db
from worth.db.db_state import DbState

log = logging.getLogger(__name__)

DB = Db.instance()

class FeedCache:
    """Maintains `worth_feed_cache`, which merges posts and reports.

    The feed cache allows for efficient querying of posts + reblogs,
    savings us from expensive queries. Effectively a materialized view.
    """

    @classmethod
    def insert(cls, post_id, account_id, created_at):
        """Inserts a [re-]post by an account into feed."""
        assert not DbState.is_initial_sync(), 'writing to feed cache in sync'
        sql = """INSERT INTO worth_feed_cache (account_id, post_id, created_at)
                      VALUES (:account_id, :id, :created_at)
                 ON CONFLICT (account_id, post_id) DO NOTHING"""
        DB.query(sql, account_id=account_id, id=post_id, created_at=created_at)

    @classmethod
    def delete(cls, post_id, account_id=None):
        """Remove a post from feed cache.

        If `account_id` is specified, we remove a single entry (e.g. a
        singular un-reblog). Otherwise, we remove all instances of the
        post (e.g. a post was deleted; its entry and all reblogs need
        to be removed.
        """
        assert not DbState.is_initial_sync(), 'writing to feed cache in sync'
        sql = "DELETE FROM worth_feed_cache WHERE post_id = :id"
        if account_id:
            sql = sql + " AND account_id = :account_id"
        DB.query(sql, account_id=account_id, id=post_id)

    @classmethod
    def rebuild(cls, truncate=True):
        """Rebuilds the feed cache upon completion of initial sync."""

        log.info("[WORTH] Rebuilding feed cache, this will take a few minutes.")
        DB.query("START TRANSACTION")
        if truncate:
            DB.query("TRUNCATE TABLE worth_feed_cache")

        lap_0 = time.perf_counter()
        DB.query("""
            INSERT INTO worth_feed_cache (account_id, post_id, created_at)
                 SELECT worth_accounts.id, worth_posts.id, worth_posts.created_at
                   FROM worth_posts
                   JOIN worth_accounts ON worth_posts.author = worth_accounts.name
                  WHERE depth = 0 AND is_deleted = '0'
            ON CONFLICT DO NOTHING
        """)
        lap_1 = time.perf_counter()
        DB.query("""
            INSERT INTO worth_feed_cache (account_id, post_id, created_at)
                 SELECT worth_accounts.id, post_id, worth_reblogs.created_at
                   FROM worth_reblogs
                   JOIN worth_accounts ON worth_reblogs.account = worth_accounts.name
            ON CONFLICT DO NOTHING
        """)
        lap_2 = time.perf_counter()
        DB.query("COMMIT")

        log.info("[WORTH] Rebuilt worth feed cache in %ds (%d+%d)",
                 (lap_2 - lap_0), (lap_1 - lap_0), (lap_2 - lap_1))

