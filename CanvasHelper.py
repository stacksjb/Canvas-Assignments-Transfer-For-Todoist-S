import json
import logging
import os
import re

import requests


class CanvasHelper:

    def __init__(self, api_key, canvas_api_heading="https://canvas.instructure.com"):
        self.canvas_api_heading = canvas_api_heading
        self.header = {"Authorization": f"Bearer {api_key.strip()}"}
        self.download_helper = CanvasDownloadHelper(api_key)

    def load_assignments(self, course_ids, param):
        """
        Iterates over the course_ids list and loads all the users assignments for those classes.
        Appends assignment objects to assignments list.
        """
        logging.info("# Loading assignments from Canvas")
        assignments = []
        for course_id in course_ids:
            response = requests.get(self.canvas_api_heading + '/api/v1/courses/' +
                                    str(course_id) + '/assignments', headers=self.header,
                                    params=param)
            if response.status_code == 401:
                logging.info('Unauthorized! Check Canvas API Key')
                exit()
            for assignment in response.json():
                assignments.append(assignment)

        return assignments

    def download_course_files_all(self, course_ids, param):
        logging.info("# Downloading Folders & Files")
        for course_id, c_obj in course_ids.items():
            c_name = c_obj['name']
            logging.info(f"# Course: {c_name}")
            save_path = c_obj['save_path']
            if not self.download_helper.download_course_files(course_id, save_path, param):
                continue

        logging.info("")

    def download_module_files_all(self, course_ids, param):
        logging.info("# Downloading Any Additional Files in Modules")
        for course_id, c_obj in course_ids.items():
            c_name = c_obj['name']
            logging.info(f"# Course: {c_name}")
            save_path = c_obj['save_path']
            if not self.download_helper.download_module_files(course_id, save_path, param):
                continue

        logging.info("")


class CanvasDownloadHelper():
    def __init__(self, api_key, canvas_api_heading="https://canvas.instructure.com"):
        self.canvas_api_heading = canvas_api_heading
        self.header = {"Authorization": f"Bearer {api_key.strip()}"}

    def download_course_files(self, course_id, save_path, param=None):
        if param is None:
            param = {}

        response = requests.get(self.canvas_api_heading + '/api/v1/courses/' +
                                str(course_id) + '/folders', headers=self.header,
                                params=param)
        if response.status_code == 401:
            return False
        for folder in response.json():
            folder_name = folder['full_name']
            # Replace +, _, -, and spaces with -
            folder_name = re.sub(r'[\s+_\-:]+', '-', folder_name)

            folder_path = os.path.join(save_path, folder_name.lower())
            os.makedirs(folder_path, exist_ok=True)

            folder_files_url = folder['files_url']
            folder_files_response = requests.get(folder_files_url, headers=self.header, params=param)

            reason_clean = folder_files_response.reason.replace(" ", "-")
            with open(os.path.join(folder_path, f'{reason_clean}.json'), 'w') as f:
                json.dump(folder_files_response.json(), f, indent=4)

            if folder_files_response.status_code == 401:
                logging.info(f"  * Folder: `{folder_name}` => "
                             f"{folder_files_response.status_code} - {folder_files_response.reason}")
                return False

            folders_count = folder['folders_count']
            files_count = folder['files_count']
            logging.info(f" * Folder `{folder_name}` (Folders: {folders_count}, Files: {files_count})")

            for file in folder_files_response.json():
                self.download_file_handler(file, folder_path)

        return True

    def download_module_files(self, course_id, save_path, param=None):
        response = requests.get(self.canvas_api_heading + '/api/v1/courses/' +
                                str(course_id) + '/modules', headers=self.header,
                                params=param)
        if response.status_code == 401:
            return False

        for module in response.json():
            module_name = module['name']
            # Replace +, _, -, and spaces with -
            module_name = re.sub(r'[\s+_\-:]+', '-', module_name)

            logging.info(f"  * Module: `{module_name}`")
            items_url = module['items_url']
            items_url_response = requests.get(items_url, headers=self.header, params=param)

            for item in items_url_response.json():
                file_type = item['type']
                if file_type != "File":
                    return False

                html_url = item['url']
                html_url_response = requests.get(html_url, headers=self.header)
                html_url_response_json = html_url_response.json()
                self.download_file_handler(html_url_response_json,
                                           os.path.join(save_path, "course-files"),
                                           module_name.lower())

        return True

    def download_file_handler(self, file_obj, folder_path, subfolder_name=None):
        os.makedirs(folder_path, exist_ok=True)
        file_name = file_obj['filename']
        # Replace any occurance of %XX with a -
        file_name = re.sub(r'%[0-9a-fA-F][0-9a-fA-F]', '-', file_name)
        # Replace +, _, -, and spaces with -
        file_name = re.sub(r'[\s+_\-:]+', '-', file_name)

        file_path = os.path.join(folder_path, file_name)

        file_url = file_obj['url']
        file_size = file_obj['size']
        file_size_mb = round(file_size / 1000000, 2)

        # Download the file to folder
        if not os.path.isfile(file_path) and subfolder_name is not None:
            return self.download_file_handler(file_obj, os.path.join(folder_path, subfolder_name))

        logging.info(f"    - Downloading `{file_name}` (size: {file_size} bytes, {file_size_mb} MB)")
        if os.path.isfile(file_path):
            # Get size in bytes of filepath
            existing_size = os.path.getsize(file_path)
            if existing_size == file_size:
                logging.info(f"      - File on disk has matching size = {existing_size}. Skipping...")
                return False

            logging.info(f"      - File needs updating: Current Size = {existing_size} => New Size = {file_size}")

        if file_url == '':
            logging.info(f"      - No URL found for file. Skipping...")
            logging.info(f"      - Lock explanation: {file_obj['lock_explanation']}")

            with open(f'{file_path}-locked.json', 'w') as f:
                json.dump(file_obj, f, indent=4)

            return False

        r = requests.get(file_url, stream=True)
        with open(file_path, 'wb') as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return True
