# Spybar

Spybar is a Linux CLI utility that adds a progress bar to any tool reading a
file. By example, it can create a progress bar for `gzip`, `md5sum` and other
traditional utilities which don't display their progress.

Simply prefix any command with `spybar`.

```
spybar gzip big_dump.sql
```

Or, if the process is already running, attach using its PID. Suppose that you
want to attach to process 42:

```
spybar -a 42
```

## FAQ

### Can you pipe it?

Yes you can, the progress bar happens on `stderr`

```
spybar gzip -c big_dump.sql > big_dump.sql.gz
```

### Can it support Win/OSX?

Unfortunately there is no known way to do so. This utility relies on `psutil`'s
[`Process.open_files()`](https://psutil.readthedocs.io/en/latest/index.html#psutil.Process.open_files)
abstraction so whenever this abstraction gives you the `position` for other
platforms than Linux then Spybar will automatically work on those.

(By automatically I mean there is maybe a few adjustments needed on 
Unix-specific assumptions but it's most likely a just few lines to change).

### How does it work?

If you navigate to the `/proc` file system you will see that for each process
you not only get the list of open files (in `/proc/XX/fd`) but also 
meta-information about those files (in `/proc/XX/fdinfo`).

This way Spybar will look for files open in read mode by your process and then
look at the current position of the file pointer, which once compared to the
file size gives you the relative progress.

### Does it always work?

Of course not, but the use case of binaries reading a file from the beginning
to the end is fairly common. Who never waited in front of a `gzip`, `xz`, `tar`
or `md5sum` wondering if they should go have a coffee or if it's just 2 seconds
more?

In the end this is just guessing but it works in many situations.

## Thanks

I would like to thank:

- Whomever put this feature in the Linux kernel
- The `psutil` maintainers
- The `tqdm` maintainers
- The `poetry` maintainers
- The `pytest` maintainers
- All open-source contributors thanks to whom this software was easy to write

## License

This software is released under the terms of the [WTFPL](./LICENSE).
