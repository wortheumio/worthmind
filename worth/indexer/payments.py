"""Process payment ops used for promoted posts."""

import logging

from worth.db.adapter import Db
from worth.db.db_state import DbState
from worth.utils.normalize import parse_amount

from worth.indexer.posts import Posts
from worth.indexer.accounts import Accounts
from worth.indexer.cached_post import CachedPost

log = logging.getLogger(__name__)

DB = Db.instance()

class Payments:
    """Handles payments to update post promotion values."""
    #pylint: disable=too-few-public-methods

    @classmethod
    def op_transfer(cls, op, tx_idx, num, date):
        """Process raw transfer op; apply balance if valid post promote."""
        record = cls._validated(op, tx_idx, num, date)
        if not record:
            return

        # add payment record
        sql = DB.build_insert('worth_payments', record, pk='id')
        DB.query(sql)

        # read current amount
        sql = "SELECT promoted FROM worth_posts WHERE id = :id"
        curr_amount = DB.query_one(sql, id=record['post_id'])
        new_amount = curr_amount + record['amount']

        # update post record
        sql = "UPDATE worth_posts SET promoted = :val WHERE id = :id"
        DB.query(sql, val=new_amount, id=record['post_id'])

        # notify cached_post of new promoted balance, and trigger update
        if not DbState.is_initial_sync():
            CachedPost.update_promoted_amount(record['post_id'], new_amount)
            author, permlink = cls._split_url(op['memo'])
            CachedPost.vote(author, permlink, record['post_id'])

    @classmethod
    def _validated(cls, op, tx_idx, num, date):
        """Validate and normalize the transfer op."""
        # pylint: disable=unused-argument
        if op['to'] != 'null':
            return # only care about payments to null

        amount, token = parse_amount(op['amount'])
        if token != 'WBD':
            return # only care about WBD payments

        url = op['memo']
        if not cls._validate_url(url):
            log.debug("invalid url: %s", url)
            return # invalid url

        author, permlink = cls._split_url(url)
        if not Accounts.exists(author):
            return

        post_id = Posts.get_id(author, permlink)
        if not post_id:
            log.debug("post does not exist: %s", url)
            return

        return {'id': None,
                'block_num': num,
                'tx_idx': tx_idx,
                'post_id': post_id,
                'from_account': Accounts.get_id(op['from']),
                'to_account': Accounts.get_id(op['to']),
                'amount': amount,
                'token': token}

    @staticmethod
    def _validate_url(url):
        """Validate if `url` is in proper `@account/permlink` format."""
        if not url or url.count('/') != 1 or url[0] != '@':
            return False
        return True

    @staticmethod
    def _split_url(url):
        """Split a `@account/permlink` string into (account, permlink)."""
        return url[1:].split('/')
