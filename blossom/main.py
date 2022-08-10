import os
import pathlib
import sys

import click
import django
import gunicorn.app.wsgiapp as wsgi
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
    "-g",
    "--gunicorn",
    "gunicorn",
    is_flag=True,
    default=False,
    help="Start server with Gunicorn.",
)
@click.version_option(version=__version__, prog_name="blossom")
def main(ctx: Context, command: str, gunicorn: bool) -> None:
    """Run Blossom!"""  # noqa: D400
    if ctx.invoked_subcommand:
        # If we asked for a specific command, don't run the server. Instead, pass control
        # directly to the subcommand.
        return

    # setup django
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "blossom.settings.routing")
    django.setup()

    from django.core.management import call_command

    if command:
        call_command(command)
        return

    if gunicorn:
        import blossom.instrumentation

        # This is just a simple way to supply args to gunicorn
        sys.argv = [
            f"-c {blossom.instrumentation.__file__}.py"
            " --access-logfile -"
            " --workers 3"
            " --bind unix:/run/gunicorn.sock",
            " blossom.wsgi:application",
        ]
        wsgi.run()
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

    # breakpoint()
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
