import logging
from datetime import datetime

from todoist import TodoistAPI


class TodoistHelper:

    def __init__(self, api_key):

        self.api = TodoistAPI(api_key.strip())
        self.sync(reset=True)

    def sync(self, reset=False):
        if reset:
            self.api.reset_state()
        self.api.sync()
        p_names_to_id_key = 'projects_by_name'
        p_names_key = 'project_names'

        self.api.state[p_names_to_id_key] = {}
        self.api.state[p_names_key] = []
        for project in self.api.state['projects']:
            name = project['name']
            self.api.state[p_names_to_id_key][project['name']] = project['id']
            self.api.state[p_names_key].append(name)

    def get_tasks(self) -> list:
        """
        Loads all user tasks from Todoist
        """
        return self.api.state['items']

    def get_project_names(self) -> list:
        """
        Loads all user projects from Todoist
        """
        logging.info("get_project_names")
        return self.api.state['project_names']

    def get_project_id(self, project_name):
        """
        Returns the project id corresponding to project_name
        """
        return self.api.state['projects_by_name'][project_name]

    def create_task(self, c_a, t_proj_id):
        """
        Adds a new task from a Canvas assignment object to Todoist under the project corresponding to project_id
        """
        logging.info(f"     NEW: Adding new Task for assignment")
        task_title = TodoistHelper.make_link_title(c_a["name"], c_a["html_url"])
        c_d = c_a['due_at']
        c_p = c_a['priority']
        self.api.add_item(task_title,
                          project_id=t_proj_id,
                          date_string=c_d,
                          priority=c_p)

    def create_projects(self, proj_names_list: list):
        """
        Checks to see if the user has a project matching their course names.
        If there isn't, a new project will be created
        """
        logging.info("# Creating Todoist projects:")
        for i, course_name in enumerate(proj_names_list):
            if not self.create_project(course_name):
                logging.info(
                    f"  {i + 1}. INFO: \"{course_name}\" already exists; skipping...")

    def create_project(self, proj_name):
        if proj_name in self.api.state['project_names']:
            logging.info(f" - INFO: Project already exists: \"{proj_name}\"")
            return False

        self.api.projects.add(proj_name)
        self.api.commit(raise_on_error=True)
        self.sync()
        logging.info(f" - OK: Created Project: \"{proj_name}\"")
        return True

    @staticmethod
    def make_link_title(title, url):
        """
        Creates a task title from an assignment object
        :param title:
        :param url:
        """
        return '[' + title + '](' + url + ')'

    @staticmethod
    def get_priority_name(priority: int):
        """
        Returns the name of the priority level
        """
        priorities = {
            1: "Normal",
            2: "Medium",
            3: "High",
            4: "Urgent"
        }
        return priorities[priority]

    @staticmethod
    def find_priority(assignment) -> int:
        """
        Finds the priority level of an assignment
        Task priority from 1 (normal, default value) to 4 (urgent).
        1: Normal, 2: Medium, 3: High, 4: Urgent
        """
        assignment_name = assignment['name']
        assignment_due_at = assignment['due_at']
        priority = 1

        keywords = {
            4: ['exam', 'test', 'midterm', 'final'],
            3: ['project', 'paper', 'quiz', 'homework', 'discussion'],
            2: ['reading', 'assignment']
        }

        for p, keywords in keywords.items():
            if p > priority and any(keyword in assignment_name.lower() for keyword in keywords):
                priority = p

        if assignment_due_at is not None:
            due_at = datetime.strptime(assignment_due_at, '%Y-%m-%dT%H:%M:%SZ')

            # If there are less than 3 days left on the assignment, set priority to 4
            if (due_at - datetime.now()).days < 3:
                priority = 4

        return priority
