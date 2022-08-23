import os
import pathlib
import sys

import click
import django
import pyuwsgi
from click.core import Context

from blossom import __version__


@click.group(
    context_settings=dict(help_option_names=["-h", "--help", "--halp"]),
    invoke_without_command=True,
)
@click.pass_context
@click.option(
    "-c",
    "--command",
    "command",
    help="Pass a command back to Django.",
)
@click.option(
    "-p",
    "--pyuwsgi",
    "use_pyuwsgi",
    is_flag=True,
    default=False,
    help="Start server with Pyuwsgi.",
)
@click.version_option(version=__version__, prog_name="blossom")
def main(ctx: Context, command: str, use_pyuwsgi: bool) -> None:
    """Run Blossom!"""  # noqa: D400
    if ctx.invoked_subcommand:
        # If we asked for a specific command, don't run the server. Instead, pass control
        # directly to the subcommand.
        return

    # setup django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blossom.settings.routing")
    django.setup()

    from django.conf import settings
    from django.core.management import call_command

    if command:
        call_command(command)
        return

    if use_pyuwsgi:
        call_command("migrate")
        call_command("bootstrap_site")
        pyuwsgi.run(settings.PYUWSGI_ARGS)
    else:
        call_command("runserver")


@main.command()
@click.option(
    "-v",
    "--verbose",
    is_flag=True,
    default=False,
    help="Show Pytest output instead of running quietly.",
)
def selfcheck(verbose: bool) -> None:
    """
    Verify the binary passes all tests internally.

    Add any other self-check related code here.
    """
    import pytest

    import blossom

    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blossom.settings.testing")
    django.setup()
    # -x is 'exit immediately if a test fails'
    # We need to get the path because the file is actually inside the extracted
    # environment maintained by shiv, not physically inside the archive at the
    # time of running.
    args = ["-x", str(pathlib.Path(blossom.__file__).parent)]
    if not verbose:
        args.append("-qq")
    # pytest will return an exit code that we can check on the command line
    sys.exit(pytest.main(args))


BANNER = r"""
__________.__
\______   \  |   ____  ______ __________   _____
 |    |  _/  |  /  _ \/  ___//  ___/  _ \ /     \
 |    |   \  |_(  <_> )___ \ \___ (  <_> )  Y Y  \
 |______  /____/\____/____  >____  >____/|__|_|  /
        \/                \/     \/            \/
"""


@main.command()
def shell() -> None:
    """Create a Python REPL inside the environment."""
    import code

    code.interact(local=globals(), banner=BANNER)


if __name__ == "__main__":
    main()
