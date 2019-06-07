import cv2
import numpy as np


def color_pipeline(raw, setup, bpp=12):
    """Order from:
    http://www.visionresearch.com/phantomzone/viewtopic.php?f=20&t=572#p3884
    """
    # 1. Offset the raw image by the amount in flare
    print("fFlare: ", setup.fFlare)

    # 2. White balance the raw picture
    #    using the white balance component of cmatrix
    BayerPatterns = {3: "gbrg", 4: "rggb"}
    pattern = BayerPatterns[setup.CFA]

    raw = whitebalance_raw(raw.astype(np.float32), setup,
                           pattern).astype(np.uint16)

    # 3. Debayer the image
    rgb_image = cv2.cvtColor(raw, cv2.COLOR_BAYER_GB2RGB)

    # convert to float
    rgb_image = rgb_image.astype(np.float32) / (2 ** bpp - 1)

    # return rgb_image

    # 4. Apply the color correction matrix component of cmatrix
    #
    # From the documentation:
    # ...should decompose this
    # matrix in two components: a diagonal one with the white balance to be
    # applied before interpolation and a normalized one to be applied after
    # interpolation.

    cmCalib = np.asarray(setup.cmCalib).reshape(3, 3)

    # normalize matrix
    ccm = cmCalib / cmCalib.sum(axis=1)[:, np.newaxis]

    # or should it be normalized this way?
    ccm2 = cmCalib.copy()
    ccm2[0][0] = 1 - ccm2[0][1] - ccm2[0][2]
    ccm2[1][1] = 1 - ccm2[1][0] - ccm2[1][2]
    ccm2[2][2] = 1 - ccm2[2][0] - ccm2[2][1]

    print("cmCalib", cmCalib)
    print("ccm: ", ccm)
    print("ccm2", ccm2)

    m = np.asarray(
        [
            1.4956012040024347,
            -0.5162879962189262,
            0.020686792216491584,
            -0.09884672458400766,
            0.757682383759598,
            0.34116434082440983,
            -0.04121405804689133,
            -0.5527871476076358,
            1.5940012056545272,
        ]
    ).reshape(3, 3)

    rgb_image = np.dot(rgb_image, m.T)
    # rgb_reshaped = rgb_image.reshape(
    # (rgb_image.shape[0] * rgb_image.shape[1], rgb_image.shape[2]))
    # rgb_image = np.dot(m, rgb_reshaped.T).T.reshape(rgb_image.shape)

    # 5. Apply the user RGB matrix umatrix
    # cmUser = np.asarray(setup.cmUser).reshape(3, 3)
    # rgb_image = np.dot(rgb_image, cmUser.T)

    # 6. Offset the image by the amount in offset
    print("fOffset: ", setup.fOffset)

    # 7. Apply the global gain
    print("fGain: ", setup.fGain)

    # 8. Apply the per-component gains red, green, blue
    print("fGainR, fGainG, fGainB: ", setup.fGainR, setup.fGainG, setup.fGainB)

    # 9. Apply the gamma curves;
    #    the green channel uses gamma,
    #    red uses gamma + rgamma and blue uses gamma + bgamma
    print("fGamma, fGammaR, fGammaB: ",
          setup.fGamma, setup.fGammaR, setup.fGammaB)
    rgb_image = apply_gamma(rgb_image, setup)

    # 10. Apply the tone curve to each of the red, green, blue channels
    fTone = np.asarray(setup.fTone)
    print(setup.ToneLabel, setup.TonePoints, fTone)

    # 11. Add the pedestals to each color channel,
    #     and linearly rescale to keep the white point the same.
    print("fPedestalR, fPedestalG, fPedestalB: ",
          setup.fPedestalR, setup.fPedestalG, setup.fPedestalB)

    # 12. Convert to YCrCb using REC709 coefficients

    # 13. Scale the Cr and Cb components by chroma.
    print("fChroma: ", setup.fChroma)

    # 14. Rotate the Cr and Cb components
    #     around the origin in the CrCb plane by hue degrees.
    print("fHue: ", setup.fHue)

    return rgb_image


def gen_mask(pattern, c, image):
    def color_kern(pattern, c):
        ret = [[pattern[0] != c, pattern[1] != c],
               [pattern[2] != c, pattern[3] != c]]
        return np.array(ret)

    (h, w) = image.shape[:2]
    cells = np.ones((h // 2, w // 2))

    return np.kron(cells, color_kern(pattern, c))


def whitebalance_raw(raw, setup, pattern):
    cmCalib = np.asarray(setup.cmCalib).reshape(3, 3)
    whitebalance = np.diag(cmCalib)
    whitebalance = [1.193739671606806, 1.0, 1.7885392465247287]

    print("WBGain: ", np.asarray(setup.WBGain))
    print("WBView: ", np.asarray(setup.WBView))
    print("fWBTemp: ", setup.fWBTemp)
    print("fWBCc: ", setup.fWBCc)
    print("cmCalib: ", cmCalib)
    print("whitebalance: ", whitebalance)

    # FIXME: maybe use .copy()
    wb_raw = np.ma.MaskedArray(raw)

    wb_raw.mask = gen_mask(pattern, "r", wb_raw)
    wb_raw *= whitebalance[0]
    wb_raw.mask = gen_mask(pattern, "g", wb_raw)
    wb_raw *= whitebalance[1]
    wb_raw.mask = gen_mask(pattern, "b", wb_raw)
    wb_raw *= whitebalance[2]

    wb_raw.mask = np.ma.nomask

    return wb_raw


def apply_gamma(rgb_image, setup):
    # FIXME: using 2.2 for now because 8.0 from
    #        the sample image seems way out of place
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
