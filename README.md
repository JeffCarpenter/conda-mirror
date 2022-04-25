# Conda/Mamba package and dependency downloader/mirror

Download conda packages and dependencies for mirroring in a local conda repository.

This is based on a modified version of [conda-mirror](https://github.com/conda-incubator/conda-mirror)

This uses the [mamba solver](https://github.com/mamba-org/mamba) if installed to find all dependencies of a package or packages, otherwise the Conda solver is used.

## Installation
```
git clone https://github.com/manics/conda-mamba-downloader
pip install .
```

## Usage

E.g. Download `jupyterlab 3.*` for `linux-64`, using `./target` as the local conda repository:

```sh
conda-mamba-download --platform linux-64 --target-directory ./target --channel conda-forge jupyterlab=3
```

E.g. Download `jupyterlab 3.*` and `aws-session-manager-plugin` for `win-64`:

```sh
conda-mamba-download --platform win-64 --target-directory ./target --channel conda-forge jupyterlab=3 aws-session-manager-plugin
```

Since two packages are specified the downloader will ensure both packages and dependencies are compatible with each other.

The downloader will add to existing packages in the target directory but will not include them when calculating dependencies for the requested packages.
This is so that you can build up a set of packages for mirroring without requiring every package in the mirror is compatible with each other.

The target-directory can be used as a local channel, or served by a web server.
