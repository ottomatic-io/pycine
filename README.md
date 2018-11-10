# pycine

Reading Vision Research cine files with python


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
