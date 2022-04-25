#!/usr/bin/env python
# https://github.com/mamba-org/mamba/blob/micromamba-0.23.0/mamba/mamba/mamba.py

import argparse
from .conda_mirror import _init_logger as conda_mirror_init_logger
from .conda_mirror import main as conda_mirror_main
import libmambapy as mamba_api
from mamba import repoquery
import sys
from tempfile import TemporaryDirectory, gettempdir


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
        help="The place where packages should be mirrored to",
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
        "--num-threads",
        action="store",
        default=1,
        type=int,
        help="Num of threads for validation. 1: Serial mode. 0: All available.",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print version and quit",
        default=False,
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
    print(args)
    if len(args.platform) > 1:
        raise NotImplementedError("Multiple platforms not supported yet")

    for platform in args.platform:
        download(args, platform, args.packages)


def download(args, platform, specs):
    print(platform, specs)
    # specs = ['jupyterlab>3', 'aws-session-manager-plugin']
    channels = args.channel or ["conda-forge"]
    pool = repoquery.create_pool(channels, platform, False)

    tmpdir = TemporaryDirectory()
    package_cache = mamba_api.MultiPackageCache([tmpdir.name])

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
        channel, platform = t[0].rsplit("/", 1)
        if channel not in packages:
            packages[channel] = {}
        if platform not in packages[channel]:
            packages[channel][platform] = set()
        packages[channel][platform].add(t[1])

    # for channel, platforms in packages.items():
    #     for platform, pkgs in platforms.items():
    #         print(f"{channel}/{platform}")
    #         for pkg in sorted(pkgs):
    #             print(f"\t{pkg}")

    conda_mirror_args = {
        # "upstream_channel":
        "target_directory": args.target_directory,
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
            conda_mirror_args["platform"] = platform
            conda_mirror_args["whitelist"] = [{"filename": p} for p in pkgs]

            conda_mirror_main(**conda_mirror_args)
            break


if __name__ == "__main__":
    main(sys.argv)
