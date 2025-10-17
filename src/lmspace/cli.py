from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from .azure import AzureAssistantsService, AzureConfigurationError
from .config import ConfigError, load_configs
from .fetcher import ContentFetcher
from .runner import Runner

_LOG_LEVELS = {"debug": logging.DEBUG, "info": logging.INFO, "warning": logging.WARNING, "error": logging.ERROR}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Provision Azure OpenAI assistants from YAML configs")
    parser.add_argument("config", type=Path, help="Path to a YAML file or directory containing YAML configs")
    parser.add_argument("--github-token", dest="github_token", default=os.getenv("GITHUB_TOKEN"), help="GitHub token for private repositories")
    parser.add_argument("--vector-store-prefix", dest="vector_store_prefix", default=os.getenv("LMSPACE_VECTOR_PREFIX", "lmspace"), help="Prefix for Azure vector stores")
    parser.add_argument("--dry-run", action="store_true", help="Download files but skip Azure provisioning")
    parser.add_argument(
        "--log-level",
        choices=sorted(_LOG_LEVELS),
        default=os.getenv("LMSPACE_LOG_LEVEL", "info"),
        help="Logging verbosity",
    )
    return parser


def configure_logging(level: str) -> None:
    logging.basicConfig(level=_LOG_LEVELS.get(level.lower(), logging.INFO), format="%(asctime)s %(levelname)s %(name)s %(message)s")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    configure_logging(args.log_level)

    try:
        configs = load_configs(args.config)
    except ConfigError as exc:
        logging.error("%s", exc)
        return 2

    fetcher = ContentFetcher(github_token=args.github_token)
    try:
        if args.dry_run:
            azure_service = None
        else:
            try:
                azure_service = AzureAssistantsService.from_env(vector_store_prefix=args.vector_store_prefix)
            except AzureConfigurationError as exc:
                logging.error("%s", exc)
                return 2

        runner = Runner(fetcher=fetcher, azure_service=azure_service, dry_run=args.dry_run)
        results = runner.run_all(configs)
    finally:
        fetcher.close()

    for result in results:
        logging.info(
            "Config=%s files=%d assistant=%s vector_store=%s agent=%s",
            result.config_path,
            result.file_count,
            result.assistant_id or "-",
            result.vector_store_id or "-",
            result.framework_agent_id or "-",
        )

    return 0


__all__ = ["build_parser", "main"]
