import os
import logging
import re
import subprocess
import datetime
from pathlib import Path
import shutil

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def setup_git():
    """Configure Git for operation."""
    subprocess.run(["git", "config", "--global", "--add", "safe.directory", "/github/workspace"])
    
    # Set Git user credentials
    git_username = os.environ.get('INPUT_GIT_USERNAME', 'github-actions[bot]')
    git_email = os.environ.get('INPUT_GIT_EMAIL', 'github-actions[bot]@users.noreply.github.com')
    subprocess.run(["git", "config", "--global", "--add", "user.email", git_email])
    subprocess.run(["git", "config", "--global", "--add", "user.name", git_username])
    
    # Example of adding files to Git
    try:
        result = subprocess.run(["git", "add", "."], capture_output=True, text=True, cwd="/github/workspace")
        if result.returncode != 0:
            raise RuntimeError(f"Failed to add files: {result.stderr}")
    except Exception as e:
        logger.error(f"Git error occurred: {e}")

def log_files_in_directory(directory):
    """Logs all files in the specified directory."""
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            log_files_in_directory(item_path)
        else:
            logger.info(f"  - {item}, Size: {os.path.getsize(item_path)} bytes")

def git_commit_push(commit_message, branch_name=None):
    """Commit and push changes to GitHub."""
    github_token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY")
    
    # Check if there are changes to commit
    status = subprocess.run(["git", "status", "--porcelain"], capture_output=True, text=True, check=True)
    
    if status.stdout.strip():
        logger.info("Changes detected, committing...")
        # There are changes to commit
        subprocess.run(["git", "add", "."], check=True)
        subprocess.run(["git", "commit", "-m", commit_message], check=True)
        
        # Create a unique branch for each update
        timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
        new_branch = f"mimic-update-{timestamp}"
        
        # Create and checkout the new branch
        subprocess.run(["git", "checkout", "-b", new_branch], check=True)
        
        # Push to the new branch
        push_url = f"https://x-access-token:{github_token}@github.com/{repo}.git"
        subprocess.run(["git", "push", push_url, new_branch], check=True)
        
        logger.info(f"Changes pushed to new branch: {new_branch}")
        
        # If you want to create a PR automatically, you'd need to use the GitHub API here
    else:
        logger.info("No changes to commit.")

def generate_new_content(source_content, target_content, start_tag, end_tag):
    """Generate new content by replacing the marked section"""
    pattern = f"{start_tag}[\\s\\S]+?{end_tag}"
    replacement = f"{start_tag}\n{source_content}\n{end_tag}"
    
    # Check if the pattern exists in the target content
    if re.search(pattern, target_content):
        return re.sub(pattern, replacement, target_content)
    else:
        logger.warning(f"Pattern not found in target content. Tags may be malformed.")
        return target_content

def get_template_identifier(mimic_file):
    """Extract an identifier from the mimic filename to use in tags."""
    # Remove .mimic extension and convert to uppercase for the tag
    identifier = os.path.splitext(mimic_file)[0].upper()
    return identifier

def find_files_with_extensions(directory, extensions):
    """Find all files with the specified extensions in the directory and its subdirectories."""
    matching_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if any(file.endswith(f".{ext}") for ext in extensions):
                matching_files.append(os.path.join(root, file))
    return matching_files

def ensure_directory_exists(directory_path):
    """Ensure that a directory exists, creating it if necessary."""
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        logger.info(f"Created directory: {directory_path}")

