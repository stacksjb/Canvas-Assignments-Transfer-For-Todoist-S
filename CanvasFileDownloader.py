import logging
import os
import sys

from src.CanvasHelper import CanvasHelper
from src.ConfigHelper import ConfigHelper


class CanvasFileDownloader:
    def __init__(self, config_path, default_save_path, skip_confirmation_prompts=False):
        self.default_save_path = default_save_path
        self.input_prompt = "> "
        self.skip_confirmation_prompts = skip_confirmation_prompts
        self.param = {'per_page': '100', 'include': 'submission'}

        self.config_helper = ConfigHelper(config_path, self.input_prompt, skip_confirmation_prompts)
        heading = str(self.config_helper.get('canvas_api_heading'))
        self.canvas_helper = CanvasHelper(self.config_helper.get('canvas_api_key'), canvas_api_heading=heading)
        self.selected_course_ids = self.canvas_helper.select_courses(self.config_helper,
                                                                     skip_confirmation_prompts=skip_confirmation_prompts)

    def run(self):
        logging.info("###################################################")
        logging.info("#               Canvas-File-Downloader            #")
        logging.info("###################################################")

        if not self.skip_confirmation_prompts:
            use_previous_input = input("Q: Would you like to download all files for these courses? (Y/n) ")
        else:
            use_previous_input = "y"

        if use_previous_input.lower() == "y":
            self.load_save_paths()
            self.canvas_helper.download_course_files_all(self.selected_course_ids, self.param)
            self.canvas_helper.download_module_files_all(self.selected_course_ids, self.param)

    def load_save_paths(self):
        has_missing = False

        for i, (c_id, c_obj) in enumerate(self.selected_course_ids.items()):
            if 'save_path' not in c_obj or c_obj['save_path'] == "" or c_obj['save_path'] is None:
                has_missing = True
                break

        if not has_missing:
            logging.info("# You have previously selected download paths:")
            for i, (c_id, c_obj) in enumerate(self.selected_course_ids.items()):
                logging.info(f"  {i + 1}. {c_obj['name']}: `{c_obj['save_path']}`")
            if not self.skip_confirmation_prompts:
                use_previous_input = input("Q: Would you like to use the download paths selected last time? (Y/n) ")
            else:
                use_previous_input = "y"
            logging.info("")
            if use_previous_input.lower() == "y":
                return

        for course_id, c_obj in self.selected_course_ids.items():
            c_name = c_obj['name']
            logging.info(f"# Course: {c_name}")

            def_save_path = os.path.join(self.default_save_path, c_name)
            logging.info(f"  - Default: {def_save_path}")
            if self.skip_confirmation_prompts:
                logging.error("You must configure save paths."
                              "Please run without -y argument to configure.")
                sys.exit(1)
            save_path = input(f"  - Enter new path, or press return to use default: ")
            if save_path.strip() == "":
                save_path = def_save_path
            self.selected_course_ids[course_id]['save_path'] = save_path

        logging.info("")

        self.config_helper.set('courses', self.selected_course_ids)
