import os
import shutil
import time
import subprocess

SUPPORTED_FORMATS = ['.ts', '.mp4', '.avi', '.mkv', '.mov', '.wmv']

def organize_files(target_suffix=None):
    # Check if target_suffix is provided, if not create generic video folder
    if target_suffix:
        folder_name = f"{target_suffix}_files"
    else:
        folder_name = "video_files"
    
    os.makedirs(folder_name, exist_ok=True)
    
    directories = [d for d in os.listdir() if os.path.isdir(d) and d.startswith('FA0-')]
    
    for dir_name in directories:
        if not target_suffix or dir_name.endswith(target_suffix):
            shutil.move(dir_name, os.path.join(folder_name, dir_name))

def process_video_folders(base_folder="video_files"):
    # Create numbered folders
    temp_dir = os.path.join(base_folder, "temp")
    os.makedirs(temp_dir, exist_ok=True)

    # Create output folder for processed videos
    processed_dir = os.path.join(base_folder, "processed_videos")
    os.makedirs(processed_dir, exist_ok=True)

    # Get and sort directories
    directories = [d for d in os.listdir(base_folder) 
                  if os.path.isdir(os.path.join(base_folder, d)) 
                  and d not in ["temp", "processed_videos"]]
    directories.sort()

    # Collect all video files
    file_counter = 1
    for dir_name in directories:
        dir_path = os.path.join(base_folder, dir_name)
        for file_name in os.listdir(dir_path):
            file_path = os.path.join(dir_path, file_name)
            if os.path.isfile(file_path) and any(file_name.lower().endswith(fmt) for fmt in SUPPORTED_FORMATS):
                ext = os.path.splitext(file_name)[1]
                new_file_name = f"{file_counter:04d}{ext}"
                shutil.copy2(file_path, os.path.join(processed_dir, new_file_name))
                file_counter += 1

def merge_videos(folder_path, output_file="output.mp4"):
    try:
        # Create file list
        video_files = []
        for file in sorted(os.listdir(folder_path)):
            if any(file.lower().endswith(fmt) for fmt in SUPPORTED_FORMATS):
                video_files.append(file)

        # Write file list
        file_list_path = os.path.join(folder_path, "file_list.txt")
        with open(file_list_path, "w", encoding="utf-8") as f:
            f.writelines(f"file '{file}'\n" for file in video_files)

        # Merge videos using FFmpeg with audio transcoding
        ffmpeg_command = [
            "ffmpeg",
            "-f", "concat",
            "-safe", "0",
            "-i", file_list_path,
            "-c:v", "copy",         # Copy video stream as is
            "-c:a", "aac",         # Convert audio to AAC
            "-strict", "experimental",
            os.path.join(folder_path, output_file)
        ]
        
        subprocess.run(ffmpeg_command, check=True)
        print(f"Videos merged successfully into {output_file}")
        
        # Clean up file list
        os.remove(file_list_path)
        
    except Exception as e:
        print(f"An error occurred: {e}")

def main():
    print("Video Organizer and Merger")
    print("1. Process folders with specific suffix(iç kamera ya da dış kamera) (20000100/20000200)")
    print("2. Process all video folders")
    choice = input("Enter your choice (1/2): ")

    if choice == "1":
        suffix = input("Enter the suffix (iç kamera ya da dış kamera) (e.g., 20000100): ")
        organize_files(suffix)
        base_folder = f"{suffix}_files"
    else:
        organize_files()
        base_folder = "video_files"

    process_video_folders(base_folder)
    
    # Merge videos in processed folder
    processed_dir = os.path.join(base_folder, "processed_videos")
    merge_videos(processed_dir)

if __name__ == "__main__":
    main()
