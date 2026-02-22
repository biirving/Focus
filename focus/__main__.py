"""Entry point for Focus OS: python -m focus"""

import argparse
import sys

from dotenv import load_dotenv

load_dotenv()

from focus.config import load_config
from focus.daemon import FocusDaemon


def main():
    parser = argparse.ArgumentParser(description="Focus OS - ambient focus monitor")
    parser.add_argument("--config", default="config.yaml", help="Path to config file")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    config = load_config(args.config)
    if args.verbose:
        config.verbose = True

    daemon = FocusDaemon(config)
    try:
        daemon.run()
    except KeyboardInterrupt:
        print("\nShutting down Focus OS...")
        daemon.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()
