#!/usr/local/bin/python3

"""CLI service router"""

import logging
from worth.conf import Conf
from worth.db.adapter import Db

logging.basicConfig()

def run():
    """Run the service specified in the `--mode` argument."""

    conf = Conf.init_argparse()
    Db.set_shared_instance(conf.db())
    mode = conf.mode()

    if conf.get('test_profile'):
        from worth.utils.profiler import Profiler
        with Profiler():
            launch_mode(mode, conf)
    else:
        launch_mode(mode, conf)


def launch_mode(mode, conf):
    """Launch a routine as indicated by `mode`."""
    if mode == 'server':
        from worth.server.serve import run_server
        run_server(conf=conf)

    elif mode == 'sync':
        from worth.indexer.sync import Sync
        Sync(conf=conf).run()

    elif mode == 'status':
        from worth.db.db_state import DbState
        print(DbState.status())

    else:
        raise Exception("unknown run mode %s" % mode)

if __name__ == '__main__':
    run()
