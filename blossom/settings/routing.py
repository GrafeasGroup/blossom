import os

# Route us to the correct settings file based on environment variables. Allows
# us to add a stage environment really easily.

env = os.environ.get('ENVIRONMENT', None)

if env == 'local':
    # noinspection PyUnresolvedReferences
    from blossom.settings.local import *
else:
    # noinspection PyUnresolvedReferences
    from blossom.settings.prod import *