def main():
    """Execute the Mimic Processing Workflow."""
    try:
        # Change working directory to /workspace
        os.chdir("/github/workspace")

        input_folder = os.environ['INPUT_INPUT_FOLDER']
        output_folder = os.environ['INPUT_OUTPUT_FOLDER']
        branch_name = os.getenv("INPUT_BRANCH_NAME") 
        commit_message = os.environ.get('INPUT_COMMIT_MESSAGE', '🤖 - Updated via Markdown Mimic')
        skip_ci = os.environ.get('INPUT_SKIP_CI', 'yes')
        
        # New parameter: overwrite_original (1 = overwrite in place, 0 = output to output_folder)
        overwrite_original = os.environ.get('INPUT_OVERWRITE_ORIGINAL', '0')
        overwrite_original = overwrite_original.strip() == '1'
        
        # Get file extensions as a comma-separated list and convert to a list
        file_exts_str = os.environ.get('INPUT_FILE_EXTS', 'md')
        file_exts = [ext.strip() for ext in file_exts_str.split(',')]
        
        root_dir = '/github/workspace/'

        # Set up git configuration
        setup_git()

        # Remove leading and trailing slashes, and leading periods.
        input_folder = re.sub(r'^/|/$', '', input_folder)
        output_folder = re.sub(r'^/|/$', '', output_folder)
        
        # Clean the extensions (remove leading dots)
        file_exts = [re.sub(r'^\.+', '', ext) for ext in file_exts]

        # Log the resolved input/output paths and settings
        logger.info(f"SRCFOLDER (Input): {input_folder}")
        logger.info(f"DSTFOLDER (Output): {output_folder}")
        logger.info(f"File Extensions: {file_exts}")
        logger.info(f"Overwrite Original: {overwrite_original}")
        logger.info(f"Skip CI: {skip_ci}")

        # Define the full paths
        input_path = os.path.join(root_dir, input_folder)
        output_path = os.path.join(root_dir, output_folder)

        # Check if the input folder exists
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input directory '{input_folder}' does not exist.")
        
        # If not overwriting, ensure output directory exists
        if not overwrite_original:
            ensure_directory_exists(output_path)

        logger.info("Logging contents of the input folder:")
        for filename in os.listdir(input_path):
            logger.info(f"  - {filename}")

        # Get the list of Mimic files in the input folder
        mimic_files = [f for f in os.listdir(input_path) if f.endswith('.mimic')]

        # Find source files to process - always look in the root directory, excluding output folder
        source_files = find_files_with_extensions(root_dir, file_exts)
        source_files = [f for f in source_files if not os.path.relpath(f, root_dir).startswith(output_folder)]
        
        logger.info(f"Found {len(source_files)} potential source files to check")
        
        # Process each Mimic file
        for mimic_file in mimic_files:
            mimic_path = os.path.join(input_path, mimic_file)
            
            # Get the identifier for this template
            identifier = get_template_identifier(mimic_file)
            
            # Define the start and end tags for this template
            start_tag = f"<!--MIMIC_{identifier}_START-->"
            end_tag = f"<!--MIMIC_{identifier}_END-->"
            
            logger.info(f"Processing template: {mimic_file} (looking for {start_tag} and {end_tag})")
            
            # Read the source content
            with open(mimic_path) as source_file:
                source_content = source_file.read()
            
            # Track modified files for this template
            modified_files = 0
            
            # Look for the tags in all source files
            for source_path in source_files:
                try:
                    with open(source_path) as source_file:
                        file_content = source_file.read()
                    
                    # Check if the file contains both tags
                    if start_tag in file_content and end_tag in file_content:
                        logger.debug(f"Found matching tags in '{source_path}'")
                        
                        # Generate updated content
                        updated_content = generate_new_content(source_content, file_content, start_tag, end_tag)
                        
                        # Determine where to write the file
                        if overwrite_original:
                            # If we're overwriting originals, check if content changed
                            if updated_content != file_content:
                                with open(source_path, "w") as target_file:
                                    target_file.write(updated_content)
                                logger.debug(f"Updated file in place: '{source_path}'")
                                modified_files += 1
                            else:
                                logger.info(f"No changes needed for '{source_path}'")
                        else:
                            # If not overwriting, determine output path and check if already exists
                            rel_path = os.path.relpath(source_path, root_dir)
                            output_file_path = os.path.join(output_path, rel_path)
                            
                            # Check if output file exists and has same content
                            should_write = True
                            if os.path.exists(output_file_path):
                                try:
                                    with open(output_file_path, 'r') as existing_file:
                                        existing_content = existing_file.read()
                                    if existing_content == updated_content:
                                        logger.debug(f"Output file already exists with same content: '{output_file_path}'")
                                        should_write = False
                                except Exception as e:
                                    logger.warning(f"Could not read existing output file: {e}")
                            
                            # Write to output if needed
                            if should_write:
                                # Ensure the directory structure exists
                                os.makedirs(os.path.dirname(output_file_path), exist_ok=True)
                                
                                # Write the file
                                with open(output_file_path, "w") as output_file:
                                    output_file.write(updated_content)
                                logger.info(f"Created/updated output file: '{output_file_path}'")
                                modified_files += 1
                except Exception as e:
                    logger.error(f"Error processing '{source_path}': {str(e)}")
            
            logger.info(f"Template {mimic_file} updated {modified_files} files")
        
        # Commit and push changes to GitHub based on SKIP_CI
        if skip_ci.lower() == 'yes':
            commit_message += " [no ci]"

        # After all processing is done:
        git_commit_push(commit_message, branch_name)

    except Exception as e:
        logger.error(f"Unexpected Error: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())

if __name__ == "__main__":
    main()