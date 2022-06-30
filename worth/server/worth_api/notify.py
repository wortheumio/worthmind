"""Worth API: Notifications"""
import logging

from worth.server.common.helpers import return_error_info, json_date
from worth.indexer.notify import NotifyType
from worth.server.worth_api.common import get_account_id, valid_limit, get_post_id

log = logging.getLogger(__name__)

STRINGS = {
    # community
    NotifyType.new_community:  '<dst> was created', # no <src> available
    NotifyType.set_role:       '<src> set <dst> <payload>',
    NotifyType.set_props:      '<src> set properties <payload>',
    NotifyType.set_label:      '<src> label <dst> <payload>',
    NotifyType.mute_post:      '<src> mute <post> - <payload>',
    NotifyType.unmute_post:    '<src> unmute <post> - <payload>',
    NotifyType.pin_post:       '<src> pin <post>',
    NotifyType.unpin_post:     '<src> unpin <post>',
    NotifyType.flag_post:      '<src> flag <post> - <payload>',
    NotifyType.subscribe:      '<src> subscribed to <comm>',

    # personal
    NotifyType.error:          'error: <payload>',
    NotifyType.reblog:         '<src> republished your post',
    NotifyType.follow:         '<src> followed you',
    NotifyType.reply:          '<src> replied to your post',
    NotifyType.reply_comment:  '<src> replied to your comment',
    NotifyType.mention:        '<src> mentioned you',
    NotifyType.vote:           '<src> voted on your post',

    #NotifyType.update_account: '<dst> updated account',
    #NotifyType.receive:        '<src> sent <dst> <payload>',
    #NotifyType.send:           '<dst> sent <src> <payload>',

    #NotifyType.reward:         '<post> rewarded <payload>',
    #NotifyType.power_up:       '<dst> power up <payload>',
    #NotifyType.power_down:     '<dst> power down <payload>',
    #NotifyType.message:        '<src>: <payload>',
}

@return_error_info
async def unread_notifications(context, account, min_score=25):
    """Load notification status for a named account."""
    db = context['db']
    account_id = await get_account_id(db, account)

    sql = """SELECT lastread_at,
                    (SELECT COUNT(*) FROM worth_notifs
                      WHERE dst_id = ha.id
                        AND score >= :min_score
                        AND created_at > lastread_at) unread
               FROM worth_accounts ha
              WHERE id = :account_id"""
    row = await db.query_row(sql, account_id=account_id, min_score=min_score)
    return dict(lastread=str(row['lastread_at']), unread=row['unread'])

@return_error_info
async def account_notifications(context, account, min_score=25, last_id=None, limit=100):
    """Load notifications for named account."""
    db = context['db']
    limit = valid_limit(limit, 100)
    account_id = await get_account_id(db, account)

    if account[:5] == 'worth-': min_score = 0

    seek = ' AND hn.id < :last_id' if last_id else ''
    col = 'hn.community_id' if account[:5] == 'worth-' else 'dst_id'
    sql = _notifs_sql(col + " = :dst_id" + seek)

    rows = await db.query_all(sql, min_score=min_score, dst_id=account_id,
                              last_id=last_id, limit=limit)
    return [_render(row) for row in rows]

@return_error_info
async def post_notifications(context, author, permlink, min_score=25, last_id=None, limit=100):
    """Load notifications for a specific post."""
    # pylint: disable=too-many-arguments
    db = context['db']
    limit = valid_limit(limit, 100)
    post_id = await get_post_id(db, author, permlink)

    seek = ' AND hn.id < :last_id' if last_id else ''
    sql = _notifs_sql("post_id = :post_id" + seek)

    rows = await db.query_all(sql, min_score=min_score, post_id=post_id,
                              last_id=last_id, limit=limit)
    return [_render(row) for row in rows]

def _notifs_sql(where):
    sql = """SELECT hn.id, hn.type_id, hn.score, hn.created_at,
                    src.name src, dst.name dst,
                    hp.author, hp.permlink, hc.name community,
                    hc.title community_title, payload
               FROM worth_notifs hn
          LEFT JOIN worth_accounts src ON hn.src_id = src.id
          LEFT JOIN worth_accounts dst ON hn.dst_id = dst.id
          LEFT JOIN worth_posts hp ON hn.post_id = hp.id
          LEFT JOIN worth_communities hc ON hn.community_id = hc.id
          WHERE %s
            AND score >= :min_score
            AND COALESCE(hp.is_deleted, False) = False
       ORDER BY hn.id DESC
          LIMIT :limit"""
    return sql % where

def _render(row):
    """Convert object to string rep."""
    # src dst payload community post
    out = {'id': row['id'],
           'type': NotifyType(row['type_id']).name,
           'score': row['score'],
           'date': json_date(row['created_at']),
           'msg': _render_msg(row),
           'url': _render_url(row),
          }

    #if row['community']:
    #    out['community'] = (row['community'], row['community_title'])

    return out

def _render_msg(row):
    msg = STRINGS[row['type_id']]
    payload = row['payload']
    if row['type_id'] == NotifyType.vote and payload:
        amt = float(payload[1:])
        if amt >= 0.01:
            msg += ' (<payload>)'
            payload = "$%.2f" % amt

    if '<dst>' in msg: msg = msg.replace('<dst>', '@' + row['dst'])
    if '<src>' in msg: msg = msg.replace('<src>', '@' + row['src'])
    if '<post>' in msg: msg = msg.replace('<post>', _post_url(row))
    if '<payload>' in msg: msg = msg.replace('<payload>', payload or 'null')
    if '<comm>' in msg: msg = msg.replace('<comm>', row['community_title'])
    return msg

def _post_url(row):
    return '@' + row['author'] + '/' + row['permlink']

def _render_url(row):
    if row['permlink']: return '@' + row['author'] + '/' + row['permlink']
    if row['community']: return 'trending/' + row['community']
    if row['src']: return '@' + row['src']
    if row['dst']: return '@' + row['dst']
    assert False, 'no url for %s' % row
    return None
