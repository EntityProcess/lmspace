"""Main CLI entry point for lmspace."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    """Main entry point for the lmspace CLI."""
    parser = argparse.ArgumentParser(
        prog="lmspace",
        description="Manage workspace agents across different backends",
    )
    
    subparsers = parser.add_subparsers(
        dest="command",
        help="Available commands",
        required=True,
    )
    
    # Add the 'code' subcommand for VS Code workspace agents
    code_parser = subparsers.add_parser(
        "code",
        help="Manage VS Code workspace agents",
    )
    code_subparsers = code_parser.add_subparsers(
        dest="action",
        help="VS Code agent actions",
        required=True,
    )
    
    # Add 'code provision' subcommand
    from .vscode.cli import add_provision_parser, add_launch_parser
    add_provision_parser(code_subparsers)
    add_launch_parser(code_subparsers)
    
    args = parser.parse_args(argv)
    
    # Route to the appropriate handler
    if args.command == "code":
        if args.action == "provision":
            from .vscode.cli import handle_provision
            return handle_provision(args)
        elif args.action == "launch":
            from .vscode.cli import handle_launch
            return handle_launch(args)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
