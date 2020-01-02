# Spybar

Spybar is a Linux CLI utility that adds a progress bar to any tool reading a
file. By example, it can create a progress bar for `gzip`, `md5sum` and other
traditional utilities which don't display their progress.

Simply prefix any command with `spybar`.

```
spybar gzip this_big_file.dat
```
