import cv2
import numpy as np


def color_pipeline(raw, setup, bpp=12):
    print(
        "WARNING: The color pipeline implementation is incomplete "
        "and will most likely not output the colors you expect!"
    )

    """Order from:
    http://www.visionresearch.com/phantomzone/viewtopic.php?f=20&t=572#p3884
    """
    # 1. Offset the raw image by the amount in flare
    print("fFlare: ", setup.fFlare)

    # 2. White balance the raw picture using the white balance component of cmatrix
    white_balance, color_matrix = decompose_cmatrix(np.asarray(setup.cmCalib).reshape((3, 3)))
    BayerPatterns = {3: "gbrg", 4: "rggb"}
    pattern = BayerPatterns[setup.CFA]
    raw = whitebalance_raw(raw.astype(np.float32), white_balance, pattern).astype(np.uint16)

    # 3. Debayer the image
    rgb_image = cv2.cvtColor(raw, cv2.COLOR_BAYER_GB2RGB)

    # convert to float
    rgb_image = rgb_image.astype(np.float32) / (2 ** bpp - 1)

    # 4. Apply the color correction matrix component of cmatrix
    # FIXME: Applying the color matrix does not produce the expected results
    # rgb_image = np.dot(rgb_image, color_matrix.T)

    # 5. Apply the user RGB matrix umatrix
    # cmUser = np.asarray(setup.cmUser).reshape(3, 3)
    # rgb_image = np.dot(rgb_image, cmUser.T)

    # 6. Offset the image by the amount in offset
    print("fOffset: ", setup.fOffset)

    # 7. Apply the global gain
    print("fGain: ", setup.fGain)

    # 8. Apply the per-component gains red, green, blue
    print("fGainR, fGainG, fGainB: ", setup.fGainR, setup.fGainG, setup.fGainB)

    # 9. Apply the gamma curves; the green channel uses gamma, red uses gamma + rgamma and blue uses gamma + bgamma
    print("fGamma, fGammaR, fGammaB: ", setup.fGamma, setup.fGammaR, setup.fGammaB)
    rgb_image = apply_gamma(rgb_image, setup)

    # 10. Apply the tone curve to each of the red, green, blue channels
    fTone = np.asarray(setup.fTone)
    print(setup.ToneLabel, setup.TonePoints, fTone)

    # 11. Add the pedestals to each color channel, and linearly rescale to keep the white point the same.
    print("fPedestalR, fPedestalG, fPedestalB: ", setup.fPedestalR, setup.fPedestalG, setup.fPedestalB)

    # 12. Convert to YCrCb using REC709 coefficients

    # 13. Scale the Cr and Cb components by chroma.
    print("fChroma: ", setup.fChroma)

    # 14. Rotate the Cr and Cb components around the origin in the CrCb plane by hue degrees.
    print("fHue: ", setup.fHue)

    return (rgb_image * (2 ** bpp - 1)).astype(np.uint16)


def gen_mask(pattern, c, image):
    def color_kern(pattern, c):
        return np.array([[pattern[0] != c, pattern[1] != c], [pattern[2] != c, pattern[3] != c]])

    (h, w) = image.shape[:2]
    cells = np.ones((h // 2, w // 2))

    return np.kron(cells, color_kern(pattern, c))


def whitebalance_raw(raw, whitebalance, pattern):
    whitebalance = whitebalance.diagonal()

    # FIXME: maybe use .copy()
    wb_raw = np.ma.MaskedArray(raw)

    wb_raw.mask = gen_mask(pattern, "r", wb_raw)
    wb_raw *= whitebalance[0] / whitebalance[1]
    wb_raw.mask = gen_mask(pattern, "g", wb_raw)
    wb_raw *= whitebalance[1]
    wb_raw.mask = gen_mask(pattern, "b", wb_raw)
    wb_raw *= whitebalance[2] / whitebalance[1]

    wb_raw.mask = np.ma.nomask

    return wb_raw


def apply_gamma(rgb_image, setup):
    # FIXME: using 2.2 for now because 8.0 from the sample image seems way out of place
    # --> this is not at all how vri is doing it!
    rgb_image **= 1.0 / 2.2
    # rgb_image[:, :, 0] **= (1.0 / (setup.fGammaR + setup.fGamma))
    # rgb_image[:, :, 1] **= (1.0 / setup.fGamma)
    # rgb_image[:, :, 2] **= (1.0 / (setup.fGammaB + setup.fGamma))

    return rgb_image


def resize(rgb_image, new_width):
    height, width = rgb_image.shape[:2]
    new_height = int(new_width * (float(height) / width))
    res = cv2.resize(rgb_image, (new_width, new_height))

    return res


def decompose_cmatrix(calibration_matrix):
    """
    Decompose the calibration matrix into a diagonal one with the white balance
    and a normalized color matrix.
    """
    iwb = np.linalg.inv(calibration_matrix).dot(np.ones(3))
    iwb /= iwb.max()

    white_balance = np.zeros((3, 3))
    np.fill_diagonal(white_balance, iwb)

    color_matrix = calibration_matrix @ white_balance

    diagonal = white_balance.diagonal().copy()
    for i in range(3):
        if iwb[i] != 0:
            diagonal[i] = 1 / iwb[i]
    np.fill_diagonal(white_balance, diagonal)

    # Normalize
    color_matrix /= color_matrix[0].sum()

    return white_balance, color_matrix
