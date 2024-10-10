import os
import zipfile


def zip_folder(folder_path, output_zip_path):
    with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        # Walk the directory
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                # Create the full filepath
                file_path = os.path.join(root, file)
                # Add file to zip, preserving the folder structure
                zipf.write(file_path, os.path.relpath(file_path, folder_path))
