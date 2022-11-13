import argparse
import logging
import os
import re

import appdirs
from termcolor import colored


def setup():
    appname = "CanvasSync"
    appauthor = "Andrei Cozma"
    os_save_path = appdirs.user_data_dir(appname, appauthor)
    os.makedirs(os_save_path, exist_ok=True)
    os_config_path = appdirs.user_config_dir(appname, appauthor)
    os.makedirs(os_config_path, exist_ok=True)
    config_path = os.path.join(os_config_path, "config.json")
    os_log_path = appdirs.user_log_dir(appname, appauthor)
    os.makedirs(os_log_path, exist_ok=True)
    log_path = os.path.join(os_log_path, "canvas-sync.log")
    return os_save_path, config_path, log_path


def parse_args():
    # Parse arguments and extract boolean flag -y which defaults to false
    parser = argparse.ArgumentParser(description='Transfer Canvas assignments to Todoist')
    parser.add_argument('-t', '--todoist', action='store_true', help='Run CanvasToTodoist')
    parser.add_argument('-f', '--files', action='store_true', help='Run CanvasFileDownloader')
    parser.add_argument('-a', '--all', action='store_true', help='Run both CanvasToTodoist and CanvasFileDownloader')
    parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation prompts')
    parser.add_argument('--reset', action='store_true', help='Reset config file')
    if not any([arg in ["-t", "-f", "-a"] for arg in os.sys.argv]):
        # print help if no arguments are provided
        parser.print_help()
        parser.error("Must have either -t or -f")
    return parser.parse_args()


def normalize_file_name(file_name, has_extension=True):
    rexp1 = r"%[0-9a-fA-F][0-9a-fA-F]"
    rexp2 = r"[\s+_\-:\\\/]+"
    # Replace any occurance of %XX with a -
    file_name = re.sub(rexp1, "-", file_name)
    if has_extension:
        # Replace +, _, -, and spaces with -
        fnsplit = file_name.split(".")
        name, ext = fnsplit[0:-1], fnsplit[-1]
        name = "-".join(name)
        name = re.sub(rexp2, "-", name)
        name = name.strip("-")
        file_name = f"{name}.{ext}"
    else:
        # Replace +, _, -, and spaces with -
        file_name = re.sub(rexp2, "-", file_name)
        file_name = file_name.strip("-")
    return file_name


def p_error(*args, **kwargs):
    logging.error(colored(*args, color="red", **kwargs))


def p_success(*args, **kwargs):
    logging.info(colored(*args, color="green", **kwargs))


def p_warn(*args, **kwargs):
    logging.warning(colored(*args, color="yellow", attrs=["bold", "reverse"], **kwargs))


def p_info(*args, **kwargs):
    logging.info(colored(*args, color="yellow", **kwargs))
