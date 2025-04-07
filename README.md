## Cloning the respository

This repository uses other repositories which are included as git submodules.
By default `git clone` does not clone submodules recursively.
Use `--recurse-submodules` clone the repo with all included submodules e.g.

```
git clone --recurse-submodules https://github.com/proteinverse/slivka-bio-installer.git
```

If you have already cloned the repository without submodules then run

```
git submodule init && git submodule update
```

## Prerequisities

As a bare minimum, the installer requires python, click, ruamel.yaml and slivka.
You can install all the dependencies with conda package manager:

```
conda create -n slivka-installer -c conda-forge python=3.10 click ruamel.yaml slivka::slivka
```

If you prefer the latest beta version of slivka then install slivka from the _beta_ subdirectory

```
conda create -n slivka-installer -c conda-forge python=3.10 click ruamel.yaml slivka/label/beta::slivka
```

The installer uses _conda_ and _docker_ which need to be available for proper functiononing. 

## Installing tools

Move to the directory where you cloned the installer repository and run:

```
python install.py <PATH>
```
subsituting the project destination for _&lt;PATH&gt;_.
The installer will display the list of tools that will be installed and prompt for the installation method for each one of them.
If the installation fails, you will be prompted to retry, skip the installation of that service, abort and stop the installer or ignore the error and proceed with the installation.

