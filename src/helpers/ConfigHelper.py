import json
import logging
import os
import sys
from datetime import datetime

from src.Utils import p_error, p_info, p_warn


class ConfigHelper:

    def __init__(self, args, config_path="config.json", input_prompt="> ", skip_confirmation_prompts=False):
        self.args = args
        self.config_path = config_path
        self.input_prompt = input_prompt
        self.skip_confirmation_prompts = skip_confirmation_prompts
        self.config = {}
        p_info("# ConfigHelper: Initialized")

        if self.args.reset:
            self.remove_config()

        self.config = self.load_config()
        # if not self.config:
        self.create_config()

    def get(self, key):
        return self.config[key] if key in self.config else None

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def contains(self, key):
        return key in self.config

    def load_config(self):
        logging.info("  - Loading configuration file...")
        # Load self.config file
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        logging.info(f"  - Reading configuration... {datetime_str}")
        logging.info(f"  -  Config Path: {self.config_path}")

        config = {}
        try:
            with open(self.config_path) as config_file:
                config = json.load(config_file)
        except FileNotFoundError:
            p_warn(f"Config file not found. Creating: {self.config_path}...")

        return config

    def create_config(self):
        logging.info("  - Creating configuration file...")
        if 'canvas_api_heading' not in self.config or len(self.config['canvas_api_heading']) == 0:
            self.config['canvas_api_heading'] = "https://canvas.instructure.com"
            # Ask the user if they want to change the default heading, or use the default one
            p_info("Default Canvas API URL: https://canvas.instructure.com.\n"
                   "Would you like to use this? (Y/n) ")
            if not self.skip_confirmation_prompts:
                use_default_heading = input(self.input_prompt)
            else:
                p_info("Using default Canvas API URL: https://canvas.instructure.com")
                use_default_heading = "y"
            if use_default_heading.lower() not in ["y", "yes", "n", "no"]:
                p_error("Invalid input. Please enter 'y' or 'n'.")
                sys.exit(1)
            if use_default_heading.lower() != "y":
                p_info("Please enter your desired Canvas API URL: ")
                self.config['canvas_api_heading'] = input(self.input_prompt)
                # if the user enters an empty string, or a string that is not a valid URL, output an error and exit
                if len(self.config['canvas_api_heading'].strip()) == 0:
                    p_error("Error: Canvas API Heading cannot be empty.")
                    sys.exit(1)
                if not self.config['canvas_api_heading'].startswith("https"):
                    p_error("Error: Canvas API Heading must start with 'https'. Exiting...")
                    sys.exit(1)

        if 'canvas_api_key' not in self.config or len(self.config['canvas_api_key']) == 0:
            p_info("Your Canvas API key has not been configured!\n"
                   "To add an API token, go to your Canvas settings and "
                   "click on New Access Token under Approved Integrations.\n"
                   "Copy the token and paste below when you are done.")
            if self.skip_confirmation_prompts:
                p_error("You must configure your Canvas API key. Please run without -y argument to configure.")
                sys.exit(1)
            self.config['canvas_api_key'] = input(self.input_prompt)
            if len(self.config['canvas_api_key'].strip()) == 0:
                p_error("Error: Canvas API Key cannot be empty. Exiting...")
                sys.exit(1)

        if self.args.todoist or self.args.all:
            if 'todoist_api_key' not in self.config or len(self.config['todoist_api_key']) == 0:
                p_info("Your Todoist API key has not been configured!\n"
                       "To add an API token, go to your Todoist settings and "
                       "copy the API token listed under the Integrations Tab.\n"
                       "Copy the token and paste below when you are done.")
                if self.skip_confirmation_prompts:
                    p_error("You must configure your Todoist API key. Please run without -y argument to configure.")
                    sys.exit(1)
                self.config['todoist_api_key'] = input(self.input_prompt)
                if len(self.config['todoist_api_key'].strip()) == 0:
                    p_error("Error: Todoist API Key cannot be empty. Exiting...")
                    sys.exit(1)

        self.save_config()

    def save_config(self):
        """
        Saves the configuration file to disk.
        """
        logging.info("  - Saving configuration file...")
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def remove_config(self):
        """
        Removes the configuration file from disk.
        """
        logging.info("  - Removing configuration file...")
        os.remove(self.config_path)
