"""Create python project stub."""
import argparse
import enum
import logging
import os
import pathlib
import shutil
import string
import subprocess
import sys


def copy_path(source: pathlib.Path, destination: pathlib.Path) -> None:
    if source.is_file():
        shutil.copy(source, destination)
    else:
        shutil.copytree(source, destination, dirs_exist_ok=True)


class PostActions(enum.Enum):
    nothing = 1 << 0
    pipenv = 1 << 2

    def __str__(self) -> str:
        return self.name

    @classmethod
    def from_string(cls, str_repr: str) -> "PostActions":
        try:
            return cls[str_repr]
        except KeyError:
            raise ValueError()


def setup_logging() -> logging.Logger:
    logging.basicConfig(format="%(levelname)s: %(message)s", level=logging.DEBUG)
    return logging.getLogger(__name__)


def parse_arguments() -> argparse.Namespace:
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
    with open(template_path, "r+", encoding="utf-8") as file:
        template = string.Template(file.read())
        content = template.safe_substitute(**keywords)

        file.seek(0)
        file.truncate()

        file.write(content)


def tweak_project_stub(project_path: pathlib.Path, logger: logging.Logger) -> None:
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
    logger.info("Finalization...")

    if PostActions.pipenv in actions:
        logger.info("Activating pipenv...")
        subprocess.check_call(["pipenv", "install", "--dev"], cwd=project_path)


def main() -> None:
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
