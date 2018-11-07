#!/usr/bin/env python3
import sys
from textwrap import dedent

import click

from pycine.file import read_header, write_header


def show_metadata(header, cine_file):
    record_rate = header["setup"].FrameRate
    playback_rate = header["setup"].fPbRate
    timecode_rate = header["setup"].fTcRate
    temp = header["setup"].fWBTemp
    cc = header["setup"].fWBCc
    tone_label = header["setup"].ToneLabel.decode("ascii")
    tone_points = list(header["setup"].fTone)[: header["setup"].TonePoints * 2]
    try:
        created_by = header["setup"].CreatedBy.decode("ascii")
    except ValueError:
        created_by = ""
    out = dedent(
        f"""
        Clip: {cine_file}
        Created by: {created_by}
        Record FPS: {record_rate}
        Playback FPS: {playback_rate}
        Timecode FPS: {timecode_rate}
        Temp: {temp}
        CC: {cc}
        CalibrationInfo: {header['setup'].CalibrationInfo}
        OpticalFilter: {header['setup'].OpticalFilter}
        cmCalib: {list(header['setup'].cmCalib)}
        Tone points: {tone_label} {' '.join([str(p) for p in tone_points])}
    """
    ).strip()
    click.echo(out + "\n")


def parse_tone(tone):
    tone = tone.split()
    if len(tone) % 2:
        tone_label = tone.pop(0)
    else:
        tone_label = ""
    tone_points = len(tone) // 2
    if tone_points > 32:
        click.secho("You can only set up to 32 tone points!", fg="red")
        sys.exit()
    tone = tuple(float(x) for x in tone)
    return tone_label, tone_points, tone


def ensure_minimal_software_version(header, cine_file, version=709):
    if header["setup"].SoftwareVersion < version:
        sys.exit(f"Software version of {cine_file} is too old.")


@click.group(help="This tool allows .cine file metadata manipulation. Use COMMAND --help for more info.")
def cli():
    pass


@cli.command(help="Show metadata")
@click.argument("clips", nargs=-1, type=click.Path(exists=True, readable=True))
def show(clips):
    for cine_file in clips:
        try:
            source_header = read_header(cine_file)
            ensure_minimal_software_version(source_header, cine_file, 709)

            show_metadata(source_header, cine_file)
        except Exception as e:
            click.echo(f"Could not read {cine_file}:")
            click.echo(e)
            click.echo()


# noinspection PyPep8Naming
@cli.command(help='Copy metadata from a source clip')
@click.option("--all_metadata", help="Copy color temperature, color correction and tone curve.", is_flag=True)
@click.option(
    "--wb",
    help="Copy white balance and color correction. This currently copies the whole calibration matrix as well.",
    is_flag=True,
)
@click.option("--tone", help="Copy tone curve.", is_flag=True)
@click.argument("source", nargs=1, type=click.Path(exists=True, readable=True))
@click.argument("destinations", nargs=-1, type=click.Path(exists=True, readable=True, dir_okay=False, file_okay=True))
def copy(all_metadata, wb, tone, source, destinations):
    source_header = read_header(source)
    ensure_minimal_software_version(source_header, source, 709)

    for d in destinations:
        dest_header = read_header(d)
        ensure_minimal_software_version(dest_header, d, 709)

        if wb or all_metadata:
            click.echo(f"Temp: {source_header['setup'].fWBTemp}")
            click.echo(f"CC: {source_header['setup'].fWBCc}")
            dest_header["setup"].fWBTemp = source_header["setup"].fWBTemp
            dest_header["setup"].fWBCc = source_header["setup"].fWBCc
            dest_header["setup"].cmCalib = source_header["setup"].cmCalib
            dest_header["setup"].WBGain = source_header["setup"].WBGain

        if tone or all_metadata:
            tone_label = source_header["setup"].ToneLabel.decode("ascii")
            tone_points = list(source_header["setup"].fTone)[: source_header["setup"].TonePoints * 2]
            click.echo(f"Tone points: {tone_label} {' '.join([str(p) for p in tone_points])}")
            dest_header["setup"].ToneLabel = source_header["setup"].ToneLabel
            dest_header["setup"].TonePoints = source_header["setup"].TonePoints
            dest_header["setup"].fTone = source_header["setup"].fTone

        click.secho(f"Writing metadata to {d}.", fg="green")
        write_header(d, dest_header)


# noinspection PyPep8Naming
@cli.command('set', help="Set metadata")
@click.option("--temp", type=float, help="Set color temperature.")
@click.option("--cc", type=float, help="Set color correction.")
@click.option("--record_fps", type=int, help="Set record FPS.")
@click.option("--playback_fps", type=float, help="Set playback FPS.")
@click.option("--timecode_fps", type=float, help="Set timecode FPS.")
@click.option(
    "--tone", type=str, help='Set tone curve in the form of "[LABEL] x1 y1 x2 y2". You can set up to 32 xy points.'
)
@click.argument("destinations", nargs=-1, type=click.Path(exists=True, readable=True, dir_okay=False, file_okay=True))
def set_(destinations, temp, cc, record_fps, playback_fps, timecode_fps, tone):
    for d in destinations:
        dest_header = read_header(d)
        ensure_minimal_software_version(dest_header, d, 709)

        if temp:
            click.secho("WARNING: This does not yet change the calibration matrix.", fg="red")
            dest_header["setup"].fWBTemp = temp

        if cc:
            click.secho("WARNING: This does not yet change the calibration matrix.", fg="red")
            dest_header["setup"].fWBCc = cc

        if tone:
            tone_label, tone_points, tone = parse_tone(tone)

            dest_header["setup"].ToneLabel = bytes(tone_label, "ascii")
            dest_header["setup"].TonePoints = tone_points
            dest_header["setup"].fTone = tone

        if record_fps:
            dest_header["setup"].FrameRate = playback_fps

        if playback_fps:
            dest_header["setup"].fPbRate = playback_fps

        if timecode_fps:
            dest_header["setup"].fTcRate = timecode_fps

        if any([temp, cc, record_fps, playback_fps, timecode_fps, tone]):
            click.secho(f"Writing metadata to {d}.", fg="green")
            write_header(d, dest_header)


if __name__ == "__main__":
    cli()
