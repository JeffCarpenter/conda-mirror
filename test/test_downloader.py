import pytest
from conda_mamba_downloader import download


def test_parse_environment_file(tmpdir):
    envfile = tmpdir.join("environment.yml")
    envfile.write(
        """
channels:
  - foo
dependencies:
  - bar>1.0
  - pip
"""
    )
    channels, specs = download.parse_environment_file(envfile)
    assert channels == ["foo"]
    assert specs == ["bar>1.0", "pip"]


def test_parse_environment_file_pip(tmpdir):
    envfile = tmpdir.join("environment.yml")
    envfile.write(
        """
channels:
  - foo
dependencies:
  - bar>1.0
  - pip:
      - abc
"""
    )
    with pytest.raises(Exception) as exc:
        download.parse_environment_file(envfile)
    assert exc.value.args == ("pip dependencies not supported",)


@pytest.mark.parametrize("platform", ["linux-64", "win-64"])
@pytest.mark.parametrize("solver", ["conda", "mamba"])
def test_solve_conda(platform, solver, tmpdir):
    if solver == "conda":
        solvef = download._solve_conda
    else:
        solvef = download._solve_mamba
    packages = solvef(
        channels=["main"],
        platform=platform,
        specs=["python<3.10", "traitlets>5,<6"],
        tmpdir=str(tmpdir),
    )
    # print(packages)

    assert list(packages.keys()) == ["main"]
    assert len(packages["main"].keys()) == 2
    assert platform in packages["main"].keys()
    assert "noarch" in packages["main"].keys()
    assert len(packages["main"]["noarch"]) > 1
    assert len(packages["main"][platform]) > 1

    found_python = False
    for p in packages["main"][platform]:
        if p.startswith("python-3.9."):
            found_python = True
            break
    assert found_python

    found_traitlets = False
    for p in packages["main"]["noarch"]:
        if p.startswith("traitlets-5."):
            found_traitlets = True
            break
    assert found_traitlets
