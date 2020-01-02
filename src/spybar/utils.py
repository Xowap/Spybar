from os import path
from queue import Queue
from threading import Thread
from time import sleep
from typing import Callable, List, NamedTuple, Optional, Sequence, Text

import enlighten
from psutil import AccessDenied, NoSuchProcess, Popen
from psutil._pslinux import popenfile

Argv = Optional[Sequence[Text]]


def run_main(main: Callable):
    return main()


class FileInfo(NamedTuple):
    path: Text
    size: int
    position: int


class SpyProcess:
    def __init__(self, args: Sequence[Text], period: float):
        self.args = args
        self.proc: Optional[Popen] = None
        self.files_cache = {}
        self.display_ticks = Queue()
        self.process_thread = Thread(target=self.watch_process)
        self.ticks_thread = Thread(
            target=self.generate_ticks, args=(period,), daemon=True
        )
        self.manager = enlighten.get_manager()
        self.counters = {}

    def start(self):
        self.proc = Popen(self.args)

    def open_files(self) -> List[popenfile]:
        return self.proc.open_files()

    def list_files(self) -> Sequence[FileInfo]:
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
        stop = False

        try:
            while not stop:
                stop = self.display_ticks.get()
                files = self.list_files()
                paths = set(f.path for f in files)

                for file in files:
                    if file.path not in self.counters:
                        self.counters[file.path] = self.manager.counter(
                            total=file.size, desc=file.path, unit="octet"
                        )

                    self.counters[file.path].count = file.position
                    self.counters[file.path].refresh()

                for to_delete in set(self.counters.keys()) - paths:
                    self.counters[to_delete].close(clear=True)
                    del self.counters[to_delete]
        finally:
            self.manager.stop()

    def generate_ticks(self, period: float):
        while True:
            self.display_ticks.put(False)
            sleep(period)

    def start_display(self):
        self.ticks_thread.start()
        self.process_thread.start()
        self.print_progress()

    def watch_process(self):
        self.return_code()
        self.display_ticks.put(True)

    def return_code(self):
        return self.proc.wait()

    def send_signal(self, sig):
        try:
            self.proc.send_signal(sig)
        except NoSuchProcess:
            pass
