#!/usr/bin/env python
# coding: utf-8
"""
Read phantom .cine files.

Usage:
cineraw.py CINEFILE [options] (-f FORMAT | --display)

Options:
-f --format FORMAT          can be one of .png, .jpg or .tif
-o --outdir FORMAT          [default: .]
-d --display                show a preview
-s --start_frame FRAME      start from FRAME [default: 1]
-c --count COUNT            [default: 1]
--fieldnames                print all fieldnames
-h --help                   print this help message

"""
import os
import struct

import cv2
import numpy as np
from docopt import docopt

import cine
from linLUT import linLUT


def read_header(myfile):
    with open(myfile, 'rb') as f:
        header = {}
        header['cinefileheader'] = cine.CINEFILEHEADER()
        header['bitmapinfoheader'] = cine.BITMAPINFOHEADER()
        header['setup'] = cine.SETUP()
        f.readinto(header['cinefileheader'])
        f.readinto(header['bitmapinfoheader'])
        f.readinto(header['setup'])

        # header_length = ctypes.sizeof(header['cinefileheader'])
        # bitmapinfo_length = ctypes.sizeof(header['bitmapinfoheader'])

        f.seek(header['cinefileheader'].OffImageOffsets)
        header['pImage'] = struct.unpack('{}q'.format(header['cinefileheader'].ImageCount),
                                         f.read(header['cinefileheader'].ImageCount * 8))

    return header


def frame_reader(myfile, header, start_frame=1, count=None):
    frame = start_frame
    if not count:
        count = header['cinefileheader'].ImageCount

    with open(myfile, 'rb') as f:
        while count:
            frame_index = frame - 1
            print "Reading frame {}".format(frame)

            f.seek(header['pImage'][frame_index])

            AnnotationSize = struct.unpack('I', f.read(4))[0]
            Annotation = struct.unpack('{}B'.format(AnnotationSize - 8),
                                       f.read((AnnotationSize - 8) / 8))
            header["Annotation"] = Annotation

            ImageSize = struct.unpack('I', f.read(4))[0]

            data = f.read(ImageSize)

            raw_image = create_raw_array(data, header)

            yield raw_image
            frame += 1
            count -= 1


def read_frames(myfile, start_frame=1, count=None):
    header = read_header(myfile)
    if header['bitmapinfoheader'].biCompression:
        bpp = 12
    else:
        bpp = header['setup'].RealBPP

    raw_images = frame_reader(myfile, header, start_frame=start_frame, count=count)

    return raw_images, header['setup'], bpp


def unpack_10bit(data, width, height):
    packed = np.frombuffer(data, dtype='uint8').astype('uint16')
    unpacked = np.zeros([height, width], dtype='uint16')

    unpacked.flat[::4] = (packed[::5] << 2) | (packed[1::5] >> 6)
    unpacked.flat[1::4] = ((packed[1::5] & 0b00111111) << 4) | (packed[2::5] >> 4)
    unpacked.flat[2::4] = ((packed[2::5] & 0b00001111) << 6) | (packed[3::5] >> 2)
    unpacked.flat[3::4] = ((packed[3::5] & 0b00000011) << 8) | packed[4::5]

    return unpacked


def create_raw_array(data, header):
    width, height = header['bitmapinfoheader'].biWidth, header['bitmapinfoheader'].biHeight
    BayerPatterns = {3: 'gbrg', 4: 'rggb'}
    pattern = BayerPatterns[header['setup'].CFA]

    if header['bitmapinfoheader'].biCompression:
        raw_image = unpack_10bit(data, width, height)
        fix_bad_pixels(raw_image, header['setup'].WhiteLevel, pattern)
        raw_image = linLUT[raw_image].astype(np.uint16)
        raw_image = np.interp(raw_image, [64, 4064], [0, 2**12-1]).astype(np.uint16)
    else:
        raw_image = np.frombuffer(data, dtype='uint16')
        raw_image.shape = (height, width)
        fix_bad_pixels(raw_image, header['setup'].WhiteLevel, pattern)
        raw_image = np.flipud(raw_image)
        raw_image = np.interp(raw_image, [header['setup'].BlackLevel, header['setup'].WhiteLevel],
                                         [0, 2**header['setup'].RealBPP-1]).astype(np.uint16)

    return raw_image


