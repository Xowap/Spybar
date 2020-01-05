import signal
from argparse import REMAINDER, ArgumentParser, Namespace

from .progress import Output
from .utils import Argv, SpyProcess, positive_int, run_main


def parse_args(argv: Argv = None) -> Namespace:
    """
    Parses arguments by default from CLI but if argv is specified parses this
    instead of the default arguments.

    Parameters
    ----------
    argv
        Optional list of arguments to parse. The system argv is used by
        default.

    Returns
    -------
    The parsed Namespace
    """

    parser = ArgumentParser(
        description="Adds a progress bar to any file-reading command"
    )

    parser.add_argument(
        "-a",
        "--attach",
        type=positive_int,
        help=(
            "Instead of starting a process, attaches to an already-running "
            "process. Specify the PID here."
        ),
    )
    parser.add_argument(
        "-p",
        "--refresh-period",
        type=float,
        help=(
            "Period in seconds between two refreshes of the progress bars "
            "(default: 1s)"
        ),
        default="1",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Output,
        help='Output the bar to "stderr" or "stdout" (default: "stderr")',
        default=Output.stderr,
    )
    parser.add_argument(
        "command_arg",
        nargs=REMAINDER,
        help=(
            "After the options, just type your regular command, by example "
            '"spybar gzip big_dump.sql"'
        ),
    )

    ns = parser.parse_args(argv)

    if ns.attach is None and not ns.command_arg:
        parser.error(
            "You need to specify at least a PID to attach (-a option) or a "
            'command to run. By example "spybar gzip bigdump.sql"'
        )
    elif ns.attach is not None and ns.command_arg:
        parser.error(
            "You cannot specify a PID to attach and a "
            "command to run at the same time"
        )

    return ns


def main(argv: Argv = None):
    """
    Runs the process spy.

    Notes
    -----
    Most things happens in SpyProcess, however this function shows you the
    regular call order.
    """

    args = parse_args(argv)

    sp = SpyProcess(
        args=args.command_arg,
        period=args.refresh_period,
        output=args.output,
        attach=args.attach,
    )
    sp.start()

    try:
        sp.start_display()
    except KeyboardInterrupt:
        sp.send_signal(signal.SIGINT)
    except SystemExit:
        sp.send_signal(signal.SIGTERM)
    finally:
        ret = sp.return_code()

    if ret is not None:
        exit(ret)


def run():
    """
    Convenient function which can be called from a binary installed by the
    setup script.
    """

    run_main(main)


if __name__ == "__main__":
    run()
