"""Create python project stub."""
import argparse
import logging
import os
import pathlib
import shutil
import string
import subprocess
import sys


def copy_path(source: pathlib.Path, destination: pathlib.Path) -> None:
    """
    Simple helper to copy <source> to <destination> allowing
    use one method for both of files and directories.
    """
    if source.is_file():
        shutil.copy(source, destination)
    else:
        shutil.copytree(source, destination, dirs_exist_ok=True)


def setup_git(project_path: pathlib.Path, logger: logging.Logger) -> None:
    logger.info("Setup git repo for the project...")
    try:
        repo_path = project_path.as_posix()
        make_call = subprocess.check_call
        make_call(["git", "config", "--global", "--add", "safe.directory", str(repo_path)])
        make_call(["git", "init", str(repo_path)])
        make_call(["git", "-C", str(repo_path), "branch", "-M", "main"])
        make_call(["git", "-C", str(repo_path), "add", "--all"])
        make_call(["git", "-C", str(repo_path), "commit", "-m", "Initial commit"])
    except subprocess.CalledProcessError as ex:
        logger.error(f"Failed to setup git: {ex}")


def activate_pipenv(project_path: pathlib.Path, logger: logging.Logger) -> None:
    if not shutil.which("pipenv"):
        logger.warning("Pipenv is missing. Trying to install")
        try:
            subprocess.check_call(["pip", "install", "pipenv"])
        except subprocess.CalledProcessError:
            logger.error("Couldn't install pipenv, so this action will be skipped.")
            logger.info(
                "You can try to install it manually 'pip(3) install pipenv'"
                "and then activate from project directory via 'pipenv install --dev'"
            )

    if shutil.which("pipenv"):
        logger.info("Activating pipenv...")
        subprocess.check_call(["pipenv", "install", "--dev"], cwd=project_path)


def set_precommit_hooks(project_path: pathlib.Path, logger: logging.Logger) -> None:
    git_folder = project_path / ".git"
    if not git_folder.exists():
        logger.warning(f"No git repo at {project_path}")
        return

    subprocess.check_call(["pipenv", "run", "pre-commit", "install"], cwd=project_path)


def setup_logging() -> logging.Logger:
    """Configure built-in logging subsystem."""
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)
    return logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
    """Configure parser and parse command-line arguments."""
    args_parser = argparse.ArgumentParser(description="Create stub for Python project.")

    args_parser.add_argument(
        "project_path",
        type=pathlib.Path,
        help="New project location. The last child name will be picked as the project name",
    )

    return args_parser.parse_args()


def create_project_stub(project_path: pathlib.Path, logger: logging.Logger) -> None:
    """Create project stub at <project_path> location."""
    try:
        project_path.mkdir(parents=True, exist_ok=False)
    except FileExistsError:
        dir_items = list(project_path.iterdir())
        if any(dir_items):
            raise  # directory contains something so we can't go further

    source_root = pathlib.Path(__file__).parent

    logger.info("Copying stubs into project directory...")
    copy_path(source_root / "template", project_path)
    copy_path(source_root / ".gitignore", project_path)
    copy_path(source_root / ".pre-commit-config.yaml", project_path)


def process_template(template_path: pathlib.Path, **keywords: str) -> None:
    """Read template file, substitute keywords and save updated file."""
    with open(template_path, "r+", encoding="utf-8") as file:
        template = string.Template(file.read())
        content = template.safe_substitute(**keywords)

        file.seek(0)
        file.truncate()

        file.write(content)


def tweak_project_stub(project_path: pathlib.Path, logger: logging.Logger) -> None:
    """Tweak project stub: do some renaming and substitutions."""
    logger.info(f"Tweaking stubs ({project_path}) files...")

    package_name = project_path / "project_name"
    package_name.rename(project_path / project_path.name)

    template_files = (project_path / "setup.py", project_path / "setup.cfg", project_path / "Pipfile")
    for template in template_files:
        process_template(
            template,
            project_name=project_path.name,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}",
            author=os.getlogin(),
        )


def finalize_project(project_path: pathlib.Path, logger: logging.Logger) -> None:
    """Apply post-setup actions if any."""
    logger.info("Finalization...")

    setup_git(project_path, logger)
    activate_pipenv(project_path, logger)
    set_precommit_hooks(project_path, logger)


def main() -> None:
    """Application entry point."""
    logger = setup_logging()

    args = parse_arguments()
    project_path = args.project_path.resolve()
    try:
        create_project_stub(project_path, logger)
        tweak_project_stub(project_path, logger)
        finalize_project(project_path, logger)
    except FileExistsError:
        logger.error("Project directory already exists.")
    except FileNotFoundError:
        logger.error("Some required files or folders are missed.")
        logger.info("Please verify that template is synced with remote.")


if __name__ == "__main__":
    main()
