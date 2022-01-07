import base64
import re
from pathlib import Path
from subprocess import CREATE_NEW_CONSOLE, Popen
from sys import argv

import ffmpeg
import PySimpleGUI as sg

PREVIEW_SIZE = (960, 540)
FRAMES = 10

RESOLUTIONS = {
    "HD": (1280, 720),
    "Full HD": (1920, 1080),
    "Quad HD": (2560, 1440),
}


def generate_preview(file: Path, time: float):
    return (
        ffmpeg.input(file, ss=time)
        .filter("scale", *PREVIEW_SIZE)
        .output("pipe:", vframes=1, format="image2", vcodec="png")
        .run(capture_stdout=True, quiet=True)
    )[0]


def update_preview(file: Path, time: float, window: sg.Window):
    window["-PREVIEW-"].update(generate_preview(file, time))


def transcode(file: Path, start, end, crf, framerate, width, height):
    new_filename = file.stem + "_smol" + file.suffix
    i = ffmpeg.input(file, ss=start, t=end - start)
    video = i.video.filter("scale", width, height)
    audio = i.audio
    command = (
        ffmpeg.output(
            video,
            audio,
            new_filename,
            crf=crf,
            r=framerate,
            vcodec="libx264",
            acodec="copy",
        )
        .overwrite_output()
        .compile()
    )
    Popen(command, creationflags=CREATE_NEW_CONSOLE)


file = Path(argv[1])
frame_num = 5

probe = ffmpeg.probe(file)
video_stream = next(
    (stream for stream in probe["streams"] if stream["codec_type"] == "video"), None
)

sg.theme("DarkAmber")  # Add a touch of color
# All the stuff inside your window.

validate_inputs_time = []
validate_inputs_integer = [
    "-CRF-",
    "-FRAMERATE-",
    "-RESOLUTION_HORIZONTAL-",
    "-RESOLUTION_VERTICAL-",
]
validate_inputs_float = [
    "-START-",
    "-END-",
]


def validate_integer(text):
    result = re.match(r"\d+", text)
    return False if result is None or result.group() != text else True


def validate_float(text):
    result = re.match(r"\d+(?:\.\d*)?", text)
    return False if result is None or result.group() != text else True


VIDEO_RANGE = (0, round(float(video_stream["duration"]), 1))

old = {
    "-CRF-": "21",
    "-FRAMERATE-": "30",
    "-RESOLUTION_HORIZONTAL-": "1920",
    "-RESOLUTION_VERTICAL-": "1080",
    "-STARTSLIDER-": VIDEO_RANGE[0],
    "-START-": VIDEO_RANGE[0],
    "-ENDSLIDER-": VIDEO_RANGE[1],
    "-END-": VIDEO_RANGE[1],
}

cropper_column = [
    [sg.Image(key="-PREVIEW-", size=PREVIEW_SIZE, source=generate_preview(file, 0))],
    [
        sg.Text("Start"),
        sg.Slider(
            orientation="h",
            key="-STARTSLIDER-",
            enable_events=True,
            default_value=old["-STARTSLIDER-"],
            range=(VIDEO_RANGE[0], VIDEO_RANGE[1] - 1),
            size=(90, 10),
            resolution=0.1,
            disable_number_display=True,
        ),
        sg.InputText(
            key="-START-", enable_events=True, default_text=old["-START-"], size=7
        ),
    ],
    [
        sg.Text("End"),
        sg.Slider(
            orientation="h",
            key="-ENDSLIDER-",
            enable_events=True,
            default_value=old["-ENDSLIDER-"],
            range=(VIDEO_RANGE[0] + 1, VIDEO_RANGE[1]),
            size=(90, 10),
            resolution=0.1,
            disable_number_display=True,
        ),
        sg.InputText(
            key="-END-", enable_events=True, default_text=old["-END-"], size=7
        ),
    ],
]

