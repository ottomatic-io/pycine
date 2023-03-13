import logging
import struct
from os import PathLike
from typing import Generator, Tuple, Union, Any

import numpy as np

from pycine.cine import SETUP
from pycine.file import read_header, Header
from pycine.linLUT import linLUT

logger = logging.getLogger()


def frame_reader(
    cine_file: Union[str, bytes, PathLike],
    header: Header,
    start_frame: int = 1,
    count: int = None,
    step: int = 1,
) -> Generator[np.ndarray, Any, None]:
    frame = start_frame
    if not count:
        count = header["cinefileheader"].ImageCount
    
    with open(cine_file, "rb") as f:
        while count // step:
            frame_index = frame - 1
            logger.debug(f"Reading frame {frame}")

            f.seek(header["pImage"][frame_index])

            annotation_size = struct.unpack("I", f.read(4))[0]
            annotation = struct.unpack(f"{annotation_size - 8}B", f.read((annotation_size - 8) // 8))
            # TODO: Save annotations

            image_size = struct.unpack("I", f.read(4))[0]

            data = f.read(image_size)

            raw_image = create_raw_array(data, header)

            yield raw_image
            frame += step
            count -= step


def read_bpp(header):
    """
    Get bit depth (bit per pixel) from header

    Parameters
    ----------
    header : dict
        A dictionary contains header information of the cine file

    Returns
    -------
    bpp : int
        Bit depth of the cine file
    """
    if header["bitmapinfoheader"].biCompression:
        # After applying the linearization LUT the bit depth is 12bit
        bpp = 12
    else:
        bpp = header["setup"].RealBPP
    return bpp


def image_generator(
        cine_file: Union[str, bytes, PathLike], start_frame: int = None, start_frame_cine: int = None, count: int = None, step: int =1
) -> Generator[np.ndarray, Any, None]:
    """
    Get only a generator of raw images for specified cine file.

    Parameters
    ----------
    cine_file : str or file-like object
        A string containing a path to a cine file
    start_frame : int
        First image in a pile of images in cine file.
        If 0 is given, it means the first frame of the saved images would be read in this function.
        Only start_frame or start_frame_cine should be specified.
        If both are specified, raise ValueError.
    start_frame_cine : int
        First image in a pile of images in cine file.
        This number corresponds to the frame number in Phantom Camera Control (PCC) application.
        Only start_frame or start_frame_cine should be specified.
        If both are specified, raise ValueError.
    count : int
        maximum number of frames to get.

    Returns
    -------
    raw_image_generator : generator
        A generator for raw image
    """
    header = read_header(cine_file)
    if start_frame and start_frame_cine:
        raise ValueError("Do not specify both of start_frame and start_frame_cine")
    elif not start_frame and not start_frame_cine:
        fetch_head = 1
    elif start_frame:
        fetch_head = start_frame
    elif start_frame_cine:
        first_image_number = header["cinefileheader"].FirstImageNo
        last_image_number = first_image_number + header["cinefileheader"].ImageCount - 1
        fetch_head = start_frame_cine - first_image_number
        if fetch_head < 0:
            raise ValueError(
                f"Cannot read frame {start_frame_cine:d}. This cine has only from {first_image_number:d} to {last_image_number:d}."
            )
    raw_image_generator = frame_reader(cine_file, header, start_frame=fetch_head, count=count, step=step)
    return raw_image_generator


def read_frames(
        cine_file: Union[str, bytes, PathLike], start_frame: int = None, start_frame_cine: int = None, count: int = None, step: int = 1
) -> Tuple[Generator[np.ndarray, Any, None], SETUP, int]:
    """
    Get a generator of raw images for specified cine file.

    Parameters
    ----------
    cine_file : str or file-like object
        A string containing a path to a cine file
    start_frame : int
        First image in a pile of images in cine file.
        If 0 is given, it means the first frame of the saved images would be read in this function.
        Only start_frame or start_frame_cine should be specified.
        If both are specified, raise ValueError.
    start_frame_cine : int
        First image in a pile of images in cine file.
        This number corresponds to the frame number in Phantom Camera Control (PCC) application.
        Only start_frame or start_frame_cine should be specified.
        If both are specified, raise ValueError.
    count : int
        maximum number of frames to get.

    Returns
    -------
    raw_image_generator : generator
        A generator for raw image
    setup : pycine.cine.tagSETUP class
        A class contains setup data of the cine file
    bpp : int
        Bit depth of the raw images
    """
    header = read_header(cine_file)
    bpp = read_bpp(header)
    setup = header["setup"]
    raw_image_generator = image_generator(cine_file, start_frame, start_frame_cine, count, step)
    return raw_image_generator, setup, bpp


def unpack_10bit(data: bytes, width: int, height: int) -> np.ndarray:
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")

    unpacked.flat[::4] = (packed[::5] << 2) | (packed[1::5] >> 6)
    unpacked.flat[1::4] = ((packed[1::5] & 0b00111111) << 4) | (packed[2::5] >> 4)
    unpacked.flat[2::4] = ((packed[2::5] & 0b00001111) << 6) | (packed[3::5] >> 2)
    unpacked.flat[3::4] = ((packed[3::5] & 0b00000011) << 8) | packed[4::5]

    return unpacked


def unpack_12bit(data: bytes, width: int, height: int) -> np.ndarray:
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")
    unpacked.flat[::2] = (packed[::3] << 4) | packed[1::3] >> 4
    unpacked.flat[1::2] = ((packed[1::3] & 0b00001111) << 8) | (packed[2::3])

    return unpacked


def create_raw_array(data: bytes, header) -> np.ndarray:
    width, height = header["bitmapinfoheader"].biWidth, header["bitmapinfoheader"].biHeight

    if header["bitmapinfoheader"].biCompression == 0:  # uncompressed data
        if header["bitmapinfoheader"].biBitCount == 16:  # 16bit
            raw_image = np.frombuffer(data, dtype="uint16")
        elif header["bitmapinfoheader"].biBitCount == 8:  # 8bit
            raw_image = np.frombuffer(data, dtype="uint8")
        else:
            raise ValueError("Only 16 and 8bit frames are supported")
        raw_image.shape = (height, width)
        raw_image = np.flipud(raw_image)
        raw_image = np.interp(
            raw_image, [header["setup"].BlackLevel, header["setup"].WhiteLevel], [0, 2 ** header["setup"].RealBPP - 1]
        ).astype(np.uint16)

    elif header["bitmapinfoheader"].biCompression == 256:  # 10bit / P10 compressed
        raw_image = unpack_10bit(data, width, height)
        raw_image = linLUT[raw_image].astype(np.uint16)
        raw_image = np.interp(raw_image, [64, 4064], [0, 2 ** 12 - 1]).astype(np.uint16)

    elif header["bitmapinfoheader"].biCompression == 1024:  # 12bit / P12L compressed
        raw_image = unpack_12bit(data, width, height)
        raw_image = np.interp(
            raw_image, [header["setup"].BlackLevel, header["setup"].WhiteLevel], [0, 2 ** header["setup"].RealBPP - 1]
        ).astype(np.uint16)

    else:
        raise ValueError("biCompression is invalid")

    return raw_image
