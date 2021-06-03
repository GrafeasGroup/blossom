import logging
from collections import defaultdict
from datetime import datetime, timedelta

import dpath.util

logger = logging.getLogger(__name__)


class RedditCommentTree(object):
    def __init__(self, allcomments, post_id):
        self.raw_comments = allcomments
        self.post_id = post_id
        tree = lambda: defaultdict(tree)
        self.tree = tree()
        try:
            self.comments = self.create_tree()
        except (StopIteration, RuntimeError):
            self.comments = None

    def find_all_items(self, obj, key, keys=None):
        """
        Example of use:
        d = {'a': 1, 'b': 2, 'c': {'a': 3, 'd': 4, 'e': {'a': 9, 'b': 3}, 'j': {'c': 4}}}
        for k, v in find_all_items(d, 'a'):
            print "* {} = {} *".format('->'.join(k), v)
        """
        ret = []
        if not keys:
            keys = []
        if key in obj:
            out_keys = keys + [key]
            ret.append((out_keys, obj[key]))
        for k, v in obj.items():
            if isinstance(v, dict):
                found_items = self.find_all_items(v, key, keys=(keys + [k]))
                ret += found_items
        return ret

    def search(self, d, k, path=None):
        if path is None:
            path = []

        if k in d.keys():
            path.append(k)
            return path

        for nk in d.keys():
            nd = d[nk]
            path.append(nk)
            if isinstance(nd, dict):
                if self.search(nd, k, path) is not None:
                    return path
            path.pop(-1)

    def _find_parent(self, item):
        parent_id = item.parent_id[3:]
        return self.search(self.tree, parent_id)

    def _add_item(self, path, item):
        container = {"object": None, "children": {}}
        path = "/" + "/".join(path)
        dpath.util.new(self.tree, path + f"/children/{item.id}", container)
        dpath.util.set(self.tree, path + f"/children/{item.id}/object", item)

    def create_tree(self):
        top_level_comments = [
            i for i in self.raw_comments if i.parent_id.startswith("t3_")
        ]
        child_comments = [
            i for i in self.raw_comments if not i.parent_id.startswith("t3_")
        ]
        logger.debug(
            f"Found {len(top_level_comments)} top level comments and {len(child_comments)} "
            f"child comments."
        )

        added_ids = list()

        tree_create_start = datetime.now()
        kill_time = tree_create_start + timedelta(seconds=20)

        for item in top_level_comments:
            self.tree[item.id] = {"object": item, "children": {}}
        for _ in range(99999):
            checkpoint = datetime.now()
            if checkpoint > kill_time:
                raise StopIteration
            if len(added_ids) == len(child_comments):
                break
            for item in child_comments:
                if item.id in added_ids:
                    continue
                parent_path = self._find_parent(item)
                if not parent_path:
                    continue
                self._add_item(parent_path, item)
                added_ids.append(item.id)

    def dicts(self, t):
        return {k: self.dicts(t[k]) for k in t}

    def find_transcription(self):
        tree_create_start = datetime.now()
        kill_time = tree_create_start + timedelta(seconds=20)
        for item in self.tree.keys():
            checkpoint = datetime.now()
            if checkpoint > kill_time:
                raise StopIteration
            if "/r/TranscribersOfReddit/wiki/" in self.tree[item]["object"].body:
                t_body = self.tree[item]["object"].body
                t_author = self.tree[item]["object"].author
                t_id = self.tree[item]["object"].id
                current_item = self.tree[item]

                while True:
                    checkpoint = datetime.now()
                    if checkpoint > kill_time:
                        raise StopIteration
                    found_something = False

                    children = current_item["children"]

                    for blorp in children.keys():
                        try:
                            if (
                                children[blorp]["object"].author == t_author
                                and children[blorp]["object"].id != t_id
                            ):
                                found_something = True
                                t_body += "\n\n"
                                t_body += children[blorp]["object"].body
                                logger.info(
                                    f"Found piece of extended transcript! ID {children[blorp]['object'].id}"
                                )

                                children = children[blorp]["children"]
                        except KeyError:
                            continue

                    if not found_something:
                        logger.info(f"returning {len(t_body)} characters")
                        return t_body
