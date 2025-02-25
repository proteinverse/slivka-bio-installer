import os
import shutil
import subprocess
from pathlib import Path

import click
from ruamel.yaml import YAML


class TemplateYamlLoader(YAML):
    def __init__(self, mapping, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mapping = mapping
        self.Constructor.add_constructor('tag:yaml.org,2002:str', self.replace_placeholder)
    
    def replace_placeholder(self, loader, node):
        value = loader.construct_scalar(node)
        for key, val in self._mapping.items():
            value = value.replace(f"{{{{ {key} }}}}", val)
        return value


@click.command()
@click.option("--conda-exe")
@click.option("--service", "-s", "services", multiple=True, default=[''], show_default="all services")
@click.argument("path", type=Path)
def main(conda_exe, services, path: Path):
    try:
        conda_exe = conda_exe or next(filter(None, _iter_conda_exe()))
    except StopIteration:
        raise click.Abort("No conda environment specified!") from None
    click.echo(f"Using conda: '{conda_exe}'")

    services_to_install = [
        service_dir.resolve()
        for service_dir in path.joinpath("install").iterdir()
        for name in services
        if service_dir.stem.startswith(name) and next(service_dir.glob("*.service.yaml"), False)
    ]
    click.echo(services_to_install)


def _iter_conda_exe():
    yield os.environ.get("CONDA_EXE")
    yield os.environ.get("MAMBA_EXE")
    yield shutil.which("micromamba")
    yield shutil.which("mamba")
    yield shutil.which("conda")


def install_conda(slivka_path: Path, service_path: Path, conda_exe: str):
    service_full_name = service_path.name
    env_file_path = service_path / "environment.yaml"
    env_path = slivka_path.joinpath("conda_env", service_full_name).resolve()
    proc = subprocess.run(
        [
            conda_exe, "env", "create",
            "--prefix", env_path,
            "--file", env_file_path,
            "--yes"
        ]
    )
    proc.check_returncode()
    return env_path


def install_service(slivka_path: Path, service_path: Path, prepend_command=[]):
    service_full_name = service_path.name
    service_template_path = next(service_path.glob("*.service.yaml"))

    data_dirs = filter(Path.is_dir, service_path.iterdir())
    for data_dir in data_dirs:
        shutil.copytree(data_dir, slivka_path / data_dir.name / service_full_name)

    yaml = TemplateYamlLoader({
        "data": f"${{SLIVKA_HOME}}/data/{service_full_name}",
        "testdata": f"${{SLIVKA_HOME}}/testdata/{service_full_name}"
    })
    service_config = yaml.load(service_template_path)
    service_config["command"] = [*prepend_command, *service_config["command"]]
    services_dir = slivka_path / "services"
    services_dir.mkdir(exist_ok=True)
    dest_file = services_dir / f"{service_full_name}.service.yaml"
    yaml.dump(service_config, dest_file)
    return dest_file


if __name__ == '__main__':
    main()
