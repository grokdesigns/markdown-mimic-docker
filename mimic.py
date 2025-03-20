import os
import logging
import re
import subprocess

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

subprocess.run(["git", "config", "--global", "--add", "safe.directory", "/github/workspace"])
start_comment = '<!--MIMIC_START-->'
end_comment = '<!--MIMIC_END-->'
content_pattern = f"{start_comment}[\\s\\S]+{end_comment}"

# Set safe directory for git to prevent dubious ownership error
# Now you can proceed with your Git operations safely
# Example of adding files to Git
try:
    result = subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd="/github/workspace")
    if result.returncode != 0:
        raise RuntimeError(f"Failed to add files: {result.stderr}")
except Exception as e:
    print("Error occurred:", e)

def log_files_in_directory(directory):
    """Logs all files in the specified directory."""
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            log_files_in_directory(item_path)
        else:
            logger.info(f"  - {item}, Size: {os.path.getsize(item_path)} bytes")

def git_commit_push(output_folder, commit_message, branch_name):
    """Stages and pushes changes to the repository."""
    # Change to the working directory for git
    os.chdir("/github/workspace")
    # Stage output folder
    subprocess.run(["git", "add", '.'], check=True)

    # Commit changes
    try:
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
    except subprocess.CalledProcessError as e:
        logger.info("No changes to commit.")
        return

    # Push changes back to the repository, specifying the branch
    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    subprocess.run(["git", "push", f"https://x-access-token:{github_token}@github.com/{repo}.git", f"HEAD:{branch_name}"], check=True)

def generate_new_content(source_content, target_content):
    """Generate new content by replacing the marked section"""
    replacement = f"{start_comment}\n{source_content}\n{end_comment}"
    return re.sub(content_pattern, replacement, target_content)

def main():
    """Execute the Mimic Processing Workflow."""
    try:
        # Change working directory to /workspace
        os.chdir("/github/workspace")

        input_folder = os.environ['INPUT_INPUT_FOLDER']
        output_folder = os.environ['INPUT_OUTPUT_FOLDER']
        branch = os.getenv("INPUT_BRANCH_NAME") 
        git_username = os.environ.get('INPUT_GIT_USERNAME', 'github-actions[bot]')  # Mapped from action.yml
        git_email = os.environ.get('INPUT_GIT_EMAIL', 'github-actions[bot]@users.noreply.github.com')  # Mapped from action.yml
        commit_message = os.environ.get('INPUT_COMMIT_MESSAGE', '🤖 - Updated via Markdown Mimic')  # Mapped from action.yml
        skip_ci = os.environ.get('INPUT_SKIP_CI', 'yes')  # Mapped from action.yml
        file_ext = os.environ.get('INPUT_FILE_EXT', 'md')  # Mapped from action.yml
        root_dir = '/github/workspace/'
        content_pattern = f"{start_comment}[\\s\\S]+{end_comment}"

        subprocess.run(["git", "config", "--global", "--add", "user.email", git_email])
        subprocess.run(["git", "config", "--global", "--add", "user.name", git_username])

        # Stripping leading and trailing slashes
        input_folder = input_folder.strip('/')
        output_folder = output_folder.strip('/')

        # Log the resolved input/output paths
        logger.info(f"SRCFOLDER (Input): {input_folder}")
        logger.info(f"DSTFOLDER (Output): {output_folder}")
        logger.info(f"Git Username: {git_username}")
        logger.info(f"Git Email: {git_email}")
        logger.info(f"Commit Message: {commit_message}")
        logger.info(f"Skip CI: {skip_ci}")

        # Define the full path for the output folder
        output_path = os.path.join(root_dir, output_folder)

        # Create the output folder if it doesn't exist
        os.makedirs(output_path, exist_ok=True)

        # Check if the input folder exists
        if not os.path.exists(input_folder):
            raise FileNotFoundError(f"Error: Input directory '{input_folder}' does not exist.")

        logger.info("Logging contents of the input folder:")
        for filename in os.listdir(input_folder):
            logger.info(f"  - {filename}")

        # Get the list of Mimic files in the input folder
        mimic_files = [f for f in os.listdir(input_folder) if f.endswith('.mimic')]

        # Process each Mimic file
        for mimic_file in mimic_files:
            working_file_path = os.path.join(root_dir, input_folder, mimic_file)
            target_file_name = mimic_file.replace(".mimic",".{file_ext}")
            target_file_path = os.path.join(root_dir, output_folder, target_file_name)

            target_decode = target_file_path.decode('utf-8')
            source_decode = working_file_path.decode('utf-8')

            # Get file contents
            target_content = target_decode.content
            source_content = source_decode.content

            result = generate_new_content(source_content, target_content)

            logger.info(f"Processing '{working_file_path}': {result.stdout}")
            if result.returncode != 0:
                logger.error(f"Mimic execution failed for '{working_file_path}': {result.stderr}")
                continue

            logger.info(f"Mimic executed successfully for '{working_file_path}'")

        logger.info("Generated files in output directory:")
        log_files_in_directory(output_path)
        
        # Commit and push changes to GitHub based on SKIP_CI
        if skip_ci.lower() == 'yes':
            commit_message += " [no ci]"

        # After all processing is done:
        git_commit_push(output_folder, commit_message, branch_name)

    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")

if __name__ == "__main__":
    main()