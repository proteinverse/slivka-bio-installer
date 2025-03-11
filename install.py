import os
import re
import shutil
import subprocess
from pathlib import Path

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
        return re.sub(r'\{\{ ?(\w+:[\w\/\.]+) ?\}\}', self._match_repl, value)


@click.command()
@click.option("--conda-exe")
@click.option("--service", "-s", "services", multiple=True, default=[''], show_default="all services")
@click.argument("path", type=Path)
def main(conda_exe, services, path: Path):
    try:
        conda_installer = CondaInstaller.create(conda_exe, path / "conda_env")
    except Exception as e:
        conda_installer = None
        click.echo(f"Failed to init conda installer: {e}")
    else:
        click.echo(f"Conda available: '{conda_installer.conda_exe}'")

    try:
        docker_installer = DockerInstaller.create()
    except Exception as e:
        docker_installer = None
        click.echo(f"Failed to init docker installer: {e}")
    else:
        click.echo(f"Docker available")

    service_paths_to_install = [
        service_dir.resolve()
        for service_dir in Path.cwd().joinpath("install").iterdir()
        for name in services
        if service_dir.stem.startswith(name) and next(service_dir.glob("*.service.yaml"), False)
    ]
    click.echo("Installing:")
    for service_path in sorted(service_paths_to_install):
        yaml_file = next(service_path.glob("*.service.yaml"))
        yaml_data = yaml.load(yaml_file)
        click.echo(f" - {yaml_data['name']}:{yaml_data['version']}")
    click.confirm("Confirm", default=True, abort=True)

    install_slivka(path)
    install_shared(path)

    installers = [
        obj for obj in (conda_installer, docker_installer) if obj is not None
    ]

    for service_path in service_paths_to_install:
        click.echo(f"Installing: {service_path.name}")
        applicable_installers = [
            obj for obj in installers
            if obj.is_applicable_to(service_path)
        ]
        retry = True
        while retry:
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
            if ans == "c": installer = conda_installer
            if ans == "d": installer = docker_installer
            try:
                rep = installer.install(service_path)
                command_prefix = installer.get_command_prefix(rep)
                retry = False
            except Exception as e:
                click.echo(f"{type(e).__name__}: {e}")
                ans = click.prompt(
                    "[R]etry, [S]kip, [A]bort, [I]gnore",
                    type=click.Choice("rsai", case_sensitive=False),
                    show_choices=False
                )
                if ans == 's':
                    click.echo(click.style("Skipping", fg="yellow")+ f": {service_path.name}")
                    break
                elif ans == 'a':
                    raise click.Abort
                elif ans == 'i':
                    retry = False
        else:
            output_file = install_service(path, service_path, command_prefix)
            click.echo(f"{click.style('Installed', fg='bright_green')}: {output_file.name}")


class CondaInstaller:
    def __init__(self, conda_exe, conda_env_root):
        self.conda_exe = conda_exe
        self.conda_env_root = conda_env_root

    @classmethod
    def create(cls, conda_exe=None, conda_env_root=None):
        if not conda_exe:
            try:
                conda_exe = next(filter(None, _iter_conda_exe()))
            except StopIteration:
                raise Exception("No conda executable found.")
        if not conda_env_root:
            raise ValueError(f"Invalid conda env root: {conda_env_root}")
        return CondaInstaller(conda_exe, conda_env_root)

    def is_applicable_to(self, template_path: Path):
        return (template_path / "environment.yaml").is_file()

    def install(self, template_path: Path):
        try:
            return create_conda_env(
                conda_env_root=self.conda_env_root,
                service_path=template_path,
                conda_exe=self.conda_exe
            )
        except subprocess.CalledProcessError:
            click.echo(f"Failed to install conda env for {template_path.name}")
            raise

    def get_command_prefix(self, conda_env):
        return [self.conda_exe, "run", "-p", str(conda_env)]


def _iter_conda_exe():
    yield os.environ.get("CONDA_EXE")
    yield os.environ.get("MAMBA_EXE")
    yield shutil.which("micromamba")
    yield shutil.which("mamba")
    yield shutil.which("conda")


