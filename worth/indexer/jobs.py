"""Worth indexer: various utility tasks"""
import logging
from worth.indexer.cached_post import CachedPost
from worth.indexer.posts import Posts

log = logging.getLogger(__name__)

def _last_post_id(db):
    sql = "SELECT id FROM worth_posts ORDER BY id DESC LIMIT 1"
    return db.query_one(sql) or 0

def _last_cached_post_id(db):
    sql = "SELECT post_id FROM worth_posts_cache ORDER BY post_id DESC LIMIT 1"
    return db.query_one(sql) or 0

def audit_cache_missing(db, worth):
    """Scan all posts to check for missing cache entries."""
    last_id = _last_cached_post_id(db)
    step = 1000000
    steps = int(last_id / step) + 1
    log.info("last post id: %d, batches: %d", last_id, steps)

    sql = """
        SELECT hp.id, hp.author, hp.permlink
          FROM worth_posts hp
     LEFT JOIN worth_posts_cache hpc
            ON hp.id = hpc.post_id
         WHERE hp.is_deleted = False
           AND hp.id BETWEEN :lbound AND :ubound
           AND hpc.post_id IS NULL"""

    for idx in range(steps):
        lbound = (idx * step) + 1
        ubound = (idx + 1) * step

        missing = db.query_all(sql, lbound=lbound, ubound=ubound)
        log.info("%d <= id <= %d: %d missing", lbound, ubound, len(missing))
        for row in missing:
            CachedPost.insert(row['author'], row['permlink'], row['id'])

        CachedPost.flush(worth, trx=True)

def audit_cache_deleted(db):
    """Scan all posts to check for extraneous cache entries."""
    last_id = _last_cached_post_id(db)
    step = 1000000
    steps = int(last_id / step) + 1
    log.info("audit_cache_deleted -- last id: %d, batches: %d", last_id, steps)

    sql = """
        SELECT hp.id, hp.author, hp.permlink
          FROM worth_posts hp
          JOIN worth_posts_cache hpc
            ON hp.id = hpc.post_id
         WHERE hp.id BETWEEN :lbound AND :ubound
           AND hp.is_deleted = True"""

    for idx in range(steps):
        lbound = (idx * step) + 1
        ubound = (idx + 1) * step

        extra = db.query_all(sql, lbound=lbound, ubound=ubound)
        log.info("%d <= id <= %d: %d to delete", lbound, ubound, len(extra))
        for row in extra:
            CachedPost.delete(row['id'], row['author'], row['permlink'])

def audit_cache_undelete(db, worth):
    """Scan all posts to check for posts erroneously deleted."""
    last_id = _last_post_id(db)
    step = 1000000
    steps = int(last_id / step) + 1
    log.info("last post id: %d, batches: %d", last_id, steps)

    sql = """
        SELECT id, author, permlink
          FROM worth_posts
         WHERE is_deleted = True
           AND id BETWEEN :lbound AND :ubound
    """

    for idx in range(steps):
        lbound = (idx * step) + 1
        ubound = (idx + 1) * step

        rows = db.query_all(sql, lbound=lbound, ubound=ubound)
        log.info("%d <= id <= %d: %d to check", lbound, ubound, len(rows))

        if not rows:
            continue

        post_args = [(row['author'], row['permlink']) for row in rows]
        posts = worth.get_content_batch(post_args)

        recovered = 0
        for row, post in zip(rows, posts):
            if post['author']:
                recovered += 1
                Posts.undelete(post, post['created'], row['id'])

        log.info("%d <= id <= %d: %d recovered", lbound, ubound, recovered)
        if recovered:
            CachedPost.flush(worth, trx=True)
