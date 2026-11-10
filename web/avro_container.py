"""Pure-Python AVRO object-container codec for the browser page.

``fastavro`` 1.10.0 publishes wheels with a C extension. Pyodide cannot install
that wheel. ``app.avro_io`` imports ``reader`` and ``writer`` and calls
``writer(file, schema, records)``. The static site mounts this module as
``fastavro`` so ``backup_table`` still runs. The local API keeps the installed
``fastavro`` package. ``tests/test_avro_container.py`` reads these bytes with
the real ``fastavro.reader``.

The codec covers the schemas in ``app.avro_io``: a flat record of ``int`` and
``string`` fields, null codec, one or more data blocks.
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable, Iterator

MAGIC = b"Obj\x01"
INT32_MIN = -2147483648
INT32_MAX = 2147483647


def _zigzag(value: int) -> int:
    return (value << 1) ^ (value >> 63)


def _encode_long(value: int) -> bytes:
    number = _zigzag(value)
    out = bytearray()
    while (number & ~0x7F) != 0:
        out.append((number & 0x7F) | 0x80)
        number >>= 7
    out.append(number & 0x7F)
    return bytes(out)


def _encode_bytes(raw: bytes) -> bytes:
    return _encode_long(len(raw)) + raw


def _as_int32(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{field_name} must be an Avro int")
    if value < INT32_MIN or value > INT32_MAX:
        raise ValueError(f"{field_name} is outside the Avro int range")
    return value


def _encode_record(schema: dict, record: dict) -> bytes:
    out = bytearray()
    for field in schema["fields"]:
        name = field["name"]
        if name not in record:
            raise ValueError(f"{name} is missing")
        kind = field["type"]
        value = record[name]
        if kind == "int":
            out += _encode_long(_as_int32(value, name))
        elif kind == "string":
            if not isinstance(value, str):
                raise ValueError(f"{name} must be an Avro string")
            out += _encode_bytes(value.encode("utf-8"))
        else:
            raise ValueError(f"unsupported Avro type: {kind}")
    return bytes(out)


def writer(
    fo,
    schema: dict,
    records: Iterable[dict],
    codec: str = "null",
    sync_marker: bytes | None = None,
    **_kwargs,
) -> None:
    """Write an object-container file. Signature matches the ``fastavro.writer`` call."""
    if codec != "null":
        raise ValueError("only the null codec is implemented")
    if not isinstance(schema, dict):
        raise ValueError("schema must be a dict")
    if sync_marker is None:
        sync_marker = os.urandom(16)
    if len(sync_marker) != 16:
        raise ValueError("sync marker must be 16 bytes")

    schema_bytes = json.dumps(schema).encode("utf-8")
    header = bytearray(MAGIC)
    header += _encode_long(2)
    header += _encode_bytes(b"avro.codec")
    header += _encode_bytes(b"null")
    header += _encode_bytes(b"avro.schema")
    header += _encode_bytes(schema_bytes)
    header += _encode_long(0)
    header += sync_marker

    rows = list(records)
    fo.write(header)
    if not rows:
        return
    payload = bytearray()
    for record in rows:
        payload += _encode_record(schema, record)
    fo.write(_encode_long(len(rows)))
    fo.write(_encode_long(len(payload)))
    fo.write(payload)
    fo.write(sync_marker)


def _read_long(data: bytes, index: int) -> tuple[int, int]:
    shift = 0
    number = 0
    while True:
        if index >= len(data):
            raise ValueError("truncated Avro long")
        byte = data[index]
        index += 1
        number |= (byte & 0x7F) << shift
        if not byte & 0x80:
            break
        shift += 7
        if shift > 63:
            raise ValueError("Avro long is too wide")
    value = (number >> 1) ^ -(number & 1)
    return value, index


def _read_bytes(data: bytes, index: int) -> tuple[bytes, int]:
    length, index = _read_long(data, index)
    if length < 0 or index + length > len(data):
        raise ValueError("truncated Avro bytes")
    return data[index : index + length], index + length


def _read_map(data: bytes, index: int) -> tuple[dict[str, bytes], int]:
    metadata: dict[str, bytes] = {}
    while True:
        count, index = _read_long(data, index)
        if count == 0:
            return metadata, index
        if count < 0:
            raise ValueError("sized Avro map blocks are not implemented")
        for _ in range(count):
            key, index = _read_bytes(data, index)
            value, index = _read_bytes(data, index)
            metadata[key.decode("utf-8")] = value


def _read_record(data: bytes, index: int, schema: dict) -> tuple[dict, int]:
    record = {}
    for field in schema["fields"]:
        kind = field["type"]
        name = field["name"]
        if kind == "int":
            value, index = _read_long(data, index)
            record[name] = value
        elif kind == "string":
            raw, index = _read_bytes(data, index)
            record[name] = raw.decode("utf-8")
        else:
            raise ValueError(f"unsupported Avro type: {kind}")
    return record, index


def decode_container(data: bytes) -> tuple[list[dict], dict]:
    if not data.startswith(MAGIC):
        raise ValueError("not an Avro object container")
    metadata, index = _read_map(data, len(MAGIC))
    codec = metadata.get("avro.codec", b"null")
    if codec != b"null":
        raise ValueError("only the null codec is implemented")
    schema = json.loads(metadata["avro.schema"].decode("utf-8"))
    if index + 16 > len(data):
        raise ValueError("truncated Avro sync marker")
    sync = data[index : index + 16]
    index += 16
    records: list[dict] = []
    while index < len(data):
        count, index = _read_long(data, index)
        if count <= 0:
            raise ValueError("non-positive Avro block count")
        size, index = _read_long(data, index)
        end = index + size
        if end + 16 > len(data):
            raise ValueError("truncated Avro block")
        for _ in range(count):
            record, index = _read_record(data, index, schema)
            records.append(record)
        if index != end:
            raise ValueError("Avro block size does not match its records")
        if data[index : index + 16] != sync:
            raise ValueError("Avro sync marker does not match the header")
        index += 16
    return records, schema


def reader(fo, *_args, **_kwargs) -> Iterator[dict]:
    """Iterate records. ``app.avro_io`` imports this name."""
    records, _schema = decode_container(fo.read())
    return iter(records)
