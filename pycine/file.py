import datetime
import os
import struct
from contextlib import contextmanager

from pycine import cine


def read_header(cine_file):
    with open(cine_file, "rb") as f:
        header = {
            "cinefileheader": cine.CINEFILEHEADER(),
            "bitmapinfoheader": cine.BITMAPINFOHEADER(),
            "setup": cine.SETUP(),
        }
        f.readinto(header["cinefileheader"])
        f.readinto(header["bitmapinfoheader"])
        f.readinto(header["setup"])

        # header_length = ctypes.sizeof(header['cinefileheader'])
        # bitmapinfo_length = ctypes.sizeof(header['bitmapinfoheader'])

        f.seek(header["cinefileheader"].OffImageOffsets)
        header["pImage"] = struct.unpack(
            "{}q".format(header["cinefileheader"].ImageCount), f.read(header["cinefileheader"].ImageCount * 8)
        )

    return header


def write_header(cine_file, header, backup=True):
    if backup:
        backup_header(cine_file)

    with open_ignoring_read_only(cine_file, "rb+") as f:
        f.write(header["cinefileheader"])
        f.write(header["bitmapinfoheader"])
        f.write(header["setup"])


def backup_header(cine_file):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    header = read_header(cine_file)
    with open(cine_file + f"_metadata_backup_{now}", "xb") as f:
        f.write(header["cinefileheader"])
        f.write(header["bitmapinfoheader"])
        f.write(header["setup"])


@contextmanager
def open_ignoring_read_only(file_path, mode):
    mode_before = os.stat(file_path).st_mode
    os.chmod(file_path, 0o600)

    with open(file_path, mode) as f:
        yield f

    os.chmod(file_path, mode_before)
