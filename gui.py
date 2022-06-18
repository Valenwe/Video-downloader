import PySimpleGUI as sg
import os
import requests
import subprocess
from winreg import *
import youtube_dl
import time
from subprocess import Popen
from threading import Thread

# pip install youtube_dl
# python -m pip install -U yt-dlp

SAVE_PATH = "C:/Users/louis/Downloads"
MODES = ["Download audio", "Download video",
         "Download audio from playlist", "Download video from playlist"]
QUALITY_CHOICE = False

# -=-=-=-=-=-=-=-=-
# YOUTUBE FUNCTIONS
# -=-=-=-=-=-=-=-=-


def get_format(video):
    format2id = {}
    for format in video["formats"]:
        if format["format_note"] == "tiny":
            resolution = str(format["abr"]).split(".")[0] + "K Hz"
        else:
            resolution = format["format_note"]

        format2id[resolution] = {"title": video.get("title"),
                                 "id": format["format_id"], "ext": format["ext"]}

    return format2id


def get_possible_downloads(link, playlist=False):
    with youtube_dl.YoutubeDL({"ignoreerrors": True, "quiet": True}) as ydl:
        informations = ydl.extract_info(link, download=False)

        if playlist:
            if "entries" not in list(informations.keys()):
                error_window("This link is not a valid playlist!")
                return None

            all_formats = []
            for video in informations["entries"]:
                all_formats.append(get_format(video))
            return all_formats
        else:
            if "entries" in list(informations.keys()):
                error_window("This link is from a playlist!")
                return None
            return get_format(informations)


def filter_format(format, type):
    new_format = {}
    for key in format.keys():
        if type == "audio" and key.count("Hz") > 0:
            new_format[key] = format[key]
        elif type == "video" and key.count("Hz") == 0:
            new_format[key] = format[key]

    return new_format


def download_command(link, format, type):
    update_logs("Downloading...")
    code = format["id"]
    title = format["title"] + "." + format["ext"]

    command = "yt-dlp -q -f {} {} -o".format(code, link)
    args = command.split()

    # in case of space in title
    args.append('{}'.format(SAVE_PATH + "/" + title))

    # print(args)

    process = Popen(args)
    while process.poll() is None:
        time.sleep(0.5)

    update_logs("Download finished!")

    if type == "audio":
        update_logs("Converting...")
        convert_audio_to_mp3()


def is_valid_link(link):
    try:
        request = requests.get(link)
        if request.status_code != 200:
            error_window("This link is not valid")
            return False
        else:
            return True
    except:
        error_window("This link is not valid")
        return False


def format2download(formats, type, playlist=False):
    if not playlist:
        if QUALITY_CHOICE:
            format_key = quality_choice_window(
                formats[list(formats.keys())[0]]["title"], list(formats.keys()), type)
            if (format_key == None):
                update_logs("Cancelled by user")
                return
            else:
                choosen_format = formats[format_key]
        else:
            # supposément le meilleur format
            choosen_format = formats[list(formats.keys())[-1]]

        thread = Thread(target=download_command, args=[
                        link, choosen_format, type])
        thread.start()
    else:
        if type == "video":
            command = "yt-dlp -q --ffmpeg-location ./ffmpeg.exe --format bestvideo+bestaudio {} --output".format(
                formats)
        else:
            command = "yt-dlp -q --ffmpeg-location ./ffmpeg.exe --format bestaudio {}  -x --audio-format mp3 --add-metadata --xattrs --embed-thumbnail --output".format(
                formats)

        update_logs("Downloading playlist...")

        args = command.split()
        args.append('{}%(title)s.%(ext)s'.format(SAVE_PATH + "/"))

        # print(args)
        process = Popen(args)
        while process.poll() is None:
            # print("downloading")
            time.sleep(0.5)

        update_logs("Download finished!")
        if type == "audio":
            update_logs("Converting...")
            convert_audio_to_mp3()


def download(link, type, playlist=False):
    if not is_valid_link(link):
        return

    if not playlist:
        update_logs("Collecting streams... ")
        formats = get_possible_downloads(link)

        if formats == None:
            return

        formats = filter_format(formats, type)
        update_logs("Done!")

        format2download(formats, type)
    else:
        format2download(link, type, True)


def get_ffmpeg_command(file, ext, audio=True):
    file_path = SAVE_PATH + "\\" + file
    if audio:
        command = [".\\ffmpeg", "-hide_banner", "-i",
                   file_path, "-vn", "-ab", "128k", "-ar", "44100", "-y",
                   SAVE_PATH + "\\" + file.replace(ext, ".mp3")]
    else:
        command = [".\\ffmpeg", "-i", file_path + ".mp4", "-i", file_path +
                   ".mp3", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac",
                   file_path + "_temp.mp4", "-y", "-hide_banner"]
    return command


def convert_audio_to_mp3():
    if not os.path.isfile(os.getcwd() + "\\ffmpeg.exe"):
        error_window(
            "Error trying to convert to mp3 files! (you need to have FFMPEG.exe in the root folder)")
        return

    for file in os.listdir(SAVE_PATH):
        if os.path.isfile(SAVE_PATH + "\\" + file) and os.path.splitext(file)[-1] in [".webm", ".m4a"]:
            update_logs("Converting " + file + "...")

            command = get_ffmpeg_command(
                file, ext=os.path.splitext(file)[-1], audio=True)
            subprocess.call(command, shell=True)

            os.remove(SAVE_PATH + "\\" + file)
            update_logs("Conversion complete")

