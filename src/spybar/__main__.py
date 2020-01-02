import signal
from argparse import ArgumentParser, Namespace

from .utils import Argv, SpyProcess, run_main


def parse_args(argv: Argv = None) -> Namespace:
    parser = ArgumentParser(
        description="Adds a progress bar to any file-reading command"
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
    parser.add_argument("command_arg", nargs="+")

    return parser.parse_args(argv)


def main(argv: Argv = None):
    args = parse_args(argv)

    sp = SpyProcess(args.command_arg, args.refresh_period)
    sp.start()

    try:
        sp.start_display()
    except KeyboardInterrupt:
        sp.send_signal(signal.SIGINT)
    except SystemExit:
        sp.send_signal(signal.SIGTERM)
    finally:
        ret = sp.return_code()

    exit(ret)


def run():
    run_main(main)


if __name__ == "__main__":
    run()
