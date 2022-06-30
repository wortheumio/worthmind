"""Worth API: Internal supporting methods"""
import logging

from worth.server.common.helpers import (
    valid_account,
    valid_permlink,
    valid_limit)

log = logging.getLogger(__name__)

def __used_refs():
    # pylint
    valid_limit('')

async def get_community_id(db, name):
    """Get community id from db."""
    return await db.query_one("SELECT id FROM worth_communities WHERE name = :name",
                              name=name)

async def url_to_id(db, url):
    """Get post_id based on post url."""
    return await get_post_id(db, *split_url(url))

async def get_post_id(db, author, permlink):
    """Get post_id based on author/permlink."""
    sql = "SELECT id FROM worth_posts WHERE author = :a AND permlink = :p"
    _id = await db.query_one(sql, a=author, p=permlink)
    assert _id, 'post id not found'
    return _id

async def get_account_id(db, name):
    """Get account id from account name."""
    assert name, 'no account name specified'
    _id = await db.query_one("SELECT id FROM worth_accounts WHERE name = :n", n=name)
    assert _id, "account not found: `%s`" % name
    return _id

def estimated_wp(vests):
    """Convert VESTS to WP units for display."""
    return vests * 0.0005034

VALID_COMMENT_SORTS = [
    'hot'  # hot algo
    'top', # payout
    'new', # newest
    #'votes', # highest number of votes (excludes comm. muted?)
]
def valid_comment_sort(sort):
    """Validate and return provided `sort`, otherwise throw."""
    assert isinstance(sort, str), 'sort was not a string'
    assert sort in VALID_COMMENT_SORTS, 'invalid sort `%s`' % sort
    return sort

def split_url(url, allow_empty=False):
    """Validate and split a post url into author/permlink."""
    if not url:
        assert allow_empty, 'url must be specified'
        return None
    assert isinstance(url, str), 'url must be a string'

    parts = url.split('/')
    assert len(parts) == 2, 'invalid url parts'

    author = valid_account(parts[0])
    permlink = valid_permlink(parts[1])
    return (author, permlink)
