"""Create python project stub."""
import argparse
import enum
import functools
import logging
import os
import pathlib
import shutil
import string
import subprocess
import sys
import typing


def copy_path(source: pathlib.Path, destination: pathlib.Path) -> None:
    """
    Simple helper to copy <source> to <destination> allowing
    use one method for both of files and directories.
    """
    if source.is_file():
        shutil.copy(source, destination)
    else:
        shutil.copytree(source, destination, dirs_exist_ok=True)


@enum.unique
class PostActions(enum.Enum):
    """Enum of available post setup actions."""

    nothing = 1 << 0
    git = 1 << 1
    pipenv = 1 << 2

    def __str__(self) -> str:
        """Support pretty print and serialization into human-readable format."""
        return self.name

    @classmethod
    def from_string(cls, str_repr: str) -> "PostActions":
        """
        The factory method creates an instance from the string.
        Useful when reading human-readable configs.
        """
        try:
            return cls[str_repr]
        except KeyError:
            raise ValueError()


ActionHandler = typing.Callable[[pathlib.Path, logging.Logger], None]


def missed_handler(action: PostActions, _: pathlib.Path, logger: logging.Logger) -> None:
    logger.warning(f"No handler for '{action}' action")


def setup_git(project_path: pathlib.Path, logger: logging.Logger) -> None:
    logger.info("Setup git repo for the project...")
    try:
        repo_path = project_path.as_posix()
        make_call = subprocess.check_call
        make_call(["git", "config", "--global", "--add", "safe.directory", str(repo_path)])
        make_call(["git", "init", str(repo_path)])
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


def handle_post_action(action: PostActions, project: pathlib.Path, logger: logging.Logger) -> None:
    handlers: dict[PostActions, ActionHandler] = {PostActions.git: setup_git, PostActions.pipenv: activate_pipenv}

    handler = handlers.get(action, functools.partial(missed_handler, action))
    handler(project, logger)


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

    args_parser.add_argument(
        "--post-action",
        type=PostActions.from_string,
        default=PostActions.nothing,
        choices=list(PostActions)[1:],
        help="Post-setup options",
        dest="post_actions",
        nargs="+",
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


def finalize_project(project_path: pathlib.Path, actions: list[PostActions], logger: logging.Logger) -> None:
    """Apply post-setup actions if any."""
    logger.info("Finalization...")

    for action in actions:
        handle_post_action(action, project_path, logger)


def main() -> None:
    """Application entry point."""
    logger = setup_logging()

    args = parse_arguments()
    project_path = args.project_path.resolve()
    try:
        create_project_stub(project_path, logger)
        tweak_project_stub(project_path, logger)
        finalize_project(project_path, args.post_actions, logger)
    except FileExistsError:
        logger.error("Project directory already exists.")
    except FileNotFoundError:
        logger.error("Some required files or folders are missed.")
        logger.info("Please verify that template is synced with remote.")


if __name__ == "__main__":
    main()
