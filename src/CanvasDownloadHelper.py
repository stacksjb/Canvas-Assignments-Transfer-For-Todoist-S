import hashlib
import json
import logging
import os
import re

import requests
from bs4 import BeautifulSoup
from termcolor import colored


class CanvasDownloadHelper:
    def __init__(self, api_key, canvas_api_heading="https://canvas.instructure.com"):
        self.canvas_api_heading = canvas_api_heading
        self.header = {"Authorization": f"Bearer {api_key.strip()}"}
        logging.info("# CanvasDownloadHelper: initialized")
        logging.info(f"  - Canvas API Heading: {self.canvas_api_heading}")
        logging.info(f"  - Header: {self.header}")

    def download_course_files(self, course_id, save_path, param=None):
        if param is None:
            param = {}
        response = requests.get(f"{self.canvas_api_heading}/api/v1/courses/{str(course_id)}/folders",
                                headers=self.header, params=param)

        if response.status_code != 200:
            logging.info(colored(f"  - Error: {response.status_code}", "red"))
            return False

        num_files = 0
        for folder in response.json():
            folder_name = folder["full_name"]
            # Replace +, _, -, and spaces with -
            folder_name = re.sub(r"[\s+_\-:\.]+", "-", folder_name)

            folder_path = os.path.join(save_path, folder_name.lower())
            os.makedirs(folder_path, exist_ok=True)

            folder_files_url = folder["files_url"]
            folder_files_response = requests.get(folder_files_url, headers=self.header, params=param)

            reason_clean = folder_files_response.reason.replace(" ", "-")
            with open(os.path.join(folder_path, f"{reason_clean}.json"), "w") as f:
                json.dump(folder_files_response.json(), f, indent=4)

            if folder_files_response.status_code != 200:
                logging.info(colored(f"  * Folder: `{folder_name}` => "
                                     f"{folder_files_response.status_code} - {folder_files_response.reason}", "red", ))
                continue

            folders_count = folder["folders_count"]
            files_count = folder["files_count"]
            logging.info(f" * Folder `{folder_name}` (Folders: {folders_count}, Files: {files_count})")

            for file in folder_files_response.json():
                try:
                    if self.download_file_handler(file["display_name"], file["url"], file, folder_path):
                        num_files += 1
                except Exception as e:
                    logging.info(colored(f"  - Error: {e}", "red"))
                    logging.info(json.dumps(file, indent=4))
                    logging.info(json.dumps(folder, indent=4))
                    continue

        return num_files

    def download_module_files(self, course_id, save_path, param=None):
        if param is None:
            param = {}

        response = requests.get(f"{self.canvas_api_heading}/api/v1/courses/{str(course_id)}/modules",
                                headers=self.header, params=param)

        if response.status_code != 200:
            logging.info(colored(f"  - Error: {response.status_code}", "red"))
            return False

        save_path = os.path.join(save_path, "course-files")

        num_files = 0
        for module in response.json():
            module_name = module["name"]
            # Replace +, _, -, and spaces with -
            module_name = re.sub(r"[\s+_\-:\.]+", "-", module_name)

            logging.info(f" * Module: `{module_name}`")
            items_url = module["items_url"]
            items_url_response = requests.get(items_url, headers=self.header, params=param)

            for item in items_url_response.json():
                file_type = item["type"]
                if file_type.lower() != "file":
                    folder_path = os.path.join(save_path, module_name.lower())
                else:
                    folder_path = save_path

                # if file_type != "File":
                if "url" not in item:
                    logging.info(colored(f"    - {file_type} - Skipping", "yellow"))
                    continue

                html_url = item["url"]
                html_url_response = requests.get(html_url, headers=self.header)
                html_url_response_json = html_url_response.json()

                # pprint(item)
                # pprint(html_url_response_json)
                try:
                    if file_type.lower() == "file":
                        file_name = html_url_response_json["display_name"]
                        file_url = html_url_response_json["url"]
                        if self.download_file_handler(file_name, file_url, html_url_response_json, folder_path,
                                                      module_name.lower(), ):
                            num_files += 1
                        continue
                    if file_type.lower() == "page":
                        file_name = html_url_response_json["title"]
                        body = html_url_response_json["body"]
                    elif file_type.lower() == "assignment":
                        file_name = html_url_response_json["name"]
                        body = html_url_response_json["description"]
                    elif file_type.lower() == "quiz":
                        file_name = html_url_response_json["title"]
                        body = html_url_response_json["description"]
                    elif file_type.lower() == "discussion":
                        file_name = html_url_response_json["title"]
                        body = html_url_response_json["message"]
                    else:
                        raise Exception(f"Unknown file type: {file_type}")

                    if self.download_html_helper(file_name, body, folder_path):
                        num_files += 1
                except Exception as e:
                    logging.info(colored(f"    - {file_type} - Error: {e}", "red"))
                    logging.info(json.dumps(item, indent=4))
                    logging.info(json.dumps(html_url_response_json, indent=4))
                    continue

        return num_files

    def download_file_handler(self, file_name, file_url, file_obj, folder_path, subfolder_name=None):
        os.makedirs(folder_path, exist_ok=True)
        file_name = self.normalize_file_name(file_name)
        file_path = os.path.join(folder_path, file_name)

        if "size" in file_obj:
            file_size = file_obj["size"]
            file_size_mb = round(file_size / 1000000, 2)

            # Download the file to folder
            if not os.path.isfile(file_path) and subfolder_name is not None:
                return self.download_file_handler(file_name, file_url, file_obj,
                                                  os.path.join(folder_path, subfolder_name), )

            if os.path.isfile(file_path):
                # Get size in bytes of filepath
                existing_size = os.path.getsize(file_path)
                if existing_size == file_size:
                    logging.info(
                            colored(f"    - Skipping `{file_name}` (size: {file_size} bytes, existing_size: {existing_size} bytes)",
                                    "yellow"))
                    return False
                logging.info(
                        colored(f"    - Updating `{file_name}` (current size: {existing_size} bytes, new size: {file_size} bytes)",
                                "green"))
            else:
                logging.info(
                    colored(f"    - Downloading `{file_name}` (size: {file_size} bytes, {file_size_mb} MB)", "green"))
        else:
            logging.info(colored(f"    - Downloading `{file_name}`", "green"))

        if file_url == "" and "lock_explanation" in file_obj:
            logging.info(colored("      - No URL found for file. Skipping...", "red"))
            logging.info(colored(f"      - Lock explanation: {file_obj['lock_explanation']}", "red"))

            with open(f"{file_path}-locked.json", "w") as f:
                json.dump(file_obj, f, indent=4)

            return False

        r = requests.get(file_url, stream=True, headers=self.header)
        with open(file_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024):
                if chunk:
                    f.write(chunk)

        return True

    def download_html_helper(self, file_name, body, folder_path):
        os.makedirs(folder_path, exist_ok=True)
        file_name = self.normalize_file_name(f"{file_name}.html")
        file_path = os.path.join(folder_path, file_name)

        logging.info(f"    - `{file_name}`")
        # Use beautiful soup to parse the html and download any images and files
        soup = BeautifulSoup(body, "html.parser")

        folder_img = os.path.join(folder_path, "img")
        folder_res = os.path.join(folder_path, "res")
        os.makedirs(folder_img, exist_ok=True)
        os.makedirs(folder_res, exist_ok=True)

        all_imgs = soup.find_all("img")
        len_all_imgs = len(all_imgs) if all_imgs is not None else 0
        for i, img in enumerate(all_imgs):
            # pprint(img)
            if "src" in img.attrs:
                img_url = img.attrs["src"]
                if img_url.startswith("http"):
                    # create a hash of the url to use as the filename
                    img_name = hashlib.md5(img_url.encode("utf-8")).hexdigest()
                    # save to res folder
                    img_path = os.path.join(folder_img, img_name)
                    if not os.path.isfile(img_path):
                        logging.info(colored(f"       - Downloading image {i + 1}/{len_all_imgs}: {img_url}", "green"))
                        r = requests.get(img_url, stream=True, headers=self.header)
                        with open(img_path, "wb") as f:
                            for chunk in r.iter_content(chunk_size=1024):
                                if chunk:
                                    f.write(chunk)
                    else:
                        logging.info(colored(f"       - Skipping image {i + 1}/{len_all_imgs}: {img_url}", "yellow"))
                    img.attrs["src"] = f"./img/{img_name}"

        if os.path.isfile(file_path):
            existing_size = os.path.getsize(file_path)
            curr_size = len(soup.prettify().encode('utf-8'))
            if existing_size == curr_size:
                logging.info(colored(
                    f"       => Skipping `{file_name}` (size: {curr_size} bytes, existing_size: {existing_size} bytes)",
                    "yellow"))
                return False
            else:
                logging.info(colored(
                    f"       => Updating `{file_name}` (current size: {existing_size} bytes, new size: {curr_size} bytes)",
                    "green"))
        else:
            logging.info(colored(f"       => Downloading `{file_name}`", "green"))

        with open(file_path, "w") as f:
            f.write(soup.prettify())

        return True

    def normalize_file_name(self, file_name):
        # Replace any occurance of %XX with a -
        file_name = re.sub(r"%[0-9a-fA-F][0-9a-fA-F]", "-", file_name)
        # Replace +, _, -, and spaces with -
        fnsplit = file_name.split(".")
        name, ext = fnsplit[0:-1], fnsplit[-1]
        name = "-".join(name)
        name = re.sub(r"[\s+_\-:]+", "-", name)
        name = name.strip("-")
        file_name = f"{name}.{ext}"
        return file_name
