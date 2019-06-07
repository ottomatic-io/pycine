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
            annotation = struct.unpack("{}B".format(
                annotation_size - 8), f.read((annotation_size - 8) // 8))
            header["Annotation"] = annotation

            image_size = struct.unpack("I", f.read(4))[0]

            data = f.read(image_size)

            raw_image = create_raw_array(data, header)

            yield raw_image
            frame += 1
            count -= 1


def read_frames(cine_file, start_frame=1, count=None):
    header = read_header(cine_file)
    if header["bitmapinfoheader"].biCompression:
        bpp = 12
    else:
        bpp = header["setup"].RealBPP

    raw_images = frame_reader(
        cine_file, header, start_frame=start_frame, count=count)

    return raw_images, header["setup"], bpp


def unpack_10bit(data, width, height):
    packed = np.frombuffer(data, dtype="uint8").astype(np.uint16)
    unpacked = np.zeros([height, width], dtype="uint16")

    unpacked.flat[::4] = (packed[::5] << 2) | (packed[1::5] >> 6)
    unpacked.flat[1::4] = ((packed[1::5] & 0b00111111)
                           << 4) | (packed[2::5] >> 4)
    unpacked.flat[2::4] = ((packed[2::5] & 0b00001111)
                           << 6) | (packed[3::5] >> 2)
    unpacked.flat[3::4] = ((packed[3::5] & 0b00000011) << 8) | packed[4::5]

    return unpacked


def create_raw_array(data, header):
    width, height = header["bitmapinfoheader"].biWidth, header["bitmapinfoheader"].biHeight

    if header["bitmapinfoheader"].biCompression:
        raw_image = unpack_10bit(data, width, height)
        raw_image = linLUT[raw_image].astype(np.uint16)
        raw_image = np.interp(raw_image, [64, 4064], [
                              0, 2 ** 12 - 1]).astype(np.uint16)
    else:
        raw_image = np.frombuffer(data, dtype="uint16")
        raw_image.shape = (height, width)
        raw_image = np.flipud(raw_image)
        raw_image = np.interp(
            raw_image, [header["setup"].BlackLevel, header["setup"].WhiteLevel], [
                0, 2 ** header["setup"].RealBPP - 1]
        ).astype(np.uint16)

    return raw_image
