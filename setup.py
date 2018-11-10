from setuptools import setup, find_packages

with open("README.md", "r") as fh:
    long_description = fh.read()

setup(
    author="Ben Hagen",
    author_email="ben@ottomatic.io",
    description="This package allows handling of .cine files created by Vision Research Phantom® cameras.",
    entry_points={"console_scripts": ["pfs_meta = pycine.cli.pfs_meta:cli", "pfs_raw = pycine.cli.pfs_raw:cli"]},
    include_package_data=True,
    install_requires=["click", "docopt", "opencv-python", "colorama"],
    long_description=long_description,
    long_description_content_type="text/markdown",
    name="pycine",
    packages=find_packages(),
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest"],
    url="https://github.com/ottomatic-io/pycine",
    use_scm_version=True,
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)",
        "Operating System :: OS Independent",
    ],
)
