import argparse
from importlib.metadata import version
from pathlib import Path

import tomllib


def main() -> None:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("installed")
    check = commands.add_parser("check")
    check.add_argument("expected_version_file", type=Path)
    args = parser.parse_args()

    if args.command == "installed":
        print(version("algobattle_base"))
        return

    checked_out_version = tomllib.loads(Path("pyproject.toml").read_text())["project"]["version"]
    build_version = args.expected_version_file.read_text().strip()
    if checked_out_version != build_version:
        raise SystemExit(
            f"algobattle-base version mismatch: checked out {checked_out_version}, "
            f"build uses {build_version}"
        )


if __name__ == "__main__":
    main()
