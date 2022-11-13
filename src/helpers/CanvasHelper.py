import logging
from operator import itemgetter

import requests
from canvasapi import Canvas
from pick import pick
from termcolor import colored

from src.Utils import normalize_file_name, p_info
from src.helpers.CanvasDownloadHelper import CanvasDownloadHelper
from src.helpers.NotificationHelper import NotificationHelper


class CanvasHelper:
    def __init__(self, api_key, canvas_api_heading: str = "https://canvas.instructure.com"):
        self.api_key = api_key
        self.canvas_api_heading = canvas_api_heading
        self.header = {"Authorization": f"Bearer {api_key.strip()}"}
        p_info("# CanvasHelper: Initialized")
        logging.info(f"  - Canvas API Heading: {self.canvas_api_heading}")
        logging.info(f"  - Header: {self.header}")
        self.download_helper = CanvasDownloadHelper(api_key, canvas_api_heading)
        self.courses_id_name_dict = {}

    @staticmethod
    def get_course_names(course_ids):
        logging.info("# Getting Course Names...")

        course_names = []
        for course_obj in course_ids.values():
            logging.info(course_obj)
            course_names.append(course_obj["name"])
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
            response = requests.get(f"{self.canvas_api_heading}/api/v1/courses/{str(course_id)}/assignments",
                                    headers=self.header, params=param)

            if response.status_code == 401:
                logging.info("Unauthorized! Check Canvas API Key")
                exit()
            assignments.extend(iter(response.json()))
        return assignments

    def download_course_files_all(self, course_ids, param):
        logging.info(colored("# Downloading Folders & Files", attrs=["bold", "reverse"]))
        for course_id, c_obj in course_ids.items():
            c_name = c_obj["name"]
            logging.info(colored(f"# Course: {c_name} - Files", attrs=["bold"]))
            save_path = c_obj["save_path"]
            num_files = self.download_helper.download_course_files(course_id, save_path, param)
            logging.info(f" => Course: {c_name} - Files - Downloaded {num_files} files")
            if num_files > 0:
                NotificationHelper.send_notification(f"{c_name} - Files", f"Downloaded {num_files} files")
            logging.info("")

    def download_module_files_all(self, course_ids, param):
        logging.info(colored("# Downloading Any Additional Files in Modules", attrs=["bold", "reverse"]))

        for course_id, c_obj in course_ids.items():
            c_name = c_obj["name"]
            logging.info(colored(f"# Course: {c_name} - Modules", attrs=["bold"]))
            save_path = c_obj["save_path"]
            num_files = self.download_helper.download_module_files(course_id, save_path, param)
            logging.info(f" => Course: {c_name} - Modules - Downloaded {num_files} files")
            if num_files > 0:
                NotificationHelper.send_notification(f"{c_name} - Modules", f"Downloaded {num_files} files")
            logging.info("")

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
                self.courses_id_name_dict[c.id] = f"{c.course_code.replace(' ', '')} - {c.name}"
                i += 1
            except AttributeError:
                logging.info("  - Skipping invalid course entry.")

        logging.info(f"=> Found {len(self.courses_id_name_dict)} courses")
        courses = config_helper.get("courses")
        if courses is not None:
            logging.info("")
            logging.info("# You have previously selected courses:")
            for i, (c_id, c_obj) in enumerate(courses.items()):
                try:
                    c_name = c_obj["name"]
                except TypeError:
                    c_name = c_obj
                    courses[c_id] = {"name": c_name}
                logging.info(f"  {i + 1}. {c_name}")
            use_previous_input = "y" if skip_confirmation_prompts else input(
                    "Q: Would you like to use the courses selected last time? (Y/n) ")

            logging.info("")
            if use_previous_input.lower() == "y":
                return courses

        title = "Select the course(s) you would like to use (press SPACE to mark, ENTER to continue):"

        sorted_ids, sorted_courses = zip(*sorted(self.courses_id_name_dict.items(), key=itemgetter(0)))

        selected = pick(sorted_courses, title, multiselect=True, min_selection_count=1)

        logging.info("# SELECTED COURSES:")
        # logging.info("# If you would like to set a different name, enter the new name below.")
        # logging.info("# To use the course name as it appears on Canvas, leave the field blank.")

        selected_courses = {}
        for i, (course_name, index) in enumerate(selected):
            course_id = str(sorted_ids[index])
            course_name_prev = course_name
            logging.info(f" {i + 1}) {course_name_prev}")

            pick_title = f"{i + 1}) {course_name_prev}\n"
            pick_title += "    What name would you like to use for this course?"

            options = list(rename_list)
            options.extend(
                    (course_name_prev, normalize_file_name(course_name_prev, has_extension=False), "+ Create new name"))
            course_name_new, indices = pick(options, pick_title)

            if course_name_new == "+ Create new name":
                course_name_new = input("\t- Name: ")

            selected_courses[course_id] = {"name": course_name_new}

        # write course ids to self.config file
        config_helper.set("courses", selected_courses)
        return selected_courses
