import json
import logging
import sys
from datetime import datetime


class ConfigHelper:

    def __init__(self, config_path="config.json", input_prompt="> ", skip_confirmation_prompts=False):
        self.config_path = config_path
        self.input_prompt = input_prompt
        self.skip_confirmation_prompts = skip_confirmation_prompts
        self.config = {}

        self.config = self.load_config()
        if not self.config:
            self.create_config()

    def get(self, key):
        if key in self.config:
            return self.config[key]
        return None

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def contains(self, key):
        return key in self.config

    def load_config(self):
        # Load self.config file
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"# Reading configuration... {datetime_str}")
        logging.info(f"  - Config Path: {self.config_path}")

        config = {}
        try:
            with open(self.config_path) as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            logging.warning("Config file not found. Creating self.config file...")

        return config

    def create_config(self):
        if 'canvas_api_heading' not in self.config:
            self.config['canvas_api_heading'] = "https://canvas.instructure.com"

        if 'todoist_api_key' not in self.config or len(self.config['todoist_api_key']) == 0:
            logging.info("Your Todoist API key has not been configured!\n"
                         "To add an API token, go to your Todoist settings and "
                         "copy the API token listed under the Integrations Tab.\n"
                         "Copy the token and paste below when you are done.")
            if self.skip_confirmation_prompts:
                logging.error(
                    "You must configure your Todoist API key. Please run without -y argument to configure.")
                sys.exit(1)
            self.config['todoist_api_key'] = input(self.input_prompt)
        if 'canvas_api_key' not in self.config or len(self.config['canvas_api_key']) == 0:
            logging.info("Your Canvas API key has not been configured!\n"
                         "To add an API token, go to your Canvas settings and"
                         "click on New Access Token under Approved Integrations.\n"
                         "Copy the token and paste below when you are done.")
            if self.skip_confirmation_prompts:
                logging.error(
                    "You must configure your Canvas API key. Please run without -y argument to configure.")
                sys.exit(1)
            self.config['canvas_api_key'] = input(self.input_prompt)

        self.save_config()

    def save_config(self):
        """
        Saves the configuration file to disk.
        """
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
