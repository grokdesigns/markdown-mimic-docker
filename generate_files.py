import os
import random
import string
import argparse
from pathlib import Path

def random_string(length=10):
    """Generate a random string of specified length."""
    return ''.join(random.choices(string.ascii_lowercase, k=length))

def random_content(min_length=100, max_length=1000):
    """Generate random text content."""
    paragraphs = []
    num_paragraphs = random.randint(1, 5)
    
    for _ in range(num_paragraphs):
        paragraph_length = random.randint(min_length // num_paragraphs, max_length // num_paragraphs)
        words = []
        while len(' '.join(words)) < paragraph_length:
            word_length = random.randint(2, 12)
            words.append(random_string(word_length))
        paragraphs.append(' '.join(words))
    
    return '\n\n'.join(paragraphs)

def create_random_file(directory, extensions, mimic_tags=None, force_tags=False):
    """Create a random file with specified extensions and possibly mimic tags."""
    # Choose a random extension
    ext = random.choice(extensions)
    filename = f"{random_string(8)}.{ext}"
    filepath = os.path.join(directory, filename)
    
    content = random_content()
    has_tags = False
    
    # Add mimic tags if it's a text file and we're either forcing tags or by random chance
    if mimic_tags and (ext in ['md', 'txt']) and (force_tags or random.random() < 0.3):
        mimic_tag = random.choice(mimic_tags)
        start_tag, end_tag = mimic_tag
        
        # Insert tags randomly in the content
        parts = content.split('\n\n')
        if len(parts) > 1:
            insert_index = random.randint(0, len(parts) - 1)
            # Simple placeholder content without referencing the tag name
            tag_content = f"{start_tag}\nThis is placeholder content that will be replaced.\n{end_tag}"
            parts.insert(insert_index, tag_content)
            content = '\n\n'.join(parts)
        else:
            content = f"{content}\n\n{start_tag}\nThis is placeholder content that will be replaced.\n{end_tag}"
        
        has_tags = True
        print(f"Created {filepath} with {start_tag}")
    else:
        print(f"Created {filepath}")
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    return filepath, ext, has_tags

def create_directory_tree(root_dir, max_depth=3, max_breadth=5):
    """Create a directory tree without files."""
    os.makedirs(root_dir, exist_ok=True)
    all_dirs = [root_dir]
    
    # Generate directory structure first
    current_dirs = [root_dir]
    for depth in range(max_depth):
        new_dirs = []
        for current_dir in current_dirs:
            # Create between 1 and max_breadth subdirectories
            num_subdirs = random.randint(1, max_breadth)
            for _ in range(num_subdirs):
                subdir_name = random_string(5)
                subdir_path = os.path.join(current_dir, subdir_name)
                os.makedirs(subdir_path, exist_ok=True)
                new_dirs.append(subdir_path)
                all_dirs.append(subdir_path)
        current_dirs = new_dirs
        if not new_dirs:  # If no new directories were created, break the loop
            break
    
    return all_dirs

def create_directory_structure_with_files(root_dir, total_files, min_text_files=10, max_depth=3, max_breadth=5):
    """Create a random directory structure with a fixed number of files."""
    # List of file extensions to choose from
    extensions = ['md', 'txt', 'py', 'js', 'css', 'html', 'json', 'yaml', 'xml']
    
    # List of mimic tags to include
    mimic_tags = [
        ('<!--MIMIC_DISCLAIMER_START-->', '<!--MIMIC_DISCLAIMER_END-->'),
        ('<!--MIMIC_GREY-FOX_START-->', '<!--MIMIC_GREY-FOX_END-->'),
        ('<!--MIMIC_PROJECT-X_START-->', '<!--MIMIC_PROJECT-X_END-->'),
        ('<!--MIMIC_README_START-->', '<!--MIMIC_README_END-->')
    ]
    
    # First create the directory structure
    all_dirs = create_directory_tree(root_dir, max_depth, max_breadth)
    
    # Then distribute the files across directories
    files_created = 0
    text_files_with_tags = 0
    
    # First, ensure we have minimum number of text files with tags
    while text_files_with_tags < min_text_files and files_created < total_files:
        target_dir = random.choice(all_dirs)
        # Force create a text file with tags
        filepath, ext, has_tags = create_random_file(
            target_dir, 
            ['md', 'txt'],  # Only text extensions
            mimic_tags,
            force_tags=True  # Force tags
        )
        files_created += 1
        text_files_with_tags += 1
    
    # Then create the rest of the files randomly
    while files_created < total_files:
        target_dir = random.choice(all_dirs)
        filepath, ext, has_tags = create_random_file(target_dir, extensions, mimic_tags)
        files_created += 1
        if has_tags:
            text_files_with_tags += 1
    
    return files_created, text_files_with_tags

def main():
    parser = argparse.ArgumentParser(description='Generate a fake directory structure with mimic tags.')
    parser.add_argument('--root', default='fake_project', help='Root directory for the fake structure')
    parser.add_argument('--depth', type=int, default=3, help='Maximum directory depth')
    parser.add_argument('--breadth', type=int, default=4, help='Maximum subdirectories per directory')
    parser.add_argument('--files', type=int, default=50, help='Total number of files to create')
    parser.add_argument('--min-tag-files', type=int, default=10,
                        help='Minimum number of text files with MIMIC tags')
    
    args = parser.parse_args()
    
    # Clear existing directory if it exists
    if os.path.exists(args.root):
        import shutil
        shutil.rmtree(args.root)
    
    # Create the project structure with specified number of files
    total_files, files_with_tags = create_directory_structure_with_files(
        args.root,
        args.files,
        min_text_files=args.min_tag_files,
        max_depth=args.depth,
        max_breadth=args.breadth
    )
    
    print(f"\nFake project structure created at: {args.root}")
    print(f"Total files created: {total_files}")
    print(f"Files with MIMIC tags: {files_with_tags}")

if __name__ == "__main__":
    main()