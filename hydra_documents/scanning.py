import socket
import struct
from dataclasses import dataclass

from django.conf import settings


class ScannerError(Exception):
    """Base error for failures that must never be treated as a clean scan."""


class ScannerUnavailable(ScannerError):
    pass


class ScannerProtocolError(ScannerError):
    pass


@dataclass(frozen=True)
class ScanResult:
    clean: bool
    scanner: str
    result: str


def _read_record(sock):
    response = bytearray()
    while b"\0" not in response:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response.extend(chunk)
        if len(response) > 65536:
            raise ScannerProtocolError("scanner response exceeded the safety limit")
    record = bytes(response).split(b"\0", 1)[0].decode("utf-8", "replace").strip()
    if not record:
        raise ScannerProtocolError("scanner returned an empty response")
    return record


def _connect():
    try:
        return socket.create_connection(
            (settings.HYDRA_CLAMD_HOST, settings.HYDRA_CLAMD_PORT),
            timeout=settings.HYDRA_CLAMD_TIMEOUT_SECONDS,
        )
    except OSError as error:
        raise ScannerUnavailable("malware scanner is unavailable") from error


def _scan_with_clamd(file_handle):
    try:
        with _connect() as sock:
            sock.settimeout(settings.HYDRA_CLAMD_TIMEOUT_SECONDS)
            sock.sendall(b"zINSTREAM\0")
            file_handle.seek(0)
            while True:
                chunk = file_handle.read(64 * 1024)
                if not chunk:
                    break
                sock.sendall(struct.pack(">I", len(chunk)))
                sock.sendall(chunk)
            sock.sendall(struct.pack(">I", 0))
            record = _read_record(sock)
    except ScannerError:
        raise
    except (OSError, ValueError) as error:
        raise ScannerUnavailable("malware scan did not complete") from error
    finally:
        try:
            file_handle.seek(0)
        except (OSError, ValueError):
            pass

    if record.endswith(": OK"):
        return ScanResult(clean=True, scanner="clamd", result="clean")
    if record.endswith(" FOUND") and ": " in record:
        threat = record.rsplit(": ", 1)[1][:-len(" FOUND")].strip()
        return ScanResult(
            clean=False,
            scanner="clamd",
            result=(threat or "threat_detected")[:160],
        )
    raise ScannerProtocolError("malware scanner returned an unrecognized result")


def scan_file(file_handle):
    if settings.HYDRA_DOCUMENT_SCANNER.strip().lower() == "clamd":
        return _scan_with_clamd(file_handle)
    raise ScannerUnavailable("no malware scanner is configured")


def scanner_health():
    if settings.HYDRA_DOCUMENT_SCANNER.strip().lower() != "clamd":
        return False, "HYDRA_DOCUMENT_SCANNER must be set to clamd"
    try:
        with _connect() as sock:
            sock.settimeout(settings.HYDRA_CLAMD_TIMEOUT_SECONDS)
            sock.sendall(b"zPING\0")
            response = _read_record(sock)
    except ScannerError:
        return False, "ClamAV scanner is unavailable"
    return (
        response == "PONG",
        "ClamAV scanner answered PING" if response == "PONG" else "ClamAV PING failed",
    )
