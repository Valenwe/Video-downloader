import cx_Freeze
import sys

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [cx_Freeze.Executable("youtube_downloader_gui.py", base=base)]

cx_Freeze.setup(
    name="Youtube Downloader",
    options={"build_exe": {"packages": [
        "os", "pytube", "subprocess", "PySimpleGUI", "re", "requests", "winreg"], "include_files": {"ffmpeg.exe"}}},
    executables=executables)