# -=-=-=-=-=-=-=-=-
#   GUI FUNCTIONS
# -=-=-=-=-=-=-=-=-


def update_logs(content):
    window["_LOGS_"].update(content)
    window.refresh()


def about_window():
    layout = [
        [sg.Text("This program is using youtube-dl & yt-dlp as a Python modules\nDevelopped by Valenwe")],
        [sg.OK()]
    ]

    window = sg.Window("About", layout)
    event, values = window.read()
    window.close()


def get_default_dl_path():
    with OpenKey(HKEY_CURRENT_USER, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as key:
        return str(QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0])


def result_window(name, header, content, folder):
    layout = [
        [sg.Text(header)],
        [sg.Text(content)],
        [sg.Button("Continue", enable_events=True),
         sg.Button("View folder", enable_events=True)]
    ]

    window = sg.Window(name, layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Continue"):
            break
        elif event == "View folder":
            subprocess.Popen(r"explorer '%s'" % folder)

    window.close()


def error_window(content):
    layout = [
        [sg.Text("Error")],
        [sg.Text(content)],
        [sg.Button("Continue", enable_events=True)]
    ]

    window = sg.Window("Error", layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Continue"):
            break

    update_logs("")
    window.close()


def confirm_window():
    confirm = False
    layout = [
        [sg.Text("This playlist contains more than 100 videos, are you sure to continue?")],
        [sg.Button("Cancel", enable_events=True),
         sg.Button("Continue", enable_events=True)]
    ]

    window = sg.Window("Confirmation", layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            break
        elif event == "Continue":
            confirm = True
            break

    window.close()
    return confirm


def quality_choice_window(title, listbox_content, type):
    format = None

    layout = [
        [sg.Text(title)],
        [sg.Text("Choose a quality for the " + type)],
        [sg.Listbox(listbox_content, enable_events=True,
                    select_mode=sg.LISTBOX_SELECT_MODE_SINGLE, size=(75, 5), key="_CHOICE_")],
        [sg.Button("Cancel", enable_events=True),
         sg.Button("Continue", enable_events=True)]
    ]

    window = sg.Window("Quality Choice", layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            format = None
            break
        elif event == "_CHOICE_":
            format = values["_CHOICE_"][0]
        elif event == "Continue":
            break

    window.close()
    return format


if not os.path.isdir(SAVE_PATH):
    try:
        SAVE_PATH = get_default_dl_path()
    except:
        pass

sg.theme("LightBrown13")
menu_def = [["Menu", ["&About", "&Exit"]]]
layout = [
    [sg.Menu(menu_def, tearoff=False, pad=(150, 1))],
    [sg.Combo(MODES, default_value=MODES[0], key="_CHOICE_", enable_events=True, readonly=True),
     sg.Button(("Quality choice: OFF", "Quality choice: ON")[QUALITY_CHOICE], button_color=(('white', ('red', 'green')[QUALITY_CHOICE])), key="_QUALITY_")],
    [sg.Text("Save path"), sg.Input(SAVE_PATH, readonly=True, key="_SAVEPATH_",
                                    size=(75, 5)), sg.FolderBrowse()],
    [sg.Text("Link"), sg.Input(key="_LINK_", size=(75, 5))],
    [sg.Text(key="_LOGS_", size=(75, 5))],
    [sg.Button("Download", key="_DOWNLOAD_", enable_events=True,
               tooltip="Execute the download")]
]

window = sg.Window("Youtube Downloader", layout)

while True:
    event, values = window.read()

    if event in (sg.WIN_CLOSED, "Exit"):
        break

    elif event == "About":
        about_window()

    elif event == "_QUALITY_":
        if values["_CHOICE_"] in [MODES[0], MODES[1]]:
            QUALITY_CHOICE = not QUALITY_CHOICE
            window["_QUALITY_"].update(("Quality choice: OFF", "Quality choice: ON")[
                QUALITY_CHOICE], button_color=(('white', ('red', 'green')[QUALITY_CHOICE])))

    elif event == "_CHOICE_":
        if values["_CHOICE_"] not in [MODES[0], MODES[1]]:
            QUALITY_CHOICE = False
            window["_QUALITY_"].update(("Quality choice: OFF", "Quality choice: ON")[
                QUALITY_CHOICE], button_color=(('white', ('red', 'green')[QUALITY_CHOICE])))

    elif event == "_DOWNLOAD_":
        SAVE_PATH = values["_SAVEPATH_"]
        link = values["_LINK_"]
        mode = values["_CHOICE_"]

        if link == "":
            error_window("The link is empty")
        else:
            # download audio
            if mode == MODES[0]:
                download(link, "audio")
            # download video
            elif mode == MODES[1]:
                download(link, "video")
            # download audio playlist
            elif mode == MODES[2]:
                download(link, "audio", True)
            # download video playlist
            elif mode == MODES[3]:
                download(link, "video", True)

window.close()
