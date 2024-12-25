import os
import git
import glob
import subprocess
from datetime import datetime

# Configuration for the repositories
REPOSITORIES = [
    {
        "name": "boilerplate-helm-charts",
        "repo_url": "git@github.com:Lynch0001/boilerplate-helm-charts.git",
        "base_branch": "main",
        "search_path": "boilerplate-helm-charts/archiver/values/demo/*",
        "script": "boilerplate-helm-charts/buildDemoProject.sh",
        "repo_path": "boilerplate-helm-charts"
    },
    {
        "name": "boilerplate-infra-live",
        "repo_url": "git@github.com:Lynch0001/boilerplate-infra-live.git",
        "base_branch": "main",
        "search_path": "boilerplate-infra-live/prod/us-east-1/xib/xib-demo/*",
        "script": "boilerplate-infra-live/buildInfraDemoProject.sh",
        "repo_path": "boilerplate-infra-live"
    },
]

PROJECT_NAMES = ["bravo", "charlie", "delta", "echo", "foxtrot", "golf", "hotel", "india", "juliet",
                 "kilo", "lima", "mike", "november", "oscar", "papa", "quebec", "romeo", "sierra", "tango",
                 "uniform", "victor", "whiskey", "xray", "yankee", "zulu"]

BRANCH_COUNTER_FILE = "./branch_counter.txt"  # Persistent counter file for branch incrementing

GIT_USERNAME = "lynch0001@gmail.com"  # Replace with your Git username
GIT_PASSWORD = ""  # Replace with your Git password


# Helper Functions

def run_command(command, cwd=None):
    """Executes a shell command and returns its output."""
    result = subprocess.run(command, cwd=cwd, text=True, shell=True, capture_output=True)
    #print(f"process results: {result}")
    if result.returncode != 0:
        raise Exception(f"Error running command: {command}\n{result.stderr}")
    return result.stdout.strip()


def update_branch_counter():
    """Increments the branch counter and resets the value daily."""
    today = datetime.now().strftime("%Y%m%d")
    if os.path.exists(BRANCH_COUNTER_FILE):
        with open(BRANCH_COUNTER_FILE, "r") as f:
            data = f.read().strip().split()
            stored_date, counter = data[0], int(data[1])
            if stored_date == today:
                counter += 1
            else:
                counter = 1  # Reset counter for the new day
    else:
        counter = 1  # Initialize counter if file doesn't exist

    # Write the updated counter to the file
    with open(BRANCH_COUNTER_FILE, "w") as f:
        f.write(f"{today} {counter}")

    return counter


def find_unused_project_name(search_path, project_names):
    """Finds the first project name not already present in the specified paths."""
    search_paths = []
    for project in project_names:
        path = search_path[:-2] + "/" + project
        search_paths.append(path)

        print(f"checking {search_path} for unused projects")
        resolved_paths = glob.glob(search_path) # list of used projects
        print(f"resolved paths {resolved_paths}")

        for name in project_names:
            print(f"checking {name} for unused projects")
            if all(name not in path for path in resolved_paths):
                return name
    return None


def execute_bash_script(script_path, argument):
    """Runs a bash script with the provided argument."""
    print(f"Running script {script_path} with argument: {argument}")
    run_command(f"{script_path} {argument}")


# Main Function
def main():
    today = datetime.now().strftime("%Y%m%d")  # Get the current date

    for repo in REPOSITORIES:
        repo_name = repo["name"]
        repo_url = repo["repo_url"]
        base_branch = repo["base_branch"]
        search_path = repo["search_path"]
        script_path = repo["script"]
        repo_dir = repo["repo_path"]

        branch_index = update_branch_counter()  # Increment and reset branch index if needed

        # Clone or update the repository
        if not os.path.exists(repo_dir):
            print(f"Cloning repository {repo_url}...")
            repo_data = git.Repo.clone_from(
                repo_url.replace("https://", f"https://{GIT_USERNAME}:{GIT_PASSWORD}@"),
                repo_dir
            )
        else:
            print(f"Repository already cloned in {repo_dir}.")
            repo_data = git.Repo(repo_dir)

        # Checkout the base branch
        print(f"Checking out the base branch '{base_branch}'...")
        repo_data.git.checkout(base_branch)

        # Create and switch to a new branch
        branch_name = f"{repo_name}-{today}-{branch_index}"  # Format branch name as date-index

        # Create and checkout a new branch
        if branch_name not in repo_data.heads:
            print(f"Creating and checking out new branch '{branch_name}'...")
            repo_data.git.checkout("-b", branch_name)
        else:
            print(f"Branch '{branch_name}' already exists. Checking out...")
            repo_data.git.checkout(branch_name)

        # Find an unused project name if search paths are provided; not applicable for db update
        unused_name = None
        if search_path:
            unused_name = find_unused_project_name(search_path, PROJECT_NAMES)
            if not unused_name:
                print(f"No unused project names found for {repo_name}. Skipping...") ##### throw error
                continue

        # Execute the bash script and create project files for commit
        if unused_name:
            execute_bash_script(script_path, unused_name)
        else:
            execute_bash_script(script_path, "")  # TODO: db config wont have new project

        # Check for changes
        print("Checking for changes...")
        if repo_data.is_dirty(untracked_files=True):
            print("Changes detected.")
            # Stage changes
            print("Staging changes...")
            repo_data.git.add(all=True)

            # Commit changes
            commit_message = f"Automated: {repo_name}"
            if unused_name:
                commit_message += f" -> project: {unused_name}"
            print(f"Committing changes with message: '{commit_message}'")
            repo_data.git.commit("-m", commit_message)

            # Push changes
            print(f"Pushing changes to branch '{branch_name}'...")
            repo_data.git.push("origin", branch_name)
        else:
            print("No changes to commit.")

        # Cleanup
        print(f"Cleaning up repo {repo_dir}")
        run_command(f"rm -rf {repo_dir}")

    #
    # DB CONFIG
    #
    print("Processing completed for all projects!")

if __name__ == "__main__":
    main()
