import PySimpleGUI as sg
import os
import re
import requests
import subprocess
from pytube import YouTube
from pytube import Playlist
from winreg import *
import traceback

SAVE_PATH = "C:/Users/louis/Downloads"
MODES = ["Download audio", "Download video",
         "Download audio from playlist", "Download video from playlist"]
QUALITY_CHOICE = False


def about_window():
    layout = [
        [sg.Text("This program is using pytube as a Python module\nCreated by Valenwe")],
        [sg.OK()]
    ]

    window = sg.Window("About", layout)
    event, values = window.read()
    window.close()


def get_default_dl_path():
    with OpenKey(HKEY_CURRENT_USER, 'SOFTWARE\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders') as key:
        return str(QueryValueEx(key, '{374DE290-123F-4565-9164-39C4925E467B}')[0])


def progress_function(stream=None, chunk=None, bytes_remaining=None):
    filesize = stream.filesize
    current = ((filesize - bytes_remaining)/filesize)
    percent = ('{0:.1f}').format(current*100)
    progress = int(50*current)
    status = '█' * progress + '-' * (50 - progress)
    update_logs("_BAR_", '  |{bar}| {percent}%\r'.format(
        bar=status, percent=percent))


def get_ffmpeg_command(file, audio=True):
    file_path = SAVE_PATH + "\\" + file
    if audio:
        command = [".\\ffmpeg", "-hide_banner", "-i",
                   file_path, "-vn", "-ab", "128k", "-ar", "44100", "-y",
                   SAVE_PATH + "\\" + file.replace(".webm", ".mp3")]
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
        if os.path.isfile(SAVE_PATH + "\\" + file) and file.endswith(".webm"):
            update_logs("_LOGS_", "Converting " + file + "...")

            command = get_ffmpeg_command(file, audio=True)
            subprocess.call(command, shell=True)

            os.remove(SAVE_PATH + "\\" + file)
            update_logs("_LOGS_", os.path.splitext(
                file)[0] + ".mp3 ready!")


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


def error_window(content, reset=False):
    if reset:
        update_logs("_LINK_", "")
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

    window.close()
    reset_bar()
    update_logs("_LOGS_", "")


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


def quality_choice_window(listbox_content, type):
    index = -1
    sorted_content = sorted(listbox_content)[::-1]
    for i in range(0, len(sorted_content)):
        if type == "audio":
            sorted_content[i] = str(sorted_content[i]) + " kbps"
        elif type == "video":
            sorted_content[i] = str(sorted_content[i][0]) + \
                " p | " + str(sorted_content[i][1]) + " FPS"

    layout = [
        [sg.Text("Choose a quality for the " + type)],
        [sg.Listbox(sorted_content, enable_events=True,
                    select_mode=sg.LISTBOX_SELECT_MODE_SINGLE, size=(75, 5), key="_CHOICE_")],
        [sg.Button("Cancel", enable_events=True),
         sg.Button("Continue", enable_events=True)]
    ]

    window = sg.Window("Quality Choice", layout)

    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            index = -1
            break
        elif event == "_CHOICE_":
            index = listbox_content.index(
                get_digits(values["_CHOICE_"][0], type))
        elif event == "Continue":
            break

    window.close()
    return index


def update_logs(key, content):
    window[key].update(content)
    window.refresh()


def reset_bar():
    window["_BAR_"].update("")
    window.refresh()


def get_index_best(streams, type):
    if type == "audio":
        max = int(streams[0].abr.replace("kbps", ""))
    elif type == "video":
        max = int(streams[0].resolution.replace("p", ""))

    index = 0
    for i in range(1, len(streams)):
        if type == "audio":
            str_abr = streams[i].abr
            res = int(str_abr.replace("kbps", ""))
        elif type == "video":
            str_res = streams[i].resolution
            res = int(str_res.replace("p", ""))

        if res > max:
            max = res
            index = i

    return index


def get_digits(str, type):
    if type == "audio":
        return int("".join(re.findall("\d+", str)))
    elif type == "video":
        return [int("".join(re.findall("\d+", str.split(" ")[0]))), int("".join(re.findall("\d+", str.split(" ")[1])))]


def get_stream(stream, type):
    if type == "video":
        return ([get_digits(stream.resolution, type), get_digits(stream.fps, type)])
    elif type == "audio":
        return (get_digits(stream.abr, type))


