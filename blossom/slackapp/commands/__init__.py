import logging
import glob
import importlib
from os.path import basename, join, isfile

from django.conf import settings


log = logging.getLogger(__name__)


def find_plugins() -> list[str]:
    modules = glob.glob(join(settings.BASE_DIR, "blossom", "slackapp", "commands", "*.py"))
    return [f for f in modules if isfile(f) and not f.endswith("__init__.py")]


def load_plugin_file(name: str) -> None:
    """
    Attempt to import the requested file and load the plugin definition.

    The plugin will come in the format of "python/path/to/file.py", which
    we can pass directly to importlib and let it figure it out.
    """
    spec = importlib.util.spec_from_file_location(basename(name)[:-3], name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)


def load_all_plugins():
    plugins = find_plugins()
    for plugin in plugins:
        try:
            load_plugin_file(plugin)
        except Exception as e:
            log.warning(f"Cannot load {plugin}: {e}")


load_all_plugins()
