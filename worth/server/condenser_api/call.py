"""Handles legacy `call` method."""

from worth.server.common.helpers import (
    ApiError,
    return_error_info,
)
from worth.server.condenser_api.get_state import get_state
from worth.server.condenser_api.tags import get_trending_tags
from worth.server.condenser_api.methods import (
    get_followers,
    get_following,
    get_followers_by_page,
    get_following_by_page,
    get_follow_count,
    get_content,
    get_content_replies,
    get_discussions_by_trending,
    get_discussions_by_hot,
    get_discussions_by_promoted,
    get_discussions_by_created,
    get_discussions_by_blog,
    get_discussions_by_feed,
    get_discussions_by_comments,
    get_replies_by_last_update,

    get_post_discussions_by_payout,
    get_comment_discussions_by_payout,

    get_discussions_by_author_before_date,
    get_blog,
    get_blog_entries,
    get_account_votes,
)

def _strict_list(params, expected_len, min_len=None):
    assert isinstance(params, list), "params not a list"
    if min_len is None:
        assert len(params) == expected_len, "expected %d params" % expected_len
    else:
        assert (len(params) <= expected_len and
                len(params) >= min_len), "expected %d params" % expected_len
    return params

def _strict_query(params):
    query = _strict_list(params, 1)[0]
    assert isinstance(query, dict), "query must be dict"

    # remove optional-yet-blank param keys -- some clients include every key
    # possible, and worths seems to ignore them silently. need to strip
    # them here, if blank, to avoid argument mismatch errors.
    all_keys = ['filter_tags', 'select_tags', 'select_authors', 'author',
                'start_author', 'start_permlink', 'start_tag', 'parent_author',
                'parent_permlink', 'start_parent_author', 'before_date', 'tag']
    for key in all_keys:
        if key in query and not query[key]:
            del query[key]

    # unsupported but seen in the wild
    assert not 'filter_tags' in query, 'filter_tags not supported'
    assert not 'select_tags' in query, 'select_tags not supported'

    # unsupported but seen in the wild (blank or matching `tag`; noop)
    if 'select_authors' in query:
        del query['select_authors']

    optional_keys = set(['truncate_body', 'start_author', 'start_permlink', 'tag'])
    expected_keys = set(['limit'])

    provided_keys = query.keys()
    missing = expected_keys - provided_keys
    unknown = provided_keys - expected_keys - optional_keys
    assert not missing, "missing query key %s" % missing
    assert not unknown, "unknown query key %s" % unknown

    return query

@return_error_info
async def call(context, api, method, params):
    """Routes legacy-style `call` method requests.

    Example:
    ```
    {"id":0,"jsonrpc":"2.0","method":"call",
     "params":["database_api","get_state",["trending"]]}
    ```"""
    # pylint: disable=too-many-return-statements, too-many-branches, no-else-return
    assert api == 'condenser_api', "`call` requires condenser_api"

    # Follows
    if method == 'get_followers':
        return await get_followers(context, *_strict_list(params, 4))
    elif method == 'get_following':
        return await get_following(context, *_strict_list(params, 4))
    elif method == 'get_followers_by_page':
        return await get_followers_by_page(context, *_strict_list(params, 4))
    elif method == 'get_following_by_page':
        return await get_following_by_page(context, *_strict_list(params, 4))
    elif method == 'get_follow_count':
        return await get_follow_count(context, *_strict_list(params, 1))

    # Content primitives
    elif method == 'get_content':
        return await get_content(context, *_strict_list(params, 2))
    elif method == 'get_content_replies':
        return await get_content_replies(context, *_strict_list(params, 2))

    # Trending tags
    elif method == 'get_trending_tags':
        return await get_trending_tags(context, *_strict_list(params, 2))

    # Content monolith
    elif method == 'get_state':
        return await get_state(context, *_strict_list(params, 1))

    # Global discussion queries
    elif method == 'get_discussions_by_trending':
        return await get_discussions_by_trending(context, **_strict_query(params))
    elif method == 'get_discussions_by_hot':
        return await get_discussions_by_hot(context, **_strict_query(params))
    elif method == 'get_discussions_by_promoted':
        return await get_discussions_by_promoted(context, **_strict_query(params))
    elif method == 'get_discussions_by_created':
        return await get_discussions_by_created(context, **_strict_query(params))
    elif method == 'get_post_discussions_by_payout':
        return await get_post_discussions_by_payout(context, **_strict_query(params))
    elif method == 'get_comment_discussions_by_payout':
        return await get_comment_discussions_by_payout(context, **_strict_query(params))

    # Account discussion queries
    elif method == 'get_discussions_by_blog':
        return await get_discussions_by_blog(context, **_strict_query(params))
    elif method == 'get_discussions_by_feed':
        return await get_discussions_by_feed(context, **_strict_query(params))
    elif method == 'get_discussions_by_comments':
        return await get_discussions_by_comments(context, **_strict_query(params))
    elif method == 'get_replies_by_last_update':
        return await get_replies_by_last_update(context, *_strict_list(params, 3))

    # Exotic account discussion queries
    elif method == 'get_discussions_by_author_before_date':
        return await get_discussions_by_author_before_date(context, *_strict_list(params, 4))
    elif method == 'get_blog':
        return await get_blog(context, *_strict_list(params, 3, 2))
    elif method == 'get_blog_entries':
        return await get_blog_entries(context, *_strict_list(params, 3, 2))

    # Misc/dummy
    elif method == 'get_account_votes':
        return await get_account_votes(context, *_strict_list(params, 1))

    raise ApiError("unknown method: %s.%s" % (api, method))
