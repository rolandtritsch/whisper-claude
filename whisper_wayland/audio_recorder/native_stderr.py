"""Native stderr suppression for noisy audio backends."""

import contextlib
import os
import typing


def should_suppress_audio_warnings() -> bool:
    """Return whether native audio backend warnings should be hidden."""
    value = os.getenv("SUPPRESS_AUDIO_WARNINGS", "true").strip().lower()
    return value not in {"0", "false", "no", "off"}


@contextlib.contextmanager
def suppress_native_stderr() -> typing.Iterator[None]:
    """Temporarily redirect process stderr to /dev/null.

    ALSA/JACK messages from PortAudio are emitted by native code directly to
    file descriptor 2, so Python logging configuration cannot filter them.
    """
    if not should_suppress_audio_warnings():
        yield
        return

    stderr_fd = 2
    saved_stderr_fd = os.dup(stderr_fd)
    try:
        with open(os.devnull, "w") as devnull:
            os.dup2(devnull.fileno(), stderr_fd)
            yield
    finally:
        os.dup2(saved_stderr_fd, stderr_fd)
        os.close(saved_stderr_fd)
