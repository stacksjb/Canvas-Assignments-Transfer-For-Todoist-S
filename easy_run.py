import json
from operator import itemgetter

import requests
from canvasapi import Canvas
from pick import pick
from todoist.api import TodoistAPI

# Loaded configuration files
config = {}
header = {}
param = {'per_page': '100', 'include': 'submission'}
course_ids = {}
assignments = []
todoist_tasks = []
courses_id_name_dict = {}
todoist_project_dict = {}

input_prompt = "> "


def main():
    print("  ###################################################")
    print(" #     Canvas-Assignments-Transfer-For-Todoist     #")
    print("###################################################\n")
    initialize_api()
    select_courses()

    load_todoist_projects()
    load_assignments()
    load_todoist_tasks()
    create_todoist_projects()
    transfer_assignments_to_todoist()
    print("# Done!")


# Makes sure that the user has their api keys set up and sets api variables
def initialize_api():
    global config
    global todoist_api

    with open("config.json") as config_file:
        config = json.load(config_file);
    if len(config['todoist_api_key']) == 0:
        print(
            "Your Todoist API key has not been configured. To add an API token, go to your Todoist settings and copy the API token listed under the Integrations Tab. Copy the token and paste below when you are done.")
        config['todoist_api_key'] = input(input_prompt)
        with open("config.json", "w") as outfile:
            json.dump(config, outfile)
    if (len(config['canvas_api_key'])) == 0:
        print(
            "Your Canvas API key has not been configured. To add an API token, go to your Canvas settings and click on New Access Token under Approved Integrations. Copy the token and paste below when you are done.")
        config['canvas_api_key'] = input(input_prompt)
        with open("config.json", "w") as outfile:
            json.dump(config, outfile)

    # create todoist_api object globally
    todoist_api = TodoistAPI(config['todoist_api_key'].strip())
    todoist_api.reset_state()
    todoist_api.sync()
    header.update({"Authorization": "Bearer " + config['canvas_api_key'].strip()})
    print("# API INITIALIZED")


# Allows the user to select the courses that they want to transfer while generating a dictionary
# that has course ids as the keys and their names as the values
def select_courses():
    global config
    print("# Fetching courses from Canvas:")
    canvas = Canvas("https://canvas.instructure.com", config['canvas_api_key'])
    courses_pag = canvas.get_courses()

    i = 1
    for c in courses_pag:
        try:
            courses_id_name_dict[c.id] = f"{c.course_code.replace(' ', '')} - {c.name} [{c.id}]"
            i += 1
        except AttributeError:
            print(" - Skipping invalid course entry.")

    print(f"=> Found {len(courses_id_name_dict)} courses")

    if config['courses']:
        print()
        print("# You have previously selected courses:")
        for i, (c_id, c_name) in enumerate(config['courses'].items()):
            print(f' {i + 1}) {c_name} [{c_id}]')

        use_previous_input = input("Would you like to use the courses selected last time? (y/n) ")
        print("")
        if use_previous_input.lower() == "y":
            for c_id, c_name in config['courses'].items():
                course_ids[c_id] = c_name
            return

    title = "Select the course(s) you would like to add to Todoist (press SPACE to mark, ENTER to continue):"

    sorted_ids, sorted_courses = zip(*sorted(courses_id_name_dict.items(), key=itemgetter(0)))

    selected = pick(sorted_courses, title, multiselect=True, min_selection_count=1)

    print("# SELECTED COURSES:")
    print("# If you would like to rename a course as it appears on Todoist, enter the new name below.")
    print("# To use the course name as it appears on Canvas, leave the field blank.")
    for i, (course_name, index) in enumerate(selected):
        course_id = sorted_ids[index]
        course_name_prev = course_name
        print(f" {i + 1}) {course_name_prev}")
        course_name_new = input("    - Project Name: ")
        course_ids[course_id] = course_name_new

    # write course ids to config.json
    config['courses'] = course_ids
    with open("config.json", "w") as outfile:
        json.dump(config, outfile)


# Iterates over the course_ids list and loads all of the users assignments
# for those classes. Appends assignment objects to assignments list
def load_assignments():
    for course_id in course_ids:
        response = requests.get(config['canvas_api_heading'] + '/api/v1/courses/' +
                                str(course_id) + '/assignments', headers=header,
                                params=param)
        if response.status_code == 401:
            print('Unauthorized! Check Canvas API Key')
            exit()
        for assignment in response.json():
            assignments.append(assignment)


# Loads all user tasks from Todoist
def load_todoist_tasks():
    tasks = todoist_api.state['items']
    for task in tasks:
        todoist_tasks.append(task)


# Loads all user projects from Todoist
def load_todoist_projects():
    print("# Loading Todoist projects...")
    projects = todoist_api.state['projects']
    for project in projects:
        todoist_project_dict[project['name']] = project['id']
    # print(todoist_project_dict)


# Checks to see if the user has a project matching their course names, if there
# isn't a new project will be created
def create_todoist_projects():
    print("# Creating Todoist projects")
    for course_id, course_name in course_ids.items():
        if course_name not in todoist_project_dict:
            # TODO: Add option to re-name course names

            project = todoist_api.projects.add(course_name)
            todoist_api.commit()
            todoist_api.sync()

            todoist_project_dict[project['name']] = project['id']
        else:
            print(f" - Project \"{course_name}\" already exists: not creating new project.")


# Transfers over assignments from canvas over to Todoist, the method Checks
# to make sure the assignment has not already been trasnfered to prevent overlap
def transfer_assignments_to_todoist():
    print("# Transferring assignments to Todoist")
    for i, assignment in enumerate(assignments):
        course_name = course_ids[str(assignment['course_id'])]
        project_id = todoist_project_dict[course_name]

        is_added = False
        is_synced = True
        item = None
        for task in todoist_tasks:
            if task['content'] == ('[' + assignment['name'] + '](' + assignment['html_url'] + ')' + ' Due') and \
                    task['project_id'] == project_id:
                print(f"{i + 1}. Assignment already synced: \"{assignment['name']}\"")
                is_added = True
                # print(assignment)
                if task['due'] and task['due']['date'] != assignment['due_at']:
                    is_synced = False
                    item = task
                    print(
                        f"  - Updating assignment due date: \"{assignment['name']}\" from [{task['due'].get('date')}] to [{assignment['due_at']}]")
                    break
            # print(assignment)

        if not is_added:
            if assignment['submission']['submitted_at'] is None:
                print(f"{i + 1}. Adding assignment: \"{assignment['name']}\", due: {assignment['due_at']}")
                add_new_task(assignment, project_id)
            else:
                print(f"{i + 1}. Assignment already exists: \"{assignment['name']}\", due: {assignment['due_at']}")
        elif not is_synced:
            print(f"{i + 1}. Updating assignment: \"{assignment['name']}\", due: {assignment['due_at']}")
            update_task(assignment, item)

        #     print("assignment already synced")
    todoist_api.commit()


# Adds a new task from a Canvas assignment object to Todoist under the
# project coreesponding to project_id
def add_new_task(assignment, project_id):
    # print(assignment);
    todoist_api.add_item('[' + assignment['name'] + '](' + assignment['html_url'] + ')' + ' Due',
                         project_id=project_id,
                         date_string=assignment['due_at'])


def update_task(assignment, item):
    item.update(due={
        'date': assignment['due_at']
    })


if __name__ == "__main__":
    main()
