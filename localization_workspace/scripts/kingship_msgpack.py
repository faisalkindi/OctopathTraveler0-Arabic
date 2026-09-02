"""
Reusable read/write for Octopath Traveler 0's Kingship BinaryAsset GameText tables.

Format (verified end-to-end, incl. live in-game deploy test, 2026-07-06):
  .uexp = [10-byte header][MessagePack payload][8-byte constant trailer]
    header  = 5 zero bytes + 0x03 + 3-byte little-endian payload length + 0x00
    payload = msgpack map {"m_DataList": [ {m_id, [m_voiceId,] m_gametext: [12 lang slots]}, ... ]}
    trailer = constant bytes 00 00 00 00 c1 83 2a 9e

  .uasset export table stores a fixed SerialSize (int64 LE) for the paired .uexp:
    SerialSize = total_uexp_file_size - 4
  Its byte offset inside the .uasset varies per table/NameMap size -- locate it by searching
  for the OLD SerialSize value as an int64 LE, don't hardcode an offset.

Requires: pip install msgpack
"""
import msgpack
import struct
import os

TRAILER = bytes.fromhex("00000000c1832a9e")


def read_uexp(path):
    """Decode a GameText .uexp into its Python object (the {"m_DataList": [...]} dict)."""
    with open(path, "rb") as f:
        data = f.read()
    header = data[:10]
    payload_len = header[6] + header[7] * 256 + header[8] * 65536
    payload = data[10:10 + payload_len]
    trailer = data[10 + payload_len:]
    if trailer != TRAILER:
        raise ValueError(f"{path}: unexpected trailer {trailer.hex()} (expected {TRAILER.hex()})")
    unpacker = msgpack.Unpacker(raw=False, strict_map_key=False)
    unpacker.feed(payload)
    obj = unpacker.unpack()
    if unpacker.tell() != len(payload):
        raise ValueError(f"{path}: msgpack did not consume the full declared payload length")
    return obj


def _pack_signed_int(n):
    """Encode an integer using msgpack's SIGNED family (positive fixint / int8/16/32/64),
    matching the original files' encoding convention for m_id -- confirmed 2026-07-07 that
    msgpack-python's default packb() prefers the UNSIGNED family (uint32=0xce) for positive
    values, while the game's own cooked files use the SIGNED family (int32=0xd2) for the same
    magnitude. Both decode to the same value under any spec-compliant reader, but the custom
    Kingship deserializer appears to care about the exact type tag."""
    if 0 <= n <= 127:
        return bytes([n])  # positive fixint
    if -32 <= n < 0:
        return bytes([n & 0xFF])  # negative fixint
    if -128 <= n <= 127:
        return b"\xd0" + struct.pack(">b", n)
    if -32768 <= n <= 32767:
        return b"\xd1" + struct.pack(">h", n)
    if -2147483648 <= n <= 2147483647:
        return b"\xd2" + struct.pack(">i", n)
    return b"\xd3" + struct.pack(">q", n)


def _pack_str(s):
    """Encode a string matching the game's own cooked-file convention -- confirmed
    2026-07-07 by scanning 20+ known-length strings in an original .uexp: FixStr only for
    length <=15, STR16 (0xda) for EVERYTHING from 16 bytes up (never FixStr 16-31, never
    STR8/0xd9, even though standard msgpack would prefer those for various ranges)."""
    b = s.encode("utf-8")
    n = len(b)
    if n <= 15:
        return bytes([0xA0 | n]) + b
    if n <= 65535:
        return b"\xda" + struct.pack(">H", n) + b
    return b"\xdb" + struct.pack(">I", n) + b


def _pack_value(value):
    if isinstance(value, str):
        return _pack_str(value)
    if isinstance(value, list):
        n = len(value)
        if n <= 15:
            head = bytes([0x90 | n])
        elif n < 65536:
            head = b"\xdc" + struct.pack(">H", n)
        else:
            head = b"\xdd" + struct.pack(">I", n)
        return head + b"".join(_pack_value(v) for v in value)
    return msgpack.packb(value, use_bin_type=False)


def _pack_row(row):
    """Encode one m_DataList entry, forcing ALL integer fields (m_id, m_voiceId, ...) to
    the signed int family and matching the game's own string-encoding convention for
    everything else (see _pack_str). Confirmed 2026-07-07: both m_id and m_voiceId use
    signed int32 (0xd2) in the original cooked files, not msgpack-python's default
    unsigned-preferring choice (0xce) for positive values."""
    parts = [bytes([0x80 | len(row)])]  # fixmap with len(row) entries
    for key, value in row.items():
        parts.append(_pack_str(key))
        if isinstance(value, int) and not isinstance(value, bool):
            parts.append(_pack_signed_int(value))
        else:
            parts.append(_pack_value(value))
    return b"".join(parts)


def _pack_object(obj):
    """Encode the top-level {"m_DataList": [...]} object with the m_id fix applied."""
    rows = obj["m_DataList"]
    header = bytes([0x81]) + _pack_str("m_DataList")
    n = len(rows)
    if n < 65536:
        arr_header = b"\xdc" + struct.pack(">H", n)
    else:
        arr_header = b"\xdd" + struct.pack(">I", n)
    parts = [header, arr_header]
    parts.extend(_pack_row(r) for r in rows)
    return b"".join(parts)


def write_uexp(path, obj):
    """Re-encode a GameText object back to .uexp bytes (header+payload+trailer). Returns new file size."""
    payload = _pack_object(obj)
    new_len = len(payload)
    if new_len >= (1 << 24):
        raise ValueError("payload too large for the 3-byte length field")
    header = bytes([0, 0, 0, 0, 0, 3, new_len & 0xFF, (new_len >> 8) & 0xFF, (new_len >> 16) & 0xFF, 0])
    data = header + payload + TRAILER
    with open(path, "wb") as f:
        f.write(data)
    return len(data)


def patch_uasset_serial_size(src_uasset_path, dst_uasset_path, new_uexp_total_size):
    """Copy src_uasset to dst_uasset with SerialSize patched to new_uexp_total_size - 4.

    Locates the field by searching for the OLD SerialSize (also computed as size-4 of whatever
    .uexp currently sits beside src_uasset) as a raw int64 LE -- this must be unique in the file,
    which holds for these small (~1-3KB) single-export BinaryAsset headers.
    """
    src_uexp_path = src_uasset_path[:-len(".uasset")] + ".uexp"
    old_uexp_size = os.path.getsize(src_uexp_path)
    old_serial_size = old_uexp_size - 4

    with open(src_uasset_path, "rb") as f:
        data = bytearray(f.read())

    needle = struct.pack("<q", old_serial_size)
    offset = data.find(needle)
    if offset == -1:
        raise ValueError(f"{src_uasset_path}: could not locate SerialSize={old_serial_size} in uasset bytes")
    if data.find(needle, offset + 1) != -1:
        raise ValueError(f"{src_uasset_path}: SerialSize value {old_serial_size} is not unique in uasset bytes")

    new_serial_size = new_uexp_total_size - 4
    struct.pack_into("<q", data, offset, new_serial_size)

    with open(dst_uasset_path, "wb") as f:
        f.write(data)
    return offset, new_serial_size
