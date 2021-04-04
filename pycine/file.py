import ctypes as ct
import datetime
import os
import struct
from contextlib import contextmanager
from io import BufferedIOBase, RawIOBase, BufferedReader
from typing import Dict, Union, TypedDict, List, BinaryIO

import numpy as np

from pycine import cine
from pycine.cine import CINEFILEHEADER, BITMAPINFOHEADER, SETUP


class Header(TypedDict):
    cinefileheader: cine.CINEFILEHEADER
    bitmapinfoheader: cine.BITMAPINFOHEADER
    setup: cine.SETUP
    pImage: List[int]
    timestamp: np.ndarray
    exposuretime: np.ndarray


def read_header(cine_file: Union[str, bytes, os.PathLike]) -> Header:
    with open(cine_file, "rb") as f:
        header: Header = {
            "cinefileheader": cine.CINEFILEHEADER(),
            "bitmapinfoheader": cine.BITMAPINFOHEADER(),
            "setup": cine.SETUP(),
            "pImage": [],
            "timestamp": np.empty(0),
            "exposuretime": np.empty(0),
        }
        f.readinto(header["cinefileheader"])
        f.readinto(header["bitmapinfoheader"])
        f.seek(header["cinefileheader"].OffSetup)
        f.readinto(header["setup"])

        # header_length = ctypes.sizeof(header['cinefileheader'])
        # bitmapinfo_length = ctypes.sizeof(header['bitmapinfoheader'])

        f.seek(header["cinefileheader"].OffImageOffsets)
        header["pImage"] = struct.unpack(
            f"{header['cinefileheader'].ImageCount}q", f.read(header["cinefileheader"].ImageCount * 8)
        )

        header = read_tagged_block(f, header)

    return header


def read_chd_header(chd_file: Union[str, bytes, os.PathLike]) -> Header:
    """
    read the .chd header file created when Vision Research software saves the images in a file format other than .cine
    """
    with open(chd_file, "rb") as f:
        header: Header = {
            "cinefileheader": cine.CINEFILEHEADER(),
            "bitmapinfoheader": cine.BITMAPINFOHEADER(),
            "setup": cine.SETUP(),
            "pImage": [],
            "timestamp": np.empty(0),
            "exposuretime": np.empty(0),
        }
        f.readinto(header["cinefileheader"])
        f.readinto(header["bitmapinfoheader"])
        f.seek(header["cinefileheader"].OffSetup)
        f.readinto(header["setup"])

    return header


def read_tagged_block(f: BinaryIO, header: Header) -> Header:
    header_length = ct.sizeof(header["cinefileheader"])
    bitmapinfo_length = ct.sizeof(header["bitmapinfoheader"])
    if not header["cinefileheader"].OffSetup + header["setup"].Length < header["cinefileheader"].OffImageOffsets:
        return header

    position = header_length + bitmapinfo_length + header["setup"].Length
    f.seek(position)

    while position < header["cinefileheader"].OffImageOffsets:
        blocksize = np.frombuffer(f.read(4), dtype="uint32")[0]
        tagtype = np.frombuffer(f.read(2), dtype="uint16")[0]

        f.seek(2, 1)  # reserved bits

        if tagtype == 1002:  # Time only block
            temp = np.frombuffer(f.read(blocksize - 8), dtype="uint32").reshape(header["cinefileheader"].ImageCount, -1)
            header["timestamp"] = temp[:, 1] + (((2 ** 32 - 1) & temp[:, 0]) / (2 ** 32))

        elif tagtype == 1003:  # Exposure only block
            header["exposuretime"] = np.frombuffer(f.read(blocksize - 8), dtype="uint32") * 2 ** -32

        else:
            f.seek(blocksize - 8, 1)
        position += blocksize

    return header


def write_header(
    cine_file: Union[str, bytes, os.PathLike],
    header: Header,
    backup=True,
):
    if backup:
        backup_header(cine_file)

    with open_ignoring_read_only(cine_file, "rb+") as f:
        f.write(header["cinefileheader"])
        f.write(header["bitmapinfoheader"])
        f.seek(header["cinefileheader"].OffSetup)
        f.write(header["setup"])


def backup_header(cine_file: Union[str, bytes, os.PathLike]):
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    header = read_header(cine_file)
    with open(str(cine_file) + f"_metadata_backup_{now}", "xb") as f:
        f.write(header["cinefileheader"])
        f.write(header["bitmapinfoheader"])
        f.seek(header["cinefileheader"].OffSetup)
        f.write(header["setup"])


@contextmanager
def open_ignoring_read_only(file_path: Union[str, bytes, os.PathLike], mode: str):
    mode_before = os.stat(file_path).st_mode
    os.chmod(file_path, 0o600)

    with open(file_path, mode) as f:
        yield f

    os.chmod(file_path, mode_before)