def create_conda_env(conda_env_root: Path, service_path: Path, conda_exe: str):
    service_full_name = service_path.name
    env_file_path = service_path / "environment.yaml"
    env_path = (conda_env_root / service_full_name).resolve()
    if env_path.exists():
        click.echo(f"Conda env already exists: {env_path}. Skipping.")
        return env_path
    proc = subprocess.run(
        [
            conda_exe, "env", "create",
            "--prefix", env_path,
            "--file", env_file_path,
            "--yes", "--quiet"
        ]
    )
    proc.check_returncode()
    return env_path


class DockerInstaller:
    @classmethod
    def create(cls):
        docker_exe = shutil.which("docker")
        if not docker_exe:
            raise Exception("Docker not found.")
        return DockerInstaller()

    def is_applicable_to(self, template_path: Path):
        return (
            (template_path / "docker.yaml").is_file() or
            (template_path / "Dockerfile").is_file()
        )

    def install(self, template_path: Path):
        image_data = yaml.load(template_path / "docker.yaml")
        if (template_path / "Dockerfile").is_file():
            return build_docker_image(
                template_path / "Dockerfile",
                image_name=image_data["image"],
                image_tag=image_data["tag"]
            )
        else:
            return pull_docker_image(
                image=image_data["image"],
                tag=image_data["tag"],
                platform=image_data["platform"]
            )

    def get_command_prefix(self, image_tag):
        wrapper_script = os.path.join("${SLIVKA_HOME}", "scripts", "run_with_docker.sh")
        return ["/usr/bin/env", "bash", wrapper_script, image_tag]


def build_docker_image(dockerfile: Path, image_name, image_tag):
    full_tag = f"{image_name}:{image_tag}"
    proc = subprocess.run(
        [
            "docker", "buildx", "build",
            "--tag", full_tag,
            "--file", dockerfile,
            dockerfile.parent
        ],
        cwd=dockerfile.parent
    )
    proc.check_returncode()
    return full_tag



def pull_docker_image(image, tag, platform):
    image_id = f"{image}:{tag}"
    proc = subprocess.run(
        [
            "docker", "image", "pull",
            "--platform", platform,
            "--quiet",
            image_id
        ]
    )
    proc.check_returncode()
    return image_id 


def install_slivka(slivka_path: Path):
    subprocess.run(["slivka", "init", slivka_path])


def install_shared(slivka_path: Path):
    shared_dir = Path.cwd() / "shared"
    for root, dirs, files in os.walk(shared_dir):
        root = Path(root)
        rel_root: Path = root.relative_to(shared_dir)
        for dirname in dirs:
            (slivka_path / rel_root / dirname).mkdir(exist_ok=True)
        for filename in files:
            target_file = slivka_path / rel_root / filename
            if not target_file.exists():
                shutil.copy2(root / filename, target_file)
            else:
                click.echo(f"File exists: {target_file}")


def install_service(slivka_path: Path, service_path: Path, prepend_command=[]):
    service_full_name = service_path.name
    service_template_path = next(service_path.glob("*.service.yaml"))

    data_dirs = filter(Path.is_dir, service_path.iterdir())
    template_dict = {}
    for data_dir in data_dirs:
        target_dir = slivka_path / data_dir.name / service_full_name
        if not target_dir.exists():
            click.echo(f"Directory exists: {target_dir}. Skipping.")
            shutil.copytree(data_dir, target_dir)
        template_dict[f"dir:{data_dir.name}"] = os.path.join("${SLIVKA_HOME}", data_dir.name, service_full_name)

    yaml = TemplateYamlLoader(template_dict)
    service_config = yaml.load(service_template_path)
    service_config["command"] = [*prepend_command, *service_config["command"]]
    services_dir = slivka_path / "services"
    services_dir.mkdir(exist_ok=True)
    dest_file = services_dir / f"{service_full_name}.service.yaml"
    yaml.dump(service_config, dest_file)
    return dest_file


if __name__ == '__main__':
    main()
