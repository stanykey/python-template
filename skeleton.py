"""Create python project stub."""
import argparse
import enum
import logging
import pathlib
import shutil
import string
import subprocess


def copy_path(source: pathlib.Path, destination: pathlib.Path) -> None:
    if source.is_file():
        shutil.copy(source, destination)
    else:
        shutil.copytree(source, destination)


class PostActions(enum.Enum):
    nothing = 1 << 0
    git = 1 << 1
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
    items_to_copy = (
        source_root / "project_name",
        source_root / "Pipfile",
        source_root / "setup.py",
        source_root / "pyproject.toml",
        source_root / "setup.cfg",
        source_root / ".gitignore",
    )

    for source in items_to_copy:
        destination = project_path / source.name
        logger.info(f"\t - copying {source.name} to {destination.relative_to(project_path.parent)}...")
        copy_path(source, destination)

    logger.info("Creating placeholders...")
    items_to_create = {
        "README.md": (
            "# TODO: Fill in this README\n",
            "\n",
            "This project is distributed under some license. See LICENSE for details.\n",
        ),
        "LICENSE": tuple(),
    }

    for name, content in items_to_create.items():
        logger.info(f"\t - creating {name}...")
        destination = project_path / name
        destination.touch()

        destination.write_text("".join(content))


def process_template(template_path: pathlib.Path, **keywords: str) -> None:
    with open(template_path, "r+", encoding="utf-8") as file:
        template = string.Template(file.read())
        content = template.substitute(**keywords)

        file.seek(0)
        file.truncate()

        file.write(content)


def tweak_project_stub(project_path: pathlib.Path, logger: logging.Logger) -> None:
    logger.info(f"Tweaking stubs ({project_path}) files...")

    package_name = project_path / "project_name"
    package_name.rename(project_path / project_path.name)

    template_files = (project_path / "setup.py", project_path / "setup.cfg")
    for template in template_files:
        process_template(template, project_name=project_path.name)


def finalize_project(project_path: pathlib.Path, actions: list[PostActions], logger: logging.Logger) -> None:
    logger.info("Finalization...")

    if PostActions.git in actions:
        logger.info("Initializing git...")
        subprocess.check_call(["git", "init"], cwd=project_path)

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
