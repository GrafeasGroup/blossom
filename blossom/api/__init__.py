# from typing import Dict
#
# import requests
#
# __all__ = ['API']
#
#
# class Tools(object):
#     def __init__(self, api_key: str, url: str=None):
#         self.api_key = api_key
#         self.url = url if url else 'http://localhost:8080'
#
#     def _call(self, path: str, json_data=None) -> Dict:
#         if 'api_key' not in json_data:
#             raise Exception('You need an API key in json_data!')
#
#         return requests.post(
#             self.url + path, json=json_data
#         ).json()
#
#
# class API(Tools):
#     """
#     How to use:
#
#     from api import API
#     x = API(api_key='asdf')
#
#     ...
#     """
#     def __init__(self, api_key):
#         super().__init__(api_key)
#         self.item = _Item(api_key)
#         self.keys = _Keys(api_key)
#         self.stats = _Stats(api_key).index
#         self.user = _User(api_key)
#
#
# class _Item(Tools):
#     def claim(self, post_id: str, debug: int=None) -> Dict:
#         return self._call(
#             '/claim',
#             json_data={
#                 'api_key': self.api_key,
#                 'post_id': post_id,
#                 'debug': debug
#             })
#
#     def done(self, post_id: str, debug: int=None) -> Dict:
#         return self._call(
#             '/done',
#             json_data={
#                 'api_key': self.api_key,
#                 'post_id': post_id,
#                 'debug': debug
#             })
#
#     def unclaim(self, post_id: str, debug: int=None) -> Dict:
#         return self._call(
#             '/unclaim',
#             json_data={
#                 'api_key': self.api_key,
#                 'post_id': post_id,
#                 'debug': debug
#             })
#
#
# class _Keys(Tools):
#     def create(self, username: str, is_admin: bool) -> Dict:
#         return self._call(
#             '/keys/create',
#             json_data={
#                 'api_key': self.api_key,
#                 'username': username,
#                 'is_admin': is_admin
#             })
#
#     def revoke(self, revoked_key) -> Dict:
#         return self._call(
#             '/keys/revoke',
#             json_data={
#                 'api_key': self.api_key,
#                 'revoked_key': revoked_key,
#             })
#
#     def me(self) -> Dict:
#         return self._call(
#             '/keys/me',
#             json_data={
#                 'api_key': self.api_key,
#             })
#
#
# class _Stats(Tools):
#     def index(self):
#         return self._call(
#             '/',
#             json_data={
#                 'api_key': self.api_key,
#             })
#
#
# class _User(Tools):
#     def lookup(self, username) -> Dict:
#         return self._call(
#             '/user/lookup',
#             json_data={
#                 'api_key': self.api_key,
#                 'username': username,
#             })
#
#     def create(self, username: str, password: str) -> Dict:
#         return self._call(
#             '/user/create',
#             json_data={
#                 'api_key': self.api_key,
#                 'username': username,
#                 'password': password
#             })
