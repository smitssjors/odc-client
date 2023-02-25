"""A small CLI tool to help with working with the ODC Server."""

__version__ = "0.1.0"

import json
import shutil
import subprocess
from pathlib import Path
from typing import Final
from zipfile import ZipFile

import fabric
import typer

CONFIG_FILE_NAME: Final[str] = "odc.json"
USERNAME: Final[str] = "username"
PASSWORD: Final[str] = "password"
HOSTNAME: Final[str] = "hostname"
PORT: Final[str] = "port"

app = typer.Typer()


def get_config() -> dict:
    try:
        with open(Path(CONFIG_FILE_NAME), "r") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Could not find config file. Don't forget to run `init`")
        raise typer.Exit(code=1)

    if config.get(USERNAME) is None:
        print("Could not find a username. Don't forget to run `init`")
        raise typer.Exit(code=1)

    if config.get(PASSWORD) is None:
        print("Could not find a password. Don't forget to run `init`")
        raise typer.Exit(code=1)

    if config.get(HOSTNAME) is None:
        print("Could not find a hostname. Don't forget to run `init`")
        raise typer.Exit(code=1)

    if config.get(PORT) is None:
        print("Could not find a port. Don't forget to run `init`")
        raise typer.Exit(code=1)

    return config


def get_connection() -> fabric.Connection:
    config = get_config()
    return fabric.Connection(
        host=config[HOSTNAME],
        port=config[PORT],
        user=config[USERNAME],
        connect_kwargs={"password": config[PASSWORD]},
    )


@app.command()
def init(
    username: str = typer.Option(
        ...,
        prompt=True,
        help="The username to log into the SFTP server. You should receive this via email.",
    ),
    password: str = typer.Option(
        ...,
        prompt=True,
        help="The password to log into the SFTP server. You should receive this via email.",
    ),
    hostname: str = typer.Option(
        "odc-09.win.tue.nl", help="The hostname of the SFTP server."
    ),
    port: int = typer.Option(222, help="The port of the SFTP server."),
    update_gitignore: bool = typer.Option(
        True,
        " /--skip-update-gitignore",
        help="Append the config file to the .gitignore.",
    ),
    force: bool = typer.Option(
        False, "--force", "-f", help="Overwrite the config if it already exists."
    ),
):
    """
    Creates an odc.json file with the configuration needed to connect to the
    SFTP server. This prevents the need to always pass the connection arguments to each
    command. As this file contains secrets, it is also added to the .gitignore if there
    is one present.
    """
    config_file_path = Path(CONFIG_FILE_NAME)

    if not force and config_file_path.is_file():
        raise typer.BadParameter(
            f"File {config_file_path} already exists. Use the --force option to overwrite it.",
            param_hint="location",
        )

    config = {USERNAME: username, PASSWORD: password, HOSTNAME: hostname, PORT: port}

    with open(config_file_path, "w") as f:
        json.dump(config, f, indent=2)

    if update_gitignore:
        gitignore_path = Path(".gitignore")

        if not gitignore_path.is_file():
            print("No .gitignore found.")
            raise typer.Exit()
        with open(gitignore_path, "a") as f:
            f.write(f"\n# ODC Client\n{CONFIG_FILE_NAME}\n")


@app.command()
def submit(
    remote_dir: Path = typer.Option(
        Path(),
        help="The remote directory to upload the program to. The directory is prefixed with '/home' so 'mydir' will "
        "give `/home/mydir`.",
    ),
    skip_build: bool = typer.Option(
        False, "--skip-build", help="Skip building the jar."
    ),
    build_command: str = typer.Option(
        "mvn clean package", help="The command to build the jar."
    ),
    jar_path: Path = typer.Option(
        Path("target/app.jar"), help="The location of the compiled jar."
    ),
    python_dir: Path = typer.Option(
        Path("app"), help="The directory in which the main.py lives."
    ),
):
    """
    Submit the project to the SFTP server. It automatically determines if it is a Java
    or Python project by checking whether there is a pom.xml file. For Python projects
    both using a single main.py file and having several files in an app directory is
    supported.
    """
    if Path("pom.xml").is_file():
        if not skip_build:
            build_command = build_command.strip()
            print(f"Running `{build_command}`...")
            result = subprocess.run(build_command.split(" "))

            if result.returncode != 0:
                print("Failed to build package")
                raise typer.Exit(code=2)

        submission = jar_path
    else:
        if python_dir.is_dir():
            print(f"Zipping {python_dir} directory...")
            shutil.make_archive("app", "zip", python_dir)
        elif Path("main.py").is_file():
            print("Zipping main.py...")
            with ZipFile("app.zip", "w") as app_zip:
                app_zip.write("main.py")
        else:
            print("Can't figure out what kind of project this is")
            raise typer.Abort()

        submission = "app.zip"

    remote_path = Path("/home/") / remote_dir

    with get_connection() as c:
        print("Connecting to server...")
        c.open()
        print(f"Uploading {submission}...")
        c.put(submission, remote=str(remote_path))

    print("Done!")


def main():
    app()
