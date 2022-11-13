import argparse
import os

import appdirs


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
    parser.add_argument('-y', '--yes', action='store_true', help='Skip confirmation prompts')
    return parser.parse_args()
