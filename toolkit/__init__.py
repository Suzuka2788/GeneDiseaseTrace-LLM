"""Shared toolkit for biomed-gene-disease-evidence runs: the model writes judgments, these scripts do the rest."""
import sys

VERSION = "0.1.0"

# Windows consoles default to a legacy code page; the messages contain Chinese enum values.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")
