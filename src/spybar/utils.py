from os import path
from queue import Queue
from threading import Thread
from time import sleep
from typing import Callable, List, NamedTuple, Optional, Sequence, Text

from psutil import AccessDenied, NoSuchProcess, Popen
from psutil._pslinux import popenfile

from .progress import Output, Progress

Argv = Optional[Sequence[Text]]


def run_main(main: Callable[[], None]):
    """
    Runs the main function. Add try/catch wrappers or whatever you need here.
    That's useful in case you want to have several points to call main().

    Parameters
    ----------
    main
        Main function
    """
    return main()


class FileInfo(NamedTuple):
    """
    Current information about the file
    """

    path: Text
    size: int
    position: int


class SpyProcess:
    """
    Spying process to detect the currently open files and their current reading
    advancement.

    Notes
    -----
    There is three threads at play here:

    - The main thread, which handles the display
    - The ticking thread which drives refreshing
    - The process watching thread, which waits for the process to be done

    Both the ticking and the process threads communicate their ticks to the
    main thread through a queue. This way the main thread can easily display
    an update every second and close instantly when the process is done.
    """

    def __init__(self, args: Sequence[Text], period: float, output: Output):
        self.args = args
        self.proc: Optional[Popen] = None
        self.files_cache = {}
        self.display_ticks = Queue()
        self.process_thread = Thread(target=self.watch_process)
        self.ticks_thread = Thread(
            target=self.generate_ticks, args=(period,), daemon=True
        )
        self.progress = Progress(output)
        self.counters = {}

    def start(self):
        """
        Starts the child process
        """

        self.proc = Popen(self.args)

    def open_files(self) -> List[popenfile]:
        """
        Returns the list of open files
        """

        return self.proc.open_files()

    def list_files(self) -> Sequence[FileInfo]:
        """
        Generates the FileInfo object of all interesting files.
        """

        files_in_use = set()
        out = []

        try:
            for f in self.open_files():
                if f.mode != "r":
                    continue

                files_in_use.add(f.path)

                if f.path not in self.files_cache:
                    self.files_cache[f.path] = path.getsize(f.path)

                out.append(
                    FileInfo(
                        path=f.path, size=self.files_cache[f.path], position=f.position
                    )
                )
        except (AccessDenied, NoSuchProcess):
            pass

        for k in set(self.files_cache.keys()) - files_in_use:
            del self.files_cache[k]

        return out

    def print_progress(self):
        """
        UI display thread, looping around until the thing is done
        """

        stop = False

        try:
            while not stop:
                files = self.list_files()
                self.progress.update(files)
                stop = self.display_ticks.get()
        finally:
            self.progress.close()

    def generate_ticks(self, period: float):
        """
        Ticks into the queue every "period" second

        Parameters
        ----------
        period
            Number of seconds between two ticks
        """

        while True:
            self.display_ticks.put(False)
            sleep(period)

    def start_display(self):
        """
        Starts the threads that will tick the display
        """

        self.ticks_thread.start()
        self.process_thread.start()
        self.print_progress()

    def watch_process(self):
        """
        Waits until the process finishes and raises the tick
        """

        self.return_code()
        self.display_ticks.put(True)

    def return_code(self) -> int:
        """
        Waits for the process to finish and returns its return code
        """

        return self.proc.wait()

    def send_signal(self, sig):
        """
        Sends a signal to the child process

        Parameters
        ----------
        sig
            Unix signal
        """

        try:
            self.proc.send_signal(sig)
        except NoSuchProcess:
            pass
