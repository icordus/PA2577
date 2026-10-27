"""Allocate a unique integration run ID for subsequent CI steps."""

import os
import uuid


def main():
    """Append the run ID to the GitHub Actions environment file."""
    with open(os.environ["GITHUB_ENV"], "a") as output:
        output.write("INTEGRATION_RUN_ID=" + uuid.uuid4().hex + "\n")


if __name__ == "__main__":
    main()