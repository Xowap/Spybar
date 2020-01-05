import sys
from enum import Enum
from fcntl import ioctl
from io import BufferedWriter
from signal import SIGWINCH, signal
from struct import unpack
from termios import TIOCGWINSZ
from typing import TYPE_CHECKING, Callable, Dict, NamedTuple, Sequence, Text, TextIO

from tqdm import tqdm

if TYPE_CHECKING:
    from .utils import FileInfo


SINK = open("/dev/null", "r+")


class Output(Enum):
    """
    Used to restrict potential values of output files from the argument
    parsing.
    """

    stderr = "stderr"
    stdout = "stdout"


class TerminalSize(NamedTuple):
    """
    Contains the output of what ioctl tells us on the terminal's size
    """

    rows: int
    cols: int
    x_pixel: int
    y_pixel: int

    @classmethod
    def from_bytes(cls, b: bytes) -> "TerminalSize":
        """
        Converts the output of ioctl into a workable TerminalSize

        Parameters
        ----------
        b
            Byte values

        Returns
        -------
        Parsed value
        """
        return cls(*unpack("hhhh", b))


class FileProgress(NamedTuple):
    """
    Information about the current progress of file
    """

    info: "FileInfo"
    tqdm: tqdm


class BottomBox:
    """
    Utility class to display something at the bottom of the screen while the
    stdout can still print things.

    Notes
    -----
    This instructs the terminal to create a scroll window above the text in the
    bottom. When an update happens, bottom lines are manually drawn. We also
    manage the cursor so that when stdout prints something it is at the bottom
    of the window it scrolls up and is not drawn downstairs.

    This happens on stderr, this way the output of stdout can be piped.

    The renderer will either get called on updates (aka when you call update())
    either when the terminal is resized.

    Also, there is an inner buffer before writing out things to make sure that
    all characters are written at the same time and avoid messing things up.
    """

    def __init__(self, renderer: Callable[[int], Sequence[Text]], output: Output):
        """
        Constructor.

        Parameters
        ----------
        renderer
            A callable that will be called when a drawing is requested
        """

        self.last_height = 0
        self.stdout: TextIO = getattr(sys, output.value)
        self.renderer = renderer
        # noinspection PyTypeChecker
        self.buffer = BufferedWriter(self.stdout.buffer, buffer_size=1_000_000)

        signal(SIGWINCH, lambda _, __: self.update())

    def _write(self, s: bytes):
        """
        Store bytes into the buffer

        Parameters
        ----------
        s
            Bytes to be flushed later
        """

        self.buffer.write(s)

    def _flush(self):
        """
        Flushes the bytes to the output
        """

        self.buffer.flush()
        self.stdout.buffer.flush()

    def _save_cursor(self) -> None:
        """
        ANSI save of the cursor position
        """

        self._write(b"\0337")

    def _restore_cursor(self) -> None:
        """
        ANSI restore of the cursor position
        """

        self._write(b"\0338")

    def _set_scroll_region(self, rows: int) -> None:
        """
        ANSI definition of the scroll area
        Parameters
        ----------
        rows
            Number of rows in the scroll area
        """

        self._write(f"\033[0;{rows}r".encode())

    def _move_cursor_to_row(self, row: int) -> None:
        """
        Moves the cursor to that row

        Parameters
        ----------
        row
            1-indexed row number
        """

        self._write(f"\033[{row};1f".encode())

    def _move_cursor_up(self) -> None:
        """
        Moves the cursor to the row up
        """

        self._write(b"\033[1A")

    def _clear_row(self) -> None:
        """
        Clears the current row
        """

        self._write(b"\033[K")

    def _get_terminal_size(self) -> TerminalSize:
        """
        Inquires the size of the terminal and returns it
        """

        return TerminalSize.from_bytes(
            ioctl(self.stdout.fileno(), TIOCGWINSZ, "\0" * 8)
        )

    def _adjust_for_height(self, new_height) -> None:
        """
        Makes sure that there is white space enough at the bottom of the output
        in order for the bottom box to be drawn.
        """

        for _ in range(self.last_height + 1, new_height):
            self._write(b"\n")

        for _ in range(self.last_height + 1, new_height):
            self._move_cursor_up()

        self.last_height = new_height

    def update(self) -> None:
        """
        Updates the content of the bottom box
        """

        size = self._get_terminal_size()
        lines = self.renderer(size.cols)

        self._adjust_for_height(len(lines))
        self._save_cursor()
        self._set_scroll_region(size.rows - len(lines))

        start = size.rows - len(lines) + 1

        for i, line in enumerate(lines):
            self._move_cursor_to_row(start + i)
            self._clear_row()
            self._write(line.encode())

        self._restore_cursor()
        self._flush()

    def cleanup(self):
        """
        When done, restores the scrolling idea and the configuration of the
        terminal (as much as possible).
        """

        size = self._get_terminal_size()
        start = size.rows - self.last_height + 1
        self._save_cursor()

        for i in range(0, self.last_height):
            self._move_cursor_to_row(start + i)
            self._clear_row()

        self._set_scroll_region(size.rows)
        self._restore_cursor()
        self._flush()


class Progress:
    """
    Displays the progress of the files, based on tqdm but with custom rendering
    """

    def __init__(self, output: Output):
        self.box = BottomBox(self._render, output)
        self.cnt = 0
        self.files: Dict[Text, FileProgress] = {}

    def _render(self, width: int) -> Sequence[Text]:
        """
        Renders all the the lines to be displayed.

        Parameters
        ----------
        width
            Terminal width

        Returns
        -------
        List of lines to be displayed
        """

        out = []

        for file, progress in self.files.items():
            progress.tqdm.ncols = width
            progress.tqdm.update(progress.info.position - progress.tqdm.n)
            out.append(repr(progress.tqdm))

        return out

    def update(self, files: Sequence["FileInfo"]) -> None:
        """
        Re-generates the progress bars from the files list.

        Notes
        -----
        We use tqdm here, however we don't want it to be handling things on
        itself. For this reason we set it to output its content to /dev/null
        and we just re-render it using the repr() method.

        Parameters
        ----------
        files
            Current status of files being read. The proper diff since last
            update will be made automatically.
        """

        present = set()

        for file in files:
            present.add(file.path)

            if file.path not in self.files:
                self.files[file.path] = FileProgress(
                    file,
                    tqdm(
                        desc=file.path,
                        total=file.size,
                        unit="o",
                        smoothing=0.1,
                        unit_divisor=1024,
                        unit_scale=True,
                        file=SINK,
                    ),
                )
            else:
                self.files[file.path] = self.files[file.path]._replace(info=file)

        for absent in set(self.files.keys()) - present:
            del self.files[absent]

        self.box.update()

    def close(self):
        """
        Triggers screen cleanup
        """

        self.box.cleanup()
