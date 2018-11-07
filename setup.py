from setuptools import setup, find_packages

setup(
    name="pycine",
    description="This package allows handling of .cine files created by Vision Research Phantom® cameras.",
    url="https://github.com/OTTOMATIC-IO/pycine",
    author="Ben Hagen",
    author_email="ben@ottomatic.io",
    packages=find_packages(),
    include_package_data=True,
    install_requires=["click", "docopt", "opencv-python"],
    entry_points={"console_scripts": ["pfs_meta = pycine.cli.pfs_meta:cli", "pfs_raw = pycine.cli.pfs_raw:cli"]},
    use_scm_version=True,
    setup_requires=["pytest-runner", "setuptools_scm"],
    tests_require=["pytest"],
)
