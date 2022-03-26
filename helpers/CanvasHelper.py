import json
import logging
import os
import re
from operator import itemgetter

import requests
from canvasapi import Canvas
from pick import pick


class CanvasHelper:

    def __init__(self, api_key, canvas_api_heading="https://canvas.instructure.com"):
        self.api_key = api_key
        self.canvas_api_heading = canvas_api_heading
        self.header = {"Authorization": f"Bearer {api_key.strip()}"}
        self.download_helper = CanvasDownloadHelper(api_key)
        self.courses_id_name_dict = {}

    @staticmethod
    def get_course_names(course_ids):
        logging.info("# Getting Course Names...")

        course_names = []
        for course_obj in course_ids.values():
            course_names.append(course_obj['name'])
        logging.info("")
        return course_names

    def get_assignments(self, course_ids, param):
        """
        Iterates over the selected_course_ids list and loads all the users assignments for those classes.
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
        num_courses = 0
        num_files_total = 0
        for course_id, c_obj in course_ids.items():
            c_name = c_obj['name']
            logging.info(f"# Course: {c_name}")
            save_path = c_obj['save_path']
            num_files = self.download_helper.download_course_files(course_id, save_path, param)
            if not num_files:
                continue
            num_courses += 1
            num_files_total += num_files

        logging.info("")
        return num_courses, num_files_total

    def download_module_files_all(self, course_ids, param):
        logging.info("# Downloading Any Additional Files in Modules")
        num_courses = 0
        num_files_total = 0
        for course_id, c_obj in course_ids.items():
            c_name = c_obj['name']
            logging.info(f"# Course: {c_name}")
            save_path = c_obj['save_path']
            num_files = self.download_helper.download_module_files(course_id, save_path, param)
            if not num_files:
                continue
            num_courses += 1
            num_files_total += num_files

        logging.info("")
        return num_courses, num_files_total

    def select_courses(self, config_helper, rename_list=None, skip_confirmation_prompts=False):
        """
        Allows the user to select the courses that they want to transfer while generating a dictionary
        that has course ids as the keys and their names as the values
        """
        if rename_list is None:
            rename_list = []
        logging.info("# Fetching courses from Canvas:")
        canvas = Canvas("https://canvas.instructure.com", self.api_key)
        courses_pag = canvas.get_courses()

        i = 1
        for c in courses_pag:
            try:
                self.courses_id_name_dict[c.id] = f"{c.course_code.replace(' ', '')} - {c.name} [ID: {c.id}]"
                i += 1
            except AttributeError:
                logging.info("  - Skipping invalid course entry.")

        logging.info(f"=> Found {len(self.courses_id_name_dict)} courses")
        courses = config_helper.get('courses')
        if courses is not None:
            logging.info("")
            logging.info("# You have previously selected courses:")
            for i, (c_id, c_obj) in enumerate(courses.items()):
                try:
                    c_name = c_obj['name']
                except TypeError:
                    c_name = c_obj
                    courses[c_id] = {'name': c_name}
                logging.info(f'  {i + 1}. {c_name} [ID: {c_id}]')
            if not skip_confirmation_prompts:
                use_previous_input = input(
                    "Q: Would you like to use the courses selected last time? (Y/n) ")
            else:
                use_previous_input = "y"
            logging.info("")
            if use_previous_input.lower() == "y":
                return courses

        title = "Select the course(s) you would like to use (press SPACE to mark, ENTER to continue):"

        sorted_ids, sorted_courses = zip(
            *sorted(self.courses_id_name_dict.items(), key=itemgetter(0)))

        selected = pick(sorted_courses, title,
                        multiselect=True, min_selection_count=1)

        logging.info("# SELECTED COURSES:")
        logging.info(
            "# If you would like to set a different name, enter the new name below.")
        logging.info(
            "# To use the course name as it appears on Canvas, leave the field blank.")

        selected_courses = {}
        for i, (course_name, index) in enumerate(selected):
            course_id = str(sorted_ids[index])
            course_name_prev = course_name
            logging.info(f" {i + 1}) {course_name_prev}")

            pick_title = f"{i + 1}) {course_name_prev}\n"
            pick_title += f"    Select a match?"

            options = list(rename_list)
            options.append("+ Create new name")

            course_name_new, indices = pick(options, pick_title)

            if selected == "+ Create new name":
                course_name_new = input("\t- Name: ")

            selected_courses[course_id] = course_name_new

        # write course ids to self.config file
        config_helper.set('courses', selected_courses)
        return selected_courses


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
        if response.status_code != 200:
            return False

        num_files = 0
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
                if self.download_file_handler(file, folder_path):
                    num_files += 1

        return num_files

    def download_module_files(self, course_id, save_path, param=None):
        if param is None:
            param = {}
        response = requests.get(self.canvas_api_heading + '/api/v1/courses/' +
                                str(course_id) + '/helpers', headers=self.header,
                                params=param)
        if response.status_code != 200:
            return False

        num_files = 0
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
                if self.download_file_handler(html_url_response_json,
                                              os.path.join(save_path, "course-files"),
                                              module_name.lower()):
                    num_files += 1

        return num_files

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
