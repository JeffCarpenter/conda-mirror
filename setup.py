from setuptools import find_packages, setup

with open("README.md") as f:
    long_description = f.read()

setup(
    name="conda_mamba_downloader",
    author="Eric Dill",
    packages=find_packages(),
    author_email="eric.dill@maxpoint.com",
    description="Mirror an upstream conda channel to a local directory",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/regro/conda-mirror",
    platforms=["Linux", "Mac OSX", "Windows"],
    license="BSD 3-Clause",
    use_scm_version={
        "write_to": "conda_mamba_downloader/_version.py",
        "write_to_template": '__version__ = "{version}"\n',
    },
    setup_requires=["setuptools_scm"],
    install_requires=["pyyaml", "requests", "tqdm"],
    # conda must be installed using conda not pip
    # Optional (not on pypi): ["mamba", "libmambapy"]
    entry_points={
        "console_scripts": [
            "conda-mamba-download = conda_mamba_downloader.download:main",
        ]
    },
)
