import os

# Route us to the correct settings file based on environment variables. Allows
# us to add a stage environment really easily.

env = os.environ.get('ENVIRONMENT', None)

if env == 'local':
    from blossom.settings.local import *
elif env == 'testing':
    from blossom.settings.testing import *
else:
    from blossom.settings.prod import *
