# pycine

[![PyPI version](https://badge.fury.io/py/pycine.svg)](https://pypi.org/project/pycine/)
[![GitHub license](https://img.shields.io/github/license/OTTOMATIC-IO/pyphantom.svg)](https://github.com/OTTOMATIC-IO/pyphantom/blob/master/LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/42cbb1d8fd0d4be99d802206c83b7b29)](https://app.codacy.com/app/OTTOMATIC/pycine?utm_source=github.com&utm_medium=referral&utm_content=OTTOMATIC-IO/pycine&utm_campaign=Badge_Grade_Dashboard)

Reading Vision Research .cine files with python


## Installation

### Release Version

#### With pip
If you have Python 3 installed you can just use `pip`:
```
pip3 install pycine
```

### Development version

```
pip install git+https://github.com/ottomatic-io/pycine.git
```

## Example usage

### Changing the playback and timecode framerates
```
pfs_meta set --playback-fps 60/1.001 --timecode_fps 60/1.001 A001C001_190302_16001.cine
```

You can also set metadata for multiple clips at once:
```
pfs_meta set --playback-fps 24/1.001 --timecode_fps 24/1.001 *.cine
```

## Help
Every command has its own help output. Just append `--help`:

```
$ pfs_meta --help
Usage: pfs_meta [OPTIONS] COMMAND [ARGS]...

  This tool allows .cine file metadata manipulation. Use COMMAND --help for
  more info.

Options:
  --help  Show this message and exit.

Commands:
  copy  Copy metadata from a source clip
  set   Set metadata
  show  Show metadata
```


```
$ pfs_meta set --help
Usage: pfs_meta set [OPTIONS] [DESTINATIONS]...

  Set metadata

Options:
  --temp FLOAT          Set color temperature.
  --cc FLOAT            Set color correction.
  --record-fps INTEGER  Set record FPS.
  --playback-fps TEXT   Set playback FPS. Use 60 or 60/1.001 but not 59.94
  --timecode-fps TEXT   Set timecode FPS. Use 60 or 60/1.001 but not 59.94
  --tone TEXT           Set tone curve in the form of "[LABEL] x1 y1 x2 y2".
                        You can set up to 32 xy points.
  --help                Show this message and exit.
```


```
$ pfs_raw --help
Usage: pfs_raw [OPTIONS] CINE_FILE [OUT_PATH]

Options:
  --file-format [.png|.jpg|.tif]
  --start-frame INTEGER
  --count INTEGER
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```


## Jupyter notebook

Check out an example on how to use the library from a jupyter notebook:
[notebooks/Display frames.ipynb](notebooks/Display%20frames.ipynb)
