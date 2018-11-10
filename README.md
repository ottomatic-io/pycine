# pycine

[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/ambv/black)
[![Codacy Badge](https://api.codacy.com/project/badge/Grade/42cbb1d8fd0d4be99d802206c83b7b29)](https://app.codacy.com/app/OTTOMATIC/pycine?utm_source=github.com&utm_medium=referral&utm_content=OTTOMATIC-IO/pycine&utm_campaign=Badge_Grade_Dashboard)

Reading Vision Research .cine files with python


## Installation

### Release Version

```
pip install pycine
```


### Development version

```
pip install git+https://github.com/ottomatic-io/pycine.git
```


## Usage

To edit metadata:
```
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

To read frames:
```
Usage: pfs_raw [OPTIONS] CINE_FILE [OUT_PATH]

Options:
  --file_format [.png|.jpg|.tif]
  --start_frame INTEGER
  --count INTEGER
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```


## Jupyter notebook

Check out an example on how to use the library from a jupyter notebook:
[notebooks/Display frames.ipynb](notebooks/Display%20frames.ipynb)
