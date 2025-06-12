import os
import shutil
import sys
from pathlib import Path

def organize_files(keywords, folder_name):
    """
    Organize files from Downloads to a new folder on Desktop.
    
    Args:
        keywords (str): Comma-separated keywords to match in filenames
        folder_name (str): Name of the folder to create on Desktop and move matching files to
    """
    downloads_path = r"C:\Users\swqwi\Downloads"
    desktop_path = r"C:\Users\swqwi\OneDrive\Desktop"
    
    target_folder = os.path.join(desktop_path, folder_name)
    os.makedirs(target_folder, exist_ok=True)
    
    keyword_list = [k.strip().lower() for k in keywords.split(',')]
    
    moved_files = 0
    for filename in os.listdir(downloads_path):
        file_path = os.path.join(downloads_path, filename)
        if os.path.isdir(file_path) or filename.startswith('.'):
            continue
        filename_lower = filename.lower()
        if any(keyword in filename_lower for keyword in keyword_list):
            try:
                shutil.move(file_path, target_folder)
                print(f"Moved '{filename}' to 'Desktop\\{folder_name}'")
                moved_files += 1
            except Exception as e:
                print(f"Error moving '{filename}': {e}")
    
    print(f"\nDone! Moved {moved_files} files to 'Desktop\\{folder_name}'.")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python organize.py <keywords> <folder_name>")
        print("Example: python organize.py 'comp1110,cs101' 'COMP1110_Lectures'")
        sys.exit(1)
    
    keywords = sys.argv[1]
    folder_name = sys.argv[2]
    
    organize_files(keywords, folder_name)