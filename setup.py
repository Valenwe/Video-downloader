import cx_Freeze
import sys

base = None
if sys.platform == 'win32':
    base = 'Win32GUI'

executables = [cx_Freeze.Executable("new_gui.py", base=base)]

cx_Freeze.setup(
    name="Youtube Downloader",
    options={"build_exe": {"packages": [
        "os", "subprocess", "PySimpleGUI", "youtube_dl", "requests", "winreg", "threading", "time"], "include_files": {"ffmpeg.exe"}}},
    executables=executables)
