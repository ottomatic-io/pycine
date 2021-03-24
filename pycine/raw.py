import logging
import struct

import numpy as np

from pycine.file import read_header
from pycine.linLUT import linLUT

logger = logging.getLogger()


def frame_reader(cine_file, header, start_frame=1, count=None):
    frame = start_frame
    if not count:
        count = header["cinefileheader"].ImageCount

    with open(cine_file, "rb") as f:
        while count:
            frame_index = frame - 1
            logger.debug("Reading frame {}".format(frame))

            f.seek(header["pImage"][frame_index])

            annotation_size = struct.unpack("I", f.read(4))[0]
            annotation = struct.unpack("{}B".format(annotation_size - 8), f.read((annotation_size - 8) // 8))
            header["Annotation"] = annotation

            image_size = struct.unpack("I", f.read(4))[0]

            data = f.read(image_size)

            raw_image = create_raw_array(data, header)

            yield raw_image
            frame += 1
            count -= 1


def image_generator(cine_file, start_frame=False, start_frame_cine=False, count=None):
    """
    Get only a generator of raw images for specified cine file.

    Parameters
    ----------
    cine_file : str or file-like object
        A string containing a path to a cine file
    start_frame : int
        First image in a pile of images in cine file.
        If 0 is given, it means the first frame of the saved images would be readed in this function.
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
    if type(start_frame) == int and type(start_frame_cine) == int:
        raise ValueError("Do not specify both of start_frame and start_frame_cine")
    elif start_frame == False and start_frame_cine == False:
        fetch_head = 1
    elif type(start_frame) == int:
        fetch_head = start_frame
    elif type(start_frame_cine) == int:
        numfirst = header["cinefileheader"].FirstImageNo
        numlast = numfirst + header["cinefileheader"].ImageCount - 1
        fetch_head = start_frame_cine - numfirst
        if fetch_head < 0:
            strerr = "Cannot read frame %d. This cine has only from %d to %d."
            raise ValueError(strerr % (start_frame_cine, numfirst, numlast))
    raw_image_generator = frame_reader(cine_file, header, start_frame=fetch_head, count=count)
    return raw_image_generator


def read_frames(cine_file, start_frame=False, start_frame_cine=False, count=None):
    """
    Get a generator of raw images for specified cine file.

    Parameters
    ----------
    cine_file : str or file-like object
        A string containing a path to a cine file
    start_frame : int
        First image in a pile of images in cine file.
        If 0 is given, it means the first frame of the saved images would be readed in this function.
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
        A class containes setup data of the cine file
    bpp : int
        Bit depth of the raw images
    """
    header = read_header(cine_file)
    setup = header["setup"]
    raw_image_generator = image_generator(cine_file, start_frame, start_frame_cine, count)
    return raw_image_generator, setup, setup.RealBPP


def unpack_10bit(data, width, height):
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")

    unpacked.flat[::4] = (packed[::5] << 2) | (packed[1::5] >> 6)
    unpacked.flat[1::4] = ((packed[1::5] & 0b00111111) << 4) | (packed[2::5] >> 4)
    unpacked.flat[2::4] = ((packed[2::5] & 0b00001111) << 6) | (packed[3::5] >> 2)
    unpacked.flat[3::4] = ((packed[3::5] & 0b00000011) << 8) | packed[4::5]

    return unpacked


def unpack_12bit(data, width, height):
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")
    unpacked.flat[::2] = (packed[::3] << 4) | packed[1::3] >> 4
    unpacked.flat[1::2] = ((packed[1::3] & 0b00001111) << 8) | (packed[2::3])

    return unpacked


def create_raw_array(data, header):
    width, height = header["bitmapinfoheader"].biWidth, header["bitmapinfoheader"].biHeight

    if header["bitmapinfoheader"].biCompression == 0:  # uncompressed data
        if header["bitmapinfoheader"].biBitCount == 16:  # 16bit
            raw_image = np.frombuffer(data, dtype="uint16")
        if header["bitmapinfoheader"].biBitCount == 8:  # 8bit
            raw_image = np.frombuffer(data, dtype="uint8")
        raw_image.shape = (height, width)
        raw_image = np.flipud(raw_image)
        raw_image = np.interp(
            raw_image, [header["setup"].BlackLevel, header["setup"].WhiteLevel], [0, 2 ** header["setup"].RealBPP - 1]
        ).astype(np.uint16)

    elif header["bitmapinfoheader"].biCompression == 256:  # 10bit / P10 compressed
        raw_image = unpack_10bit(data, width, height)
        raw_image = linLUT[raw_image].astype(np.uint16)
        raw_image = np.interp(
            raw_image, [header["setup"].BlackLevel, header["setup"].WhiteLevel], [0, 2 ** header["setup"].RealBPP - 1]
        ).astype(np.uint16)

    elif header["bitmapinfoheader"].biCompression == 1024:  # 12bit / P12L compressed
        raw_image = unpack_12bit(data, width, height)
        raw_image = np.interp(
            raw_image, [header["setup"].BlackLevel, header["setup"].WhiteLevel], [0, 2 ** header["setup"].RealBPP - 1]
        ).astype(np.uint16)

    return raw_image
