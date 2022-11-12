"""
Modifications by Andrei Cozma which are based on the original code from the following repository:
- https://github.com/scottquach/Canvas-Assignments-Transfer-For-Todoist

What's new:
 - Use the 'canvasapi' library instead of requests for shorter/cleaner code
 - Use the 'pick' library for better multiple-item selection
 - Added ability to rename a course as it appears as a Todoist project (can optionally use the default name from Canvas)
 - Automatically set task priority based on keywords (configurable)
 - Print short and detailed summaries after assignment transfer.
 - Shows counts of new assignments, updated assignments, and skipped assignments (already submitted or already up to date)
 - Optional file downloading capability
 - Reformatted print statements for better verbosity and readability.


Huge thanks to scottquach and stacksjb for their awesome work on this project.
"""

import argparse
import logging
import os

import appdirs

from CanvasFileDownloader import CanvasFileDownloader
from CanvasToTodoist import CanvasToTodoist

appname = "CanvasToTodoist"
appauthor = "GitHub Community"
os_save_path = appdirs.user_data_dir(appname, appauthor)
os.makedirs(os_save_path, exist_ok=True)
os_config_path = appdirs.user_config_dir(appname, appauthor)
os.makedirs(os_config_path, exist_ok=True)
os_log_path = appdirs.user_log_dir(appname, appauthor)
os.makedirs(os_log_path, exist_ok=True)

# Set up logging
log_fn = "canvas-to-todoist.log"
log_path = os.path.join(os_log_path, log_fn)
log_handlers = [logging.FileHandler(log_path, mode='w'),
                logging.StreamHandler()]
# handlers = [logging.FileHandler(f"{logfilename}.log", mode='w')]
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    # format="%(asctime)s %(levelname)6s : %(message)s [%(funcName)s():%(lineno)s]",
    handlers=log_handlers
)


def main():
    logging.info(f"Logs saved to: {log_path}")
    logging.info("")

    # Parse arguments and extract boolean flag -y which defaults to false
    parser = argparse.ArgumentParser(
        description='Transfer Canvas assignments to Todoist')
    parser.add_argument('-y', '--yes', action='store_true',
                        help='Skip confirmation prompts')
    # Get value of -y flag
    args = parser.parse_args()
    skip_confirmation_prompts = args.yes

    if skip_confirmation_prompts:
        logging.info("Skipping confirmation prompts")

    config_path = os.path.join(os_config_path, "config.json")

    # ct = CanvasToTodoist(config_path, skip_confirmation_prompts)
    # ct.run()

    cd = CanvasFileDownloader(config_path, os_save_path, skip_confirmation_prompts)
    cd.run()


if __name__ == "__main__":
    # Main Execution
    main()
