#!/usr/bin/env python3

# System libraries
import yaml
import logging
import argparse
from os import path, makedirs
from systemd.journal import JournalHandler

# Our libraries
import warwickd

# Parse arguments and launch daemon
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="warwickd, python mqtt daemon")
    parser.add_argument("-l", "--log-level", default="info")
    parser.add_argument("-c", "--config-file", default="./config.yaml")
    arguments = parser.parse_args()

    logger = logging.getLogger("warwickd")
    logger.addHandler(JournalHandler(SYSLOG_IDENTIFIER="warwickd"))
    if arguments.log_level.lower() == "critical":
        logger.setLevel(logging.CRITICAL)
    elif arguments.log_level.lower() == "error":
        logger.setLevel(logging.ERROR)
    elif arguments.log_level.lower() == "warning":
        logger.setLevel(logging.WARNING)
    elif arguments.log_level.lower() == "info":
        logger.setLevel(logging.INFO)
    elif arguments.log_level.lower() == "debug":
        logger.setLevel(logging.DEBUG)

    logger.info("Starting warwickd...")

    # Create the working directory if needed
    if not path.exists("/var/lib/warwickd"):
        logger.info('Creating working dir "/var/lib/warwickd"')
        makedirs("/var/lib/warwickd")

    # Load confg
    # TODO handler to check and create defaults if undefined
    with open(arguments.config_file, "r") as stream:
        config = yaml.safe_load(stream)

    # Start this show
    warwickd.daemon(config)