def download(link, type, for_video):

    try:
        request = requests.get(link)
        if request.status_code != 200:
            error_window("This link is not valid", True)
            return
    except:
        error_window("This link is not valid", True)
        return

    try:
        yt = YouTube(link, on_progress_callback=progress_function)
    except:
        error_window("Error trying to find Youtube from the link", True)
        return

    try:
        update_logs("_LOGS_", "Collecting streams... ")
        if type == "video":
            files = yt.streams.filter(
                mime_type="video/mp4", only_video=True)

        elif type == "audio":
            files = yt.streams.filter(only_audio=True)

        update_logs("_LOGS_", "Done!")
    except:
        traceback.print_exc()
        error_window("No video found with that link!")
        return

    if len(files) == 0:
        error_window("No possible files found for this link", True)
        return

    if QUALITY_CHOICE:
        listbox_content = []
        for i in range(0, len(files)):
            listbox_content.append(
                get_stream(files[i], type))

        index = quality_choice_window(listbox_content, type)
        if (index == -1):
            update_logs("_LOGS_", "Cancelled by user")
            return

    else:
        index = get_index_best(files, type)

    try:
        if type == "video":
            update_logs("_LOGS_", "Downloading video... ")
        elif type == "audio":
            update_logs("_LOGS_", "Downloading audio... ")

        if type != "audio" and not for_video and os.path.isfile(SAVE_PATH + "/" + yt.title + ".mp4"):
            os.remove(SAVE_PATH + "/" + yt.title + ".mp4")

        if for_video:
            prefix = "temp_video_"
            if os.path.isfile(SAVE_PATH + "/temp_video_" + yt.title + ".mp4"):
                os.remove(SAVE_PATH + "/temp_video_" + yt.title + ".mp4")
        else:
            prefix = ""

        out_file = yt.streams.get_by_itag(
            files[index].itag).download(SAVE_PATH, filename_prefix=prefix)
    except:
        error_window("Error trying to download the file!")
        return

    base, ext = os.path.splitext(out_file)

    if type == "audio" and for_video:
        new_file = base.split("\\")[0] + "\\" + \
            base.split("\\")[-1][11:] + ".mp3"
        if os.path.isfile(new_file):
            os.remove(new_file)

        os.rename(out_file, new_file)

    update_logs("_LOGS_", "Done!")

    if type == "audio" and not for_video:
        #print("Audio ready " + new_file)
        update_logs("_LOGS_", "Audio ready " + out_file)

    reset_bar()
    return SAVE_PATH + "/" + base.split("\\")[-1]


def download_video(link):
    file_path = download(link, "video", False)
    download(link, "audio", True)

    if len(file_path) > 0:
        update_logs("_LOGS_", "Combining video and audio files...")

        if os.path.isfile(file_path + "_temp.mp4"):
            os.remove(file_path + "_temp.mp4")

        command = get_ffmpeg_command(os.path.basename(file_path), audio=False)

        try:
            subprocess.call(command, shell=True)
            os.remove(file_path + ".mp3")
            os.remove(file_path + ".mp4")
            os.rename(file_path + "_temp.mp4", file_path + ".mp4")
        except:
            error_window(
                "Error trying to convert to mp3 files! (you need to have FFMPEG.exe in the root folder)")
            return

        update_logs("_LOGS_", os.path.splitext(
            os.path.basename(file_path))[0] + ".mp4 ready!")


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
    [sg.Text(key="_BAR_", size=(75, 5))],
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
        QUALITY_CHOICE = not QUALITY_CHOICE
        window["_QUALITY_"].update(("Quality choice: OFF", "Quality choice: ON")[
                                   QUALITY_CHOICE], button_color=(('white', ('red', 'green')[QUALITY_CHOICE])))

    elif event == "_DOWNLOAD_":
        SAVE_PATH = values["_SAVEPATH_"]
        link = values["_LINK_"]
        mode = values["_CHOICE_"]

        if link == "":
            error_window("The link is empty")

        # download audio
        if mode == MODES[0]:
            download(link, "audio", False)
            convert_audio_to_mp3()

        # download video
        elif mode == MODES[1]:
            download_video(link)

        elif mode in (MODES[2], MODES[3]):
            p = Playlist(link)
            try:
                if len(p.video_urls) == 0:
                    error_window(
                        "Error, this playlist does not contain any video!")
                elif len(p.video_urls) > 100:
                    answer = confirm_window()

            except:
                error_window(
                    "Error, this link is not a Youtube playlist or it is private!")

            # download audio playlist
            if mode == MODES[2]:
                for i in range(0, len(p.video_urls)):
                    update_logs("_LOGS_", "[" + str(i+1) + "/" + str(len(p.video_urls)) +
                                "] Downloading " + p.videos[i].title + "... ")
                    download(p.video_urls[i], "audio", False)

                convert_audio_to_mp3()

            # download video playlist
            elif mode == MODES[3]:
                for i in range(0, len(p.video_urls)):
                    update_logs("_LOGS_", "[" + str(i+1) + "/" + str(len(p.video_urls)) +
                                "] Downloading " + p.videos[i].title + "... ")
                    download_video(p.video_urls[i])

window.close()
