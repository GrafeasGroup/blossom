import json
import logging
import os
import signal
from typing import List

logger = logging.getLogger(__name__)


def redis():
    from redis import StrictRedis

    url = os.environ.get("REDIS_CONNECTION_URL", "redis://localhost:6379/0")
    conn = StrictRedis.from_url(url)
    conn.ping()
    return conn


def pull_user_data_from_redis(user_list, rconn):
    user_objs = list()

    for person in user_list:
        user_objs.append(User(username=person, redis_conn=rconn))

    return user_objs


def get_user_list_from_redis(rconn):
    results = list(rconn.smembers("accepted_CoC"))
    # comes in bytes, need unicode
    results = [y.decode() for y in results]
    return results


class User(object):
    """
    Usage:
    from users import User

    pam = User('pam', redis_conn=config.redis)
    pam.update('age', 39)
    pam.update('position', 'Office Administrator')
    pam.save()
    """

    def __init__(self, username=None, redis_conn=None, create_if_not_found=True):
        """
        Create our own Redis connection if one is not passed in.
        We also assume that there is already a logging object created.

        :param username: String; the username we're looking for. No fuzzing
            here; this must be exact.
        :param redis: Object; a `redis` instance.
        """

        self.r = redis_conn

        self.username = username

        self.create_if_not_found = create_if_not_found
        self.redis_key = "::user::{}"
        self.user_data = self._load()

    def __repr__(self):
        return repr(self.user_data)

    def get(self, key, default_return=None):
        return self.user_data.get(key, default_return)

    def _load(self):
        """
        :return: Dict or None; the loaded information from Redis.
        """
        result = self.r.get(self.redis_key.format(self.username))
        if not result:
            if self.create_if_not_found:
                logging.debug("Did not find existing user, loaded blank slate.")
                return self._create_default_user_data()
            else:
                logging.debug("User not found, returning None.")
                return None

        return json.loads(result.decode())

    def save(self):
        self.r.set(self.redis_key.format(self.username), json.dumps(self.user_data))

    def update(self, key, value):
        self.user_data[key] = value

    def list_update(self, key, value):
        if not self.user_data.get(key):
            self.user_data[key] = list()
        self.user_data[key] += [value]

    def _create_default_user_data(self):
        self.user_data = dict()
        self.user_data.update({"username": self.username})
        return self.user_data

    def to_dict(self):
        return self.user_data

    def get_username(self):
        return self.user_data.get("username")


def get_transcribot_text(comments: List, post_id: str):
    # Try to pull the transcribot comment too
    try:
        trancribot_text = [
            i for i in comments if i.parent_id != post_id and i.author == "transcribot"
        ][0].body.split("\n\n---\n\n")[0]
    except Exception:
        trancribot_text = None
    return trancribot_text


def get_transcribot_comment(comments: List, post_id: str):
    # search through for the first comment that contains a transcription
    try:
        top_level_comment = [
            i for i in comments if i.parent_id == post_id and i.author == "transcribot"
        ][0]
        transcribot_c = [
            i
            for i in comments
            if i.parent_id == top_level_comment.id and i.author == "transcribot"
        ][0]
    except Exception:
        transcribot_c = None

    return transcribot_c


class graceful_interrupt_handler(object):
    """
    Usage:
    with graceful_interrupt_handler as handler:
        do_stuff()
        if handler.interrupted:
            do_more_stuff()

    handler.interrupted is called immediately upon receiving the termination
    signal, so do_more_stuff() in the above example should be something that
    allows do_stuff to finish cleanly. The script will exit after
    handler.interrupted finishes unless you wrap calls in itself, at which
    point it will require as many consecutive calls to kill as you wrap.

    A fully tested suite based off http://stackoverflow.com/a/10972804/2638784
    """

    def __init__(self, signals=(signal.SIGINT, signal.SIGTERM)):
        self.signals = signals
        self.original_handlers = {}

    def __enter__(self):
        self.interrupted = False
        self.released = False

        for sig in self.signals:
            self.original_handlers[sig] = signal.getsignal(sig)
            signal.signal(sig, self.handler)

        return self

    def handler(self, signum, frame):
        self.release()
        self.interrupted = True

    def __exit__(self, type, value, tb):
        self.release()

    def release(self):
        if self.released:
            return False

        for sig in self.signals:
            signal.signal(sig, self.original_handlers[sig])

        self.released = True
        return True
