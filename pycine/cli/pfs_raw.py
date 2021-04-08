#!/usr/bin/env python3
import os
import functools

import click
import cv2
import numpy as np


from pycine.color import color_pipeline
from pycine.raw import read_frames
from pycine.viewer import view_cine


def image_post_processing(image, setup, bpp):
    if setup.CFA in [3, 4]:
        image = color_pipeline(image, setup=setup, bpp=bpp)
    elif setup.CFA == 0:
        pass
    else:
        raise ValueError("Sensor not supported")

    if setup.EnableCrop:
        image = image[setup.CropRect.top : setup.CropRect.bottom + 1, setup.CropRect.left : setup.CropRect.right + 1]

    if setup.EnableResample:
        image = cv2.resize(image, (setup.ResampleWidth, setup.ResampleHeight))
    return image


@click.command()
@click.option("--file-format", default=".png", type=click.Choice([".png", ".jpg", ".tif"]))
@click.option("--start-frame", default=1, type=click.INT)
@click.option("--count", default=None, type=click.INT)
@click.argument("cine_file", type=click.Path(exists=True, readable=True, dir_okay=False, file_okay=True))
@click.argument("out_path", required=False, type=click.Path(exists=True, dir_okay=True, file_okay=False))
@click.version_option()
def cli(
    file_format: str,
    start_frame: int,
    count: int,
    out_path: str,
    cine_file: str,
):
    images, setup, bpp = read_frames(cine_file, start_frame=start_frame, count=count)
    images.post_processing = functools.partial(image_post_processing, setup=setup, bpp=bpp)

    if not out_path:
        # cine count is not used here
        view_cine(images)
        return

    for i, rgb_image in enumerate(images):
        frame_number = start_frame + i

        ending = file_format.strip(".")
        name = os.path.splitext(os.path.basename(cine_file))[0]
        out_name = f"{name}-{frame_number:06d}.{ending}"
        out_file = os.path.join(out_path, out_name)
        print(f"Writing File {out_file}")
        interpolated = np.interp(rgb_image, [0, 2 ** bpp - 1], [0, 2 ** 16 - 1]).astype(np.uint16)
        cv2.imwrite(out_file, interpolated)


if __name__ == "__main__":
    cli()