def fix_bad_pixels(raw_image, white_level, pattern):
    hot = np.where(raw_image > white_level)
    coordinates = zip(hot[0], hot[1])

    masked_image = np.ma.MaskedArray(raw_image)

    for color in 'rgb':
        # FIXME: reuse those masks for whitebalancing
        mask = gen_mask(pattern, color, raw_image)
        masked_image.mask = mask
        smooth = cv2.medianBlur(masked_image, ksize=3)

        for coord in coordinates:
            if not mask[coord]:
                print 'fixing {} in color {}'.format(coord, color)
                raw_image[coord] = smooth[coord]

        print 'done color', color

    masked_image.mask = np.ma.nomask


def color_pipeline(raw, setup, bpp=12):
    """Order from:
    http://www.visionresearch.com/phantomzone/viewtopic.php?f=20&t=572#p3884
    """
    # 1. Offset the raw image by the amount in flare
    print "fFlare: ", setup.fFlare

    # 2. White balance the raw picture using the white balance component of cmatrix
    BayerPatterns = {3: 'gbrg', 4: 'rggb'}
    pattern = BayerPatterns[setup.CFA]

    whitebalance_raw(raw, setup, pattern)

    # 3. Debayer the image
    rgb_image = cv2.cvtColor(raw, cv2.COLOR_BAYER_GB2RGB)

    # convert to float
    rgb_image = rgb_image.astype(np.float32) / (2**bpp-1)

    # 4. Apply the color correction matrix component of cmatrix
    """
    From the documentation:
    ...should decompose this
    matrix in two components: a diagonal one with the white balance to be
    applied before interpolation and a normalized one to be applied after
    interpolation.
    """
    cmCalib = np.asarray(setup.cmCalib).reshape(3, 3)

    # normalize matrix
    ccm = cmCalib / cmCalib.sum(axis=1)[:, np.newaxis]

    # or should it be normalized this way?
    ccm2 = cmCalib.copy()
    ccm2[0][0] = 1 - ccm2[0][1] - ccm2[0][2]
    ccm2[1][1] = 1 - ccm2[1][0] - ccm2[1][2]
    ccm2[2][2] = 1 - ccm2[2][0] - ccm2[2][1]

    print "cmCalib", cmCalib
    print "ccm: ", ccm
    print "ccm2", ccm2

    rgb_image = np.dot(rgb_image, ccm.T)

    # 5. Apply the user RGB matrix umatrix
    cmUser = np.asarray(setup.cmUser).reshape(3, 3)
    rgb_image = np.dot(rgb_image, cmUser.T)

    # 6. Offset the image by the amount in offset
    print "fOffset: ", setup.fOffset

    # 7. Apply the global gain
    print "fGain: ", setup.fGain

    # 8. Apply the per-component gains red, green, blue
    print "fGainR, fGainG, fGainB: ", setup.fGainR, setup.fGainG, setup.fGainB

    # 9. Apply the gamma curves; the green channel uses gamma, red uses gamma + rgamma and blue uses gamma + bgamma
    print "fGamma, fGammaR, fGammaB: ", setup.fGamma, setup.fGammaR, setup.fGammaB
    rgb_image = apply_gamma(rgb_image, setup)

    # 10. Apply the tone curve to each of the red, green, blue channels
    fTone = np.asarray(setup.fTone)
    print setup.ToneLabel, setup.TonePoints, fTone

    # 11. Add the pedestals to each color channel, and linearly rescale to keep the white point the same.
    print "fPedestalR, fPedestalG, fPedestalB: ", setup.fPedestalR, setup.fPedestalG, setup.fPedestalB

    # 12. Convert to YCrCb using REC709 coefficients

    # 13. Scale the Cr and Cb components by chroma.
    print "fChroma: ", setup.fChroma

    # 14. Rotate the Cr and Cb components around the origin in the CrCb plane by hue degrees.
    print "fHue: ", setup.fHue

    return rgb_image


