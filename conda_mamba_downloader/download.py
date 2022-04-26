#!/usr/bin/env python
# https://github.com/mamba-org/mamba/blob/micromamba-0.23.0/mamba/mamba/mamba.py

import argparse
import conda.api
import os.path
import sys
from tempfile import gettempdir

from .conda_mirror import _init_logger as conda_mirror_init_logger
from .conda_mirror import main as conda_mirror_main
from . import __version__

try:
    import libmambapy as mamba_api
    import mamba.repoquery as mamba_repoquery

    _MAMBA_ENABLED = True
except ImportError:
    _MAMBA_ENABLED = False


def main(argv=None):
    parser = argparse.ArgumentParser(description="conda package downloader")

    parser.add_argument(
        "--channel",
        "-c",
        action="append",
        help="Conda channel(s)",
    )
    parser.add_argument(
        "--target-directory",
        "-t",
        required=True,
        help=(
            "The place where packages should be mirrored to. "
            "Packages will be under <target-directory>/<channel>/<platform>/"
        ),
    )
    parser.add_argument(
        "--temp-directory",
        help="Temporary download location for the packages.",
        default=gettempdir(),
    )
    parser.add_argument(
        "--platform",
        action="append",
        required=True,
        help="The OS platform(s) to mirror. E.g. 'linux-64', 'osx-64', 'win-64'.",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        help=(
            "logging defaults to error/exception only. Takes up to three "
            "'-v' flags. '-v': warning. '-vv': info. '-vvv': debug."
        ),
        default=0,
    )
    # parser.add_argument(
    #     "--config",
    #     action="store",
    #     help="Path to the yaml config file",
    # )
    parser.add_argument(
        "--solver",
        help=(
            "Whether to use the mamba or conda solver. "
            "Default is to use mamba if available, otherwise conda."
        ),
        choices=["auto", "conda", "mamba"],
        default="auto",
    )
    parser.add_argument(
        "--num-threads",
        action="store",
        default=1,
        type=int,
        help="Num of threads for validation. 1: Serial mode. 0: All available.",
    )
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what will be downloaded. Will not validate existing packages",
        default=False,
    )
    parser.add_argument(
        "--minimum-free-space",
        help="Threshold for free diskspace. Given in megabytes.",
        type=int,
        default=1000,
    )
    parser.add_argument(
        "--max-retries",
        help="Maximum number of retries before a download error is reraised.",
        type=int,
        default=100,
    )
    parser.add_argument(
        "--no-progress",
        action="store_false",
        dest="show_progress",
        help="Do not display progress bars.",
    )
    parser.add_argument(
        "packages",
        nargs="+",
        help="Package specifications",
    )

    if not argv:
        argv = sys.argv
    args = parser.parse_args(argv[1:])
    if len(args.platform) > 1:
        raise NotImplementedError("Multiple platforms not supported yet")

    for platform in args.platform:
        download(args, platform, args.packages)


def _solve_conda(*, channels, platform, specs, tmpdir):
    if platform == "noarch":
        platforms = ["noarch"]
    else:
        platforms = [platform, "noarch"]

    solver = conda.api.Solver(
        prefix=tmpdir, channels=channels, subdirs=platforms, specs_to_add=specs
    )
    transaction = solver.solve_final_state()

    packages = {}
    for package in transaction:
        ch = package["channel"]
        filename = package["url"].rsplit("/", 1)[-1]
        if ch.name not in packages:
            packages[ch.name] = {}
        if ch.platform not in packages[ch.name]:
            packages[ch.name][ch.platform] = set()
        packages[ch.name][ch.platform].add(filename)

    return packages


def _solve_mamba(*, channels, platform, specs, tmpdir):
    pool = mamba_repoquery.create_pool(channels, platform, False)
    package_cache = mamba_api.MultiPackageCache([tmpdir])

    solver_options = [(mamba_api.SOLVER_FLAG_ALLOW_UNINSTALL, 1)]
    solver = mamba_api.Solver(pool, solver_options)

    mamba_solve_specs = [mamba_api.MatchSpec(s).conda_build_form() for s in specs]
    solver.add_jobs(mamba_solve_specs, mamba_api.SOLVER_INSTALL)

    solved = solver.solve()
    if not solved:
        print(solver.problems_to_str())
        # print(solver.all_problems_to_str())
        raise Exception("Unable to solve")

    transaction = mamba_api.Transaction(solver, package_cache, [])
    mmb_specs, to_link, to_unlink = transaction.to_conda()

    packages = {}
    for t in to_link:
        # t[0]: https://conda.anaconda.org/<channel>/<platform>
        _, channel, platform = t[0].rsplit("/", 2)
        if channel not in packages:
            packages[channel] = {}
        if platform not in packages[channel]:
            packages[channel][platform] = set()
        packages[channel][platform].add(t[1])

    return packages


def download(args, platform, specs):
    channels = args.channel
    if not channels:
        channels = ["conda-forge"]

    if args.solver == "auto":
        if _MAMBA_ENABLED:
            solver = _solve_mamba
        else:
            solver = _solve_conda
    elif args.solver == "mamba":
        if not _MAMBA_ENABLED:
            raise Exception("Mamba is not installed")
        solver = _solve_mamba
    else:
        solver = _solve_conda
    packages = solver(
        channels=channels, platform=platform, specs=specs, tmpdir=args.temp_directory
    )

    for channel, platforms in packages.items():
        for platform, pkgs in platforms.items():
            print(f"{channel}/{platform}")
            for pkg in sorted(pkgs):
                print(f"\t{pkg}")

    conda_mirror_args = {
        # "upstream_channel":
        # "target_directory":
        "temp_directory": args.temp_directory,
        # "platform":
        "num_threads": args.num_threads,
        "blacklist": [{"filename": "*"}],
        # "whitelist":
        "include_depends": False,
        "dry_run": args.dry_run,
        # Skip, otherwise existing files will be deleted if they don't match the specs
        "no_validate_target": True,
        "minimum_free_space": args.minimum_free_space,
        "proxies": None,
        "ssl_verify": True,
        "max_retries": args.max_retries,
        "show_progress": args.show_progress,
    }
    conda_mirror_init_logger(2)
    for channel, platforms in packages.items():
        for platform, pkgs in platforms.items():
            print(f"{channel}/{platform}")
            conda_mirror_args["upstream_channel"] = channel
            conda_mirror_args["target_directory"] = os.path.join(
                args.target_directory, channel
            )
            conda_mirror_args["platform"] = platform
            conda_mirror_args["whitelist"] = [{"filename": p} for p in pkgs]

            conda_mirror_main(**conda_mirror_args)


if __name__ == "__main__":
    main(sys.argv)
