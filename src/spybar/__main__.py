import signal
from argparse import REMAINDER, ArgumentParser, Namespace

from .progress import Output
from .utils import Argv, SpyProcess, run_main


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
        type=int,
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
    parser.add_argument("command_arg", nargs=REMAINDER)

    return parser.parse_args(argv)


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