def whitebalance_raw(raw, setup, pattern):
    cmCalib = np.asarray(setup.cmCalib).reshape(3, 3)
    whitebalance = np.diag(cmCalib)

    print "WBGain: ", np.asarray(setup.WBGain)
    print "WBView: ", np.asarray(setup.WBView)
    print "fWBTemp: ", setup.fWBTemp
    print "fWBCc: ", setup.fWBCc
    print "cmCalib: ", cmCalib
    print "whitebalance: ", whitebalance

    # FIXME: maybe use .copy()
    wb_raw = np.ma.MaskedArray(raw)

    wb_raw.mask = gen_mask(pattern, 'r', wb_raw)
    wb_raw *= whitebalance[0]
    wb_raw.mask = gen_mask(pattern, 'g', wb_raw)
    wb_raw *= whitebalance[1]
    wb_raw.mask = gen_mask(pattern, 'b', wb_raw)
    wb_raw *= whitebalance[2]

    wb_raw.mask = np.ma.nomask

    return wb_raw


def gen_mask(pattern, c, image):
    def color_kern(pattern, c):
        return np.array([[pattern[0] != c, pattern[1] != c],
                         [pattern[2] != c, pattern[3] != c]])

    (h, w) = image.shape[:2]
    cells = np.ones((h/2, w/2))

    return np.kron(cells, color_kern(pattern, c))


def apply_gamma(rgb_image, setup):
    # FIXME: using 2.2 for now because 8.0 from the sample image seems way out of place
    rgb_image **= (1/2.2)
    # rgb_image **= (1/setup.fGamma)
    # rgb_image[:,:,0] **= (1/(setup.fGammaR + setup.fGamma))
    # rgb_image[:,:,2] **= (1/(setup.fGammaB + setup.fGamma))

    return rgb_image


def resize(rgb_image, new_width):
    height, width = rgb_image.shape[:2]
    new_height = int(new_width * (float(height) / width))
    res = cv2.resize(rgb_image, (new_width, new_height))

    return res


def display(image_8bit):
    cv2.imshow('image', image_8bit)
    cv2.waitKey(0)
    cv2.destroyAllWindows()


def save(rgb_image, outfile):
    cv2.imwrite(outfile, rgb_image * 255)


if __name__ == '__main__':
    args = docopt(__doc__)

    start_frame = int(args['--start_frame'])
    count = int(args['--count'])

    raw_images, setup, bpp = read_frames(args['CINEFILE'],
                                         start_frame=start_frame,
                                         count=count)

    rgb_images = (color_pipeline(raw_image, setup=setup, bpp=bpp) for raw_image in raw_images)

    if args['--fieldnames']:
        for field_name, field_type in setup._fields_:
            attr = getattr(setup, field_name)
            print field_name, np.asarray(attr)

    for i, rgb_image in enumerate(rgb_images):
        frame = start_frame + i

        if setup.EnableCrop:
            rgb_image = rgb_image[setup.CropRect.top:setup.CropRect.bottom + 1,
                                  setup.CropRect.left:setup.CropRect.right + 1]

        if setup.EnableResample:
            rgb_image = cv2.resize(rgb_image, (setup.ResampleWidth,
                                               setup.ResampleHeight))
        if args['--format']:
            ending = args['--format'].strip('.')
            name = os.path.splitext(os.path.basename(args['CINEFILE']))[0]
            outname = '{}-{:06d}.{}'.format(name, frame, ending)
            outfile = os.path.join(args['--outdir'], outname)
            print "Writing File {}".format(outname)
            save(rgb_image, outfile)

        if args['--display']:
            display(resize(rgb_image, 500))
