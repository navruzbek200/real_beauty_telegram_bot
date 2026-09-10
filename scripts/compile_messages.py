#!/usr/bin/env python
"""
Compile locale/**/*.po into the .mo files gettext reads at runtime.

Normally `manage.py compilemessages` does this, but it shells out to msgfmt
from the GNU gettext package, which is not installed here (and is an awkward
thing to require of everyone who checks the project out). The MO container is
a documented, simple binary format, so we write it directly.

    python scripts/compile_messages.py
"""

from __future__ import annotations

import array
import re
import struct
import sys
from pathlib import Path

LOCALE_DIR = Path(__file__).resolve().parent.parent / "locale"
MAGIC = 0x950412DE

# Only the escapes a .po actually uses. Going through `unicode_escape` instead
# would decode the text as latin-1 and turn every Uzbek «…» and ’ into mojibake
# — including inside msgids, which then silently fail to match at runtime.
_ESCAPES = {
    "\\n": "\n",
    "\\t": "\t",
    "\\r": "\r",
    '\\"': '"',
    "\\\\": "\\",
}


def unescape(value: str) -> str:
    out: list[str] = []
    index = 0
    while index < len(value):
        pair = value[index : index + 2]
        if pair in _ESCAPES:
            out.append(_ESCAPES[pair])
            index += 2
        else:
            out.append(value[index])
            index += 1
    return "".join(out)


def parse_po(text: str) -> dict[str, str]:
    """Read the msgid/msgstr pairs we use — no plurals, no contexts."""
    entries: dict[str, str] = {}
    msgid: list[str] = []
    msgstr: list[str] = []
    target: list[str] | None = None

    def flush() -> None:
        if target is None:
            return
        key, value = "".join(msgid), "".join(msgstr)
        # An empty msgstr means "not translated" — leave it to fall back.
        if value:
            entries[key] = value

    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("msgid "):
            flush()
            msgid, msgstr = [], []
            target = msgid
            line = line[len("msgid "):]
        elif line.startswith("msgstr "):
            target = msgstr
            line = line[len("msgstr "):]
        if target is None:
            continue
        found = re.match(r'^"(.*)"$', line)
        if found:
            target.append(unescape(found.group(1)))
    flush()
    return entries


def write_mo(entries: dict[str, str], path: Path) -> None:
    # The header entry (empty msgid) carries the charset; keep it present.
    entries.setdefault("", "Content-Type: text/plain; charset=UTF-8\n")
    keys = sorted(entries)

    ids = b""
    strs = b""
    offsets: list[tuple[int, int, int, int]] = []
    for key in keys:
        encoded_id = key.encode("utf-8")
        encoded_str = entries[key].encode("utf-8")
        offsets.append((len(ids), len(encoded_id), len(strs), len(encoded_str)))
        ids += encoded_id + b"\x00"
        strs += encoded_str + b"\x00"

    keystart = 7 * 4 + 16 * len(keys)
    valuestart = keystart + len(ids)
    koffsets: list[int] = []
    voffsets: list[int] = []
    for o1, l1, o2, l2 in offsets:
        koffsets += [l1, o1 + keystart]
        voffsets += [l2, o2 + valuestart]

    output = struct.pack(
        "Iiiiiii",
        MAGIC,
        0,
        len(keys),
        7 * 4,
        7 * 4 + len(keys) * 8,
        0,
        0,
    )
    output += array.array("i", koffsets + voffsets).tobytes()
    output += ids + strs
    path.write_bytes(output)


def main() -> int:
    po_files = sorted(LOCALE_DIR.rglob("*.po"))
    if not po_files:
        print(f"No .po files under {LOCALE_DIR}", file=sys.stderr)
        return 1
    for po in po_files:
        entries = parse_po(po.read_text(encoding="utf-8"))
        mo = po.with_suffix(".mo")
        write_mo(entries, mo)
        print(f"{po.relative_to(LOCALE_DIR.parent)} -> {mo.name} ({len(entries)} ta)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
