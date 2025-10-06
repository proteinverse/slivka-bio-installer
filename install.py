from collections import ChainMap
import collections.abc
import os
import re
import shutil
import subprocess
from pathlib import Path
import tempfile
from typing import Iterable

import click
from ruamel.yaml import YAML


yaml = YAML()


class TemplateYamlLoader(YAML):
    def __init__(self, mapping, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mapping = mapping
        self.Constructor.add_constructor('tag:yaml.org,2002:str', self.replace_placeholder)

    def _match_repl(self, match):
        return self._mapping[match.group(1)]

    def replace_placeholder(self, loader, node):
        value = loader.construct_scalar(node)
        return re.sub(r'\{\{ ?([\w\-]+:[\w\-\/\.]+) ?\}\}', self._match_repl, value)


@click.command()
@click.option("--conda-exe")
@click.option("--service", "-s", "services", multiple=True, default=[''], show_default="all services")
@click.argument("path", type=Path)
def main(conda_exe, services, path: Path):
    try:
        conda_installer = CondaInstaller(conda_exe, path / "conda_env")
    except Exception as e:
        conda_installer = None
        click.echo(f"Failed to init conda installer: {e}")
    else:
        click.echo(f"Conda available: '{conda_installer.conda_exe}'")

    try:
        docker_installer = DockerInstaller()
    except Exception as e:
        docker_installer = None
        click.echo(f"Failed to init docker installer: {e}")
    else:
        click.echo(f"Docker available")

    service_files = [
        path
        for path in Path.cwd().joinpath("services").glob("**/*.service.yaml")
        for name in services
        if path.name.startswith(name)
    ]
    if not service_files:
        click.echo("Nothing to install.")
        raise click.Abort
    click.echo("Installing:")
    for service_file in sorted(service_files):
        yaml_data = yaml.load(service_file)
        click.echo(f" - {yaml_data['name']}:{yaml_data['version']}")
    click.confirm("Confirm", default=True, abort=True)

    init_slivka(path)
    copy_shared_files(path)

    for service_file in service_files:
        base_name = service_file.name[:-len(".service.yaml")]
        click.echo(f"Installing: {base_name}")
        applicable_installers = []
        if service_file.with_name(f"{base_name}.conda.yaml").is_file() and conda_installer is not None:
            applicable_installers.append(conda_installer)
        if service_file.with_name(f"{base_name}.docker.yaml").is_file() and docker_installer is not None:
            applicable_installers.append(docker_installer)
        if not applicable_installers:
            click.echo(f"No applicable installer for {base_name}")
            continue
        while True:
            installer_names = []
            choices = []
            if conda_installer in applicable_installers:
                installer_names.append("[c]onda")
                choices.append("c")
            if docker_installer in applicable_installers:
                installer_names.append("[d]ocker")
                choices.append("d")
            ans = click.prompt(
                f"Choose installer: {', '.join(installer_names)}",
                type=click.Choice(choices, case_sensitive=False),
                show_choices=False
            )
            if ans == "c":
                installer = conda_installer
                installer_file = service_file.with_name(f"{base_name}.conda.yaml")
            if ans == "d":
                installer = docker_installer
                installer_file = service_file.with_name(f"{base_name}.docker.yaml")
            try:
                output_file = installer.install_service(installer_file, path)
                click.echo(f"{click.style('Installed', fg='bright_green')}: {output_file.name}")
                break
            except Exception as e:
                click.echo(f"{type(e).__name__}: {e}")
                ans = click.prompt(
                    "[R]etry, [S]kip, [A]bort",
                    type=click.Choice("rsai", case_sensitive=False),
                    show_choices=False
                )
                if ans == 's':
                    click.echo(click.style("Skipping", fg="yellow")+ f": {base_name}")
                    break
                elif ans == 'a':
                    raise click.Abort



class DataFilesContextMap(dict):
    def __init__(self, paths, dst_root, key_prefix=""):
        super().__init__()
        for src_path, dst_path in paths:
            self[f"{key_prefix}path:{src_path}"] = str(dst_root / dst_path)


def local_paths_context(paths, dst_root):
    return DataFilesContextMap(paths, dst_root, key_prefix="local-")


def runtime_paths_context(paths, dst_root):
    return DataFilesContextMap(paths, dst_root, key_prefix="runtime-")


def find_data_dirs(src_root: Path, patterns: list[dict]) -> list[Path]:
    """
    Find data directories under the given path matching the given patterns.
    If no patterns are specified, all directories are included.
    If the first pattern is not 'include', {include: *} is added.

    :return: Set of relative paths matching the patterns
    """
    if not patterns:
        patterns = [{'include': '*'}]
    if 'include' not in patterns[0]:
        patterns.insert(0, {'include': '*'})
    matched = set()
    for rule in patterns:
        if len(rule) > 1:
            raise ValueError(f"Rule contains multiple keys: {rule}")
        key, val = next(iter(rule.items()))
        if '**' in val or os.path.sep in val:
            raise ValueError(f"Recursive globbing is not supported: {val}")
        if key == "include":
            operation = matched.add
        elif key == "exclude":
            operation = matched.discard
        else:
            raise KeyError(f"Invalid rule: {key}")
        for path in src_root.glob(val):
            if path.is_dir():
                operation(path.relative_to(src_root))
    return matched



def copy_data_dirs(copy_list: Iterable[tuple[Path, Path]]):
    """
    Copy data directories to the target root.

    :param Iterable[tuple[Path, Path]] copy_paths:
        Tuples of source and target absolute paths.
    :return:
        List of copied paths
    """
    copied = []
    for src_path, dst_path in copy_list:
        if dst_path.exists():
            if click.confirm(f"Directory exists: {dst_path}. Overwrite?", default=False):
                shutil.rmtree(dst_path)
            else:
                click.echo(f"Skipping: {dst_path}")
                continue
        shutil.copytree(src_path, dst_path)
        copied.append((src_path, dst_path))
    return copied


def find_and_copy_data_dirs(src_root: Path, patterns: list[dict], target_root: Path) -> list[tuple[Path, Path]]:
    """
    Find data directories under the given path matching the given patterns
    and copy them to the target root.
    If no patterns are specified, all directories are included.
    If the first pattern is not 'include', {include: *} is added.

    :param Path src_root:
        Source directory to search for data directories.
    :param list[dict] patterns:
        List of patterns to match source data directories.
    :param Path target_root:
        Target directory to copy data directories to.
    """
    files_mapping = [
        (match, match)
        for match in find_data_dirs(src_root, patterns)
    ]
    copy_data_dirs(
        (src_root / src_path, target_root / dst_path)
        for src_path, dst_path in files_mapping
    )
    return files_mapping


def copy_service_file(template_file: Path, target_root: Path, template_data: dict, prepend_command=[]):
    yaml = TemplateYamlLoader(template_data)
    service_config = yaml.load(template_file)
    service_config["command"] = [*prepend_command, *service_config["command"]]
    (target_root / "services").mkdir(exist_ok=True)
    dest_file = target_root / "services" / template_file.name
    yaml.dump(service_config, dest_file)
    return dest_file


def interpolate_string(data: str, context: dict):
    return re.sub(r'\{\{ ?([\w\-]+:[\w\/\.]+) ?\}\}', lambda m: context[m.group(1)], data)


def interpolate_list(data: list, context: dict):
    return [
        interpolate_string(item, context) if isinstance(item, str) else
        interpolate_dict(item, context) if isinstance(item, collections.abc.Mapping) else
        interpolate_list(item, context) if isinstance(item, collections.abc.Iterable) else
        item
        for item in data
    ]


def interpolate_dict(data: dict, context: dict):
    return {
        key: (
            interpolate_string(value, context) if isinstance(value, str) else
            interpolate_dict(value, context) if isinstance(value, collections.abc.Mapping) else
            interpolate_list(value, context) if isinstance(value, collections.abc.Iterable) else
            value
        )
        for key, value in data.items()
    }


class CondaEnvContextMap:
    def __init__(self, conda_exe, env_path):
        self.conda_exe = conda_exe
        self.env_path = env_path

    def __getitem__(self, item):
        key, name = item.split(":", 1)
        if key == "env":
            return os.environ[name]
        if key == "which":
            exe = shutil.which(name, path=f"{self.env_path}/bin{os.pathsep}{os.environ['PATH']}")
            if not exe:
                raise ValueError(f"Executable not found: {name}")
            return exe
        raise KeyError(item)


class CondaInstaller:
    def __init__(self, conda_exe, conda_env_root: Path):
        self.conda_exe = shutil.which(conda_exe) if conda_exe else detect_conda_exe()
        if not self.conda_exe:
            raise FileNotFoundError(f"Invalid conda exe: {conda_exe}")
        self.conda_env_root = conda_env_root

    def install_service(self, install_file: Path, project_path: Path):
        """
        Install conda environment from the given install file.

        :param Path install_file:
            Path to the conda install file.
        :param Path project_path:
            Path to the target project directory.
        """
        config = yaml.load(install_file)
        # strip .conda.yaml suffix
        base_name = install_file.name[:-len(".conda.yaml")]

        if "environment" in config:
            with tempfile.NamedTemporaryFile(suffix=".yaml") as env_file:
                yaml.dump(config["environment"], env_file)
                env_file.flush()
                env_path = self.create_env(base_name, Path(env_file.name))
        else:
            env_file = config.get("environment-file", "environment.yaml")
            env_file = install_file.with_name(env_file)
            env_path = self.create_env(base_name, env_file)
        env_context = CondaEnvContextMap(self.conda_exe, env_path)

        dst_data_dir = project_path / "data" / base_name
        copied_data_dirs = find_and_copy_data_dirs(
            src_root=install_file.parent,
            target_root=dst_data_dir,
            patterns=config.get("files", [])
        )
        data_dirs_context = local_paths_context(
            copied_data_dirs, dst_root=dst_data_dir
        )
        runtime_data_dirs_context = runtime_paths_context(
            copied_data_dirs, dst_root=dst_data_dir
        )

        context_map = ChainMap(
            env_context, data_dirs_context, runtime_data_dirs_context
        )
        vars_context = {
            f"var:{key}": val
            for key, val in interpolate_dict(config.get("vars", {}), context_map).items()
        }
        context_map.maps.insert(0, vars_context)

        command_prefix = [self.conda_exe, "run", "-p", str(env_path)]
        return copy_service_file(
            template_file=install_file.with_name(f"{base_name}.service.yaml"),
            target_root=project_path,
            template_data=context_map,
            prepend_command=command_prefix
        )


    def create_env(self, env_name: str, env_file: Path):
        if not env_file.is_file():
            raise FileNotFoundError(f"{env_file}")
        os.makedirs(self.conda_env_root, exist_ok=True)
        if not self.conda_env_root.is_dir():
            raise NotADirectoryError(f"Invalid conda env root: {self.conda_env_root}")
        env_path = (self.conda_env_root / env_name).resolve()
        if env_path.exists():
            if not click.confirm(f"Conda env already exists: {env_path}. Overwrite?"):
                return env_path
        proc = subprocess.run(
            [
                self.conda_exe, "env", "create",
                "--prefix", env_path,
                "--file", env_file,
                "--yes", "--quiet"
            ]
        )
        proc.check_returncode()
        return env_path


def detect_conda_exe():
    try:
        return next(filter(None, _iter_conda_exe()), None)
    except StopIteration:
        raise Exception("No conda executable found.")


def _iter_conda_exe():
    yield os.environ.get("MAMBA_EXE")
    yield os.environ.get("CONDA_EXE")
    yield shutil.which("micromamba")
    yield shutil.which("mamba")
    yield shutil.which("conda")


class DockerEnvContextMap:
    def __init__(self, docker_exe, image_name):
        self.docker_exe = docker_exe
        self.image_name = image_name
        self._env_vars = None

    def __getitem__(self, item):
        key, name = item.split(":", 1)
        if key == "env":
            return self.get_env_var(name)
        if key == "which":
            return self.get_which(name)
        raise KeyError(item)

    def get_env_var(self, name):
        if self._env_vars is None:
            self._populate_env_vars()
        return self._env_vars[name]

    def _populate_env_vars(self):
        output = subprocess.check_output(
            [
                self.docker_exe, "run",
                "--rm", "--entrypoint", "env",
                self.image_name
            ],
            text=True
        )
        self._env_vars = dict(
            line.split("=", 1) for line in output.splitlines()
        )

    def get_which(self, prog_name):
        try:
            output = subprocess.check_output(
                [
                    self.docker_exe, "run",
                    "--rm", "--entrypoint", "which",
                    self.image_name,
                    prog_name
                ],
                text=True
            )
        except subprocess.CalledProcessError as e:
            if e.returncode == 1:
                raise ValueError(f"Executable not found: {prog_name}")
        return output.strip()


class DockerInstaller:
    def __init__(self):
        self.docker_exe = shutil.which("docker")
        if not self.docker_exe:
            raise FileNotFoundError("Docker not found.")

    def install_service(self, install_file: Path, project_path: Path):
        config = yaml.load(install_file)
        # strip .docker.yaml suffix
        base_name = install_file.name[:-len(".docker.yaml")]
        image_name = self._make_image(install_file.parent, config)
        env_context = DockerEnvContextMap(self.docker_exe, image_name)

        dst_data_dir = project_path / "data" / base_name
        copied_data_dirs = find_and_copy_data_dirs(
            src_root=install_file.parent,
            target_root=dst_data_dir,
            patterns=config.get("files", [])
        )
        data_dirs_context = local_paths_context(
            copied_data_dirs, dst_root=dst_data_dir
        )
        runtime_data_dirs_context = runtime_paths_context(
            copied_data_dirs, dst_root=Path("/data")
        )

        context_map = ChainMap(
            env_context, data_dirs_context, runtime_data_dirs_context
        )
        vars_context = {
            f"var:{key}": val
            for key, val in interpolate_dict(config.get("vars", {}), context_map).items()
        }
        context_map.maps.insert(0, vars_context)

        mount_args = sum(
            (
                ("--mount", f"type=bind,src={dst_data_dir / p},dst=/data/{p},ro")
                for _, p in copied_data_dirs
            ),
            ()
        )
        wrapper_script = os.path.join("${SLIVKA_HOME}", "scripts", "run_with_docker.sh")
        command_prefix = [
            shutil.which("env"),
            # DOCKER_* variables are essential for "run_with_docker.sh" but slivka removes them
            *(f"{k}={v}" for k, v in os.environ.items() if k.startswith("DOCKER_")),
            "bash",
            wrapper_script,
            *mount_args,
            image_name
        ]
        return copy_service_file(
            template_file=install_file.with_name(f"{base_name}.service.yaml"),
            target_root=project_path,
            template_data=context_map,
            prepend_command=command_prefix
        )


    def _make_image(self, src_root: Path, config: dict):
        if "pull" in config:
            if isinstance(config["pull"], str):
                return pull_docker_image(
                    image_name=config["pull"]
                )
            else:
                return pull_docker_image(
                    image_name=config["pull"]["image"],
                    image_tag=config["pull"].get("tag"),
                    platform=config["pull"].get("platform")
                )
        if "build" in config:
            return build_docker_image(
                dockerfile=src_root / config["build"]["dockerfile"],
                image_name=config["build"]["image"],
                image_tag=config["build"].get("tag"),
                platform=config["build"].get("platform")
            )
        raise ValueError("No image specified in the config.")



def build_docker_image(dockerfile: Path, image_name, image_tag=None, platform=None):
    if not dockerfile.is_file():
        raise FileNotFoundError(f"{dockerfile}")
    full_tag = f"{image_name}:{image_tag}" if image_tag else image_name
    options = []
    if platform:
        options.extend(["--platform", platform])
    proc = subprocess.run(
        [
            "docker", "buildx", "build",
            "--tag", full_tag,
            *options,
            "--file", dockerfile,
            dockerfile.parent
        ],
        cwd=dockerfile.parent
    )
    proc.check_returncode()
    return full_tag



def pull_docker_image(image_name, image_tag=None, platform=None):
    full_tag = f"{image_name}:{image_tag}" if image_tag else image_name
    options = []
    if platform:
        options.extend(["--platform", platform])
    proc = subprocess.run(
        [
            "docker", "image", "pull",
            *options,
            "--quiet",
            full_tag
        ]
    )
    proc.check_returncode()
    return full_tag


def init_slivka(slivka_path: Path):
    subprocess.run(["slivka", "init", slivka_path])


def copy_shared_files(target_root: Path):
    shared_dir = Path.cwd() / "shared"
    for root, dirs, files in os.walk(shared_dir):
        root = Path(root)
        rel_root: Path = root.relative_to(shared_dir)
        for dirname in dirs:
            (target_root / rel_root / dirname).mkdir(exist_ok=True)
        for filename in files:
            target_file = target_root / rel_root / filename
            if not target_file.exists():
                shutil.copy2(root / filename, target_file)
            else:
                click.echo(f"File exists: {target_file}")


if __name__ == '__main__':
    main()