settings_column = [
    [sg.Text("CRF"), sg.InputText(key="-CRF-", default_text=old["-CRF-"], size=3)],
    [
        sg.Text("Framerate"),
        sg.InputText(
            key="-FRAMERATE-",
            default_text=old["-FRAMERATE-"],
            enable_events=True,
            size=3,
        ),
    ],
    [
        sg.Text("Resolution"),
        sg.InputText(
            key="-RESOLUTION_HORIZONTAL-",
            default_text=old["-RESOLUTION_HORIZONTAL-"],
            enable_events=True,
            size=5,
        ),
        sg.Text("x"),
        sg.InputText(
            key="-RESOLUTION_VERTICAL-",
            default_text=old["-RESOLUTION_VERTICAL-"],
            enable_events=True,
            size=5,
        ),
    ],
    [
        sg.Combo(
            list(RESOLUTIONS.keys()),
            enable_events=True,
            key="-RESOLUTION_DROPDOWN-",
        )
    ],
]

layout = [
    [sg.Column(cropper_column), sg.VSeperator(), sg.Column(settings_column)],
    [
        sg.Button(
            button_text="Transcode",
            key="-TRANSCODE-",
            enable_events=True,
        )
    ],
]

# Create the Window
window = sg.Window("Window Title", layout)

# Event Loop to process "events" and get the "values" of the inputs
while True:
    event, values = window.read()
    if (
        event == sg.WIN_CLOSED or event == "Cancel"
    ):  # if user closes window or clicks cancel
        break
    if event in validate_inputs_integer:
        element, text = window[event], values[event]
        if validate_integer(text):
            old[event] = text
        else:
            element.update(old[event])
            continue
    if event in validate_inputs_float:
        element, text = window[event], values[event]
        if validate_float(text):
            old[event] = text
        else:
            element.update(old[event])
            continue

    if event == "-START-":
        if VIDEO_RANGE[0] <= float(values["-START-"]) < VIDEO_RANGE[1]:
            window["-STARTSLIDER-"].update(float(values["-START-"]))
            update_preview(file, float(values["-START-"]), window)
        elif float(values["-START-"]) < VIDEO_RANGE[0]:
            window["-START-"].update(VIDEO_RANGE[0])
            window["-STARTSLIDER-"].update(VIDEO_RANGE[0])
            update_preview(file, VIDEO_RANGE[0], window)
        elif VIDEO_RANGE[1] <= float(values["-START-"]):
            window["-START-"].update(VIDEO_RANGE[1])
            window["-STARTSLIDER-"].update(VIDEO_RANGE[1])
            update_preview(file, VIDEO_RANGE[1], window)
    if event == "-END-":
        if VIDEO_RANGE[0] < float(values["-END-"]) <= VIDEO_RANGE[1]:
            window["-ENDSLIDER-"].update(float(values["-END-"]))
            update_preview(file, float(values["-END-"]), window)
        elif float(values["-END-"]) <= VIDEO_RANGE[0]:
            window["-END-"].update(VIDEO_RANGE[0])
            window["-ENDSLIDER-"].update(VIDEO_RANGE[0])
            update_preview(file, VIDEO_RANGE[0], window)
        elif VIDEO_RANGE[1] < float(values["-END-"]):
            window["-END-"].update(VIDEO_RANGE[1])
            window["-ENDSLIDER-"].update(VIDEO_RANGE[1])
            update_preview(file, VIDEO_RANGE[1], window)
    if event == "-STARTSLIDER-":
        window["-START-"].update(float(values["-STARTSLIDER-"]))
        update_preview(file, float(values["-STARTSLIDER-"]), window)
    if event == "-ENDSLIDER-":
        window["-END-"].update(float(values["-ENDSLIDER-"]))
        update_preview(file, float(values["-ENDSLIDER-"]), window)

    if event == "-TRANSCODE-":
        transcode(
            file,
            float(values["-STARTSLIDER-"]),
            float(values["-ENDSLIDER-"]),
            int(values["-CRF-"]),
            int(values["-FRAMERATE-"]),
            int(values["-RESOLUTION_HORIZONTAL-"]),
            int(values["-RESOLUTION_VERTICAL-"]),
        )

    if event == "-RESOLUTION_DROPDOWN-":
        window["-RESOLUTION_HORIZONTAL-"].update(
            RESOLUTIONS[values["-RESOLUTION_DROPDOWN-"]][0]
        )
        window["-RESOLUTION_VERTICAL-"].update(
            RESOLUTIONS[values["-RESOLUTION_DROPDOWN-"]][1]
        )


window.close()
