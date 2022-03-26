import logging
from datetime import datetime

from helpers.CanvasHelper import CanvasHelper
from helpers.ConfigHelper import ConfigHelper
from helpers.TodoistHelper import TodoistHelper


class CanvasToTodoist:

    def __init__(self, config_path, skip_confirmation_prompts=False):
        self.skip_confirmation_prompts = skip_confirmation_prompts
        self.param = {'per_page': '100', 'include': 'submission'}
        self.input_prompt = "> "
        self.selected_course_ids = None

        # Loaded configuration files
        self.config_helper = ConfigHelper(config_path, self.input_prompt, self.skip_confirmation_prompts)

        self.canvas_helper = CanvasHelper(self.config_helper.get('canvas_api_key'))
        self.todoist_helper = TodoistHelper(self.config_helper.get('todoist_api_key'))

    def run(self):
        logging.info("###################################################")
        logging.info("#     Canvas-Assignments-Transfer-For-Todoist     #")
        logging.info("###################################################")

        todoist_project_names = self.todoist_helper.get_project_names()
        self.selected_course_ids = self.canvas_helper.select_courses(self.config_helper,
                                                                     todoist_project_names,
                                                                     self.skip_confirmation_prompts)

        course_names = self.canvas_helper.get_course_names(self.selected_course_ids)

        self.todoist_helper.create_projects(course_names)

        assignments = self.canvas_helper.get_assignments(self.selected_course_ids, self.param)
        self.transfer_assignments_to_todoist(assignments)
        logging.info("# Finished!")

    def check_existing_task(self, assignment, project_id):
        """
        Checks to see if a task already exists for the assignment.
        Return flags for whether the task exists and if it needs to be updated,
        as well as the corresponding task object.
        """
        is_added = False
        is_synced = True
        item = None
        for task in self.todoist_helper.get_tasks():
            task_title = TodoistHelper.make_link_title(assignment["name"], assignment["html_url"])
            # If title and project match, then the task already exists
            if task['content'] == task_title and task['project_id'] == project_id:
                is_added = True
                # Check if the task is synced by comparing due dates and priority
                if (task['due'] and task['due']['date'] != assignment['due_at']) or \
                        task['priority'] != assignment['priority']:
                    is_synced = False
                    item = task
                    break
        return is_added, is_synced, item

    def transfer_assignments_to_todoist(self, assignments):
        """
        Transfers over assignments from Canvas over to Todoist.
        The method Checks to make sure the assignment has not already been transferred to prevent overlap.
        """
        logging.info("# Transferring assignments to Todoist...")

        summary = {'added': [], 'updated': [],
                   'is-submitted': [], 'up-to-date': []}

        for i, c_a in enumerate(assignments):
            # Get the canvas assignment name, due date, course name, todoist project id
            c_n = c_a['name']
            c_d = c_a['due_at']
            c_cn = self.selected_course_ids[str(c_a['course_id'])]['name']
            t_proj_id = self.todoist_helper.get_project_id(c_cn)

            # Find the corresponding priority based on the assignment properties
            priority = TodoistHelper.find_priority(c_a)
            c_a['priority'] = priority

            # Check if the assignment already exists in Todoist and if it needs updating
            is_added, is_synced, item = self.check_existing_task(c_a, t_proj_id)
            logging.info(f"  {i + 1}. Assignment: \"{c_n}\"")

            # Handle cases for adding and updating tasks on Todoist
            if not is_added:
                if c_a['submission']['workflow_state'] == "unsubmitted":
                    self.todoist_helper.create_task(c_a, t_proj_id)
                    summary['added'].append(c_a)
                else:
                    logging.info(f"     INFO: Already submitted, skipping...")
                    summary['is-submitted'].append(c_a)
            elif not is_synced:
                self.update_task(c_a, item)
                summary['updated'].append(c_a)
            else:
                logging.info(f"     OK: Task is already up to date!")
                summary['up-to-date'].append(c_a)
            logging.info(f"     Course: {c_cn}")
            logging.info(f"     Due Date: {c_d}")
            logging.info(f"     Priority: {TodoistHelper.get_priority_name(priority)}")

        # Commit changes to Todoist
        self.todoist_helper.api.commit(raise_on_error=True)

        # Print out short summary
        logging.info("")
        logging.info(f"# Short Summary:")
        logging.info(f"  * Added: {len(summary['added'])}")
        logging.info(f"  * Updated: {len(summary['updated'])}")
        logging.info(f"  * Already Submitted: {len(summary['is-submitted'])}")
        logging.info(f"  * Up to Date: {len(summary['up-to-date'])}")

        if len(summary['added']) > 0 or len(summary['updated']) > 0:
            logging.info("New tasks added or updated. Sending notification.")
            n_title = f"Canvas to Todoist (Total: {len(assignments)})"
            n_msg = f"Added {len(summary['added'])} & Updated {len(summary['updated'])}.\n" \
                    f"Completed: {len(summary['is-submitted'])} & Up-to-Date {len(summary['up-to-date'])}."
            NotificationHelper.send_notification(n_title, n_msg)
        else:
            logging.info("No new tasks added or updated. Skipping notification.")

        # Print detailed summary?
        logging.info("")
        if not self.skip_confirmation_prompts:
            answer = input("Q: Print Detailed Summary? (Y/n): ")
        else:
            answer = "y"

        if answer.lower() == 'y':
            logging.info("")
            logging.info(f"# Detailed Summary:")
            for cat in reversed(summary.keys()):
                a_list = summary[cat]
                logging.info(f"  * {cat.upper()}: {len(a_list)}")
                for i, c_a in enumerate(a_list):
                    c_n = c_a['name']
                    c_cn = self.selected_course_ids[str(c_a['course_id'])]['name']
                    a_p = c_a['priority']
                    a_d = c_a['due_at']
                    d = None
                    if a_d:
                        d = datetime.strptime(a_d, '%Y-%m-%dT%H:%M:%SZ')
                    # Convert to format: May 22, 2022 at 12:00 PM
                    d_nat = "Unknown" if d is None else d.strftime(
                        '%b %d, %Y at %I:%M %p')
                    logging.info(f"    {i + 1}. \"{c_n}\"")
                    logging.info(f"         Course: {c_cn}")
                    logging.info(f"         Due Date: {d_nat}")
                    logging.info(f"         Priority: {TodoistHelper.get_priority_name(a_p)}")

    @staticmethod
    def update_task(c_a, t_task):
        """
        Updates an existing task from a Canvas assignment object to Todoist
        """
        updates_list = []
        # Check if due date has changed
        t_d = t_task['due']['date'] if t_task['due'] else None
        c_d = c_a['due_at']
        if t_d != c_d:
            updates_list.append('due date')
        # Check if priority has changed
        t_p = t_task['priority']
        c_p = c_a['priority']
        # Print changes
        if t_p != c_p:
            updates_list.append('priority')
        logging.info(f"     UPDATE: Updating Task: " + ", ".join(updates_list))
        # Update Todoist task
        t_task.update(due={
            'date': c_d,
        },
            priority=c_p)
