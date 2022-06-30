"""Worth server and API tests."""
from worth.conf import Conf
from worth.db.adapter import Db

Db.set_shared_instance(Conf.init_test().db())
