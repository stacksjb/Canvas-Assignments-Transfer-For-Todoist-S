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
"""

import logging

from CanvasFileDownloader import CanvasFileDownloader
from CanvasToTodoist import CanvasToTodoist
from src.Utils import parse_args, setup

os_save_path, config_path, log_path = setup()

# Set up logging
log_handlers = [logging.FileHandler(log_path, mode='w'), logging.StreamHandler()]
logging.basicConfig(level=logging.INFO, format="%(message)s",
                    # format="%(asctime)s %(levelname)6s : %(message)s [%(funcName)s():%(lineno)s]",
                    handlers=log_handlers)


def main():
    logging.info(f"Logs saved to: {log_path}")
    logging.info("")

    args = parse_args()
    skip_confirmation_prompts = args.yes

    if skip_confirmation_prompts:
        logging.info("Skipping confirmation prompts")

    ct = CanvasToTodoist(config_path, skip_confirmation_prompts)
    ct.run()

    cd = CanvasFileDownloader(config_path, os_save_path, skip_confirmation_prompts)
    cd.run()


if __name__ == "__main__":
    # Main Execution
    main()
