import gdown
import shutil
import sys
from pydub import AudioSegment
from gtts import gTTS
import os
from moviepy.editor import AudioFileClip, ImageClip
import yt_dlp
import yaml


def generate_part_separator(i):
    tts = gTTS(f"part {i}", lang="en")
    tts.save(os.path.join("partSeparators", f"{i}.mp3"))


def download_drive_mp3(id, output_path):
    url = f"https://drive.google.com/uc?id={id}"
    gdown.download(url, output_path, quiet=True)


def stitch_timestamps(input_path, output_path, time_intervals):
    audio = AudioSegment.from_mp3(input_path)
    res = sum(
        [
            AudioSegment.from_mp3(os.path.join("partSeparators", f"{i + 1}.mp3"))
            + AudioSegment.silent(duration=500)
            + audio[interval[0] * 1000 : interval[1] * 1000]
            + AudioSegment.silent(duration=500)
            for i, interval in enumerate(time_intervals)
        ],
        AudioSegment.empty(),
    )
    res.export(output_path, format="mp3")


def download_youtube_mp3(url, output_path):
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "outtmpl": output_path,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def stitch_sources(input_paths, output_path):
    res = sum(
        [
            AudioSegment.from_mp3(os.path.join("partSeparators", f"{i + 1}.mp3"))
            + AudioSegment.silent(duration=500)
            + AudioSegment.from_mp3(path)
            + AudioSegment.silent(duration=500)
            for i, path in enumerate(input_paths)
        ],
        AudioSegment.empty(),
    )
    res.export(output_path, format="mp3")


def do_audio(title, drive_id, timestamps):
    download_drive_mp3(drive_id, "audio.mp3")
    stitch_timestamps("audio.mp3", "stitched_audio.mp3", timestamps)
    upload_mp3("audio.mp3", f"{title} (Full Audio)")
    upload_mp3("stitched_audio.mp3", title)
    os.remove("audio.mp3")
    os.remove("stitched_audio.mp3")


def do_source(title, urls):
    for i, url in enumerate(urls):
        download_youtube_mp3(url, f"temp_{i}")
    paths = [f"temp_{i}.mp3" for i in range(len(urls))]
    if len(paths) == 1:
        shutil.copy(f"temp_0.mp3", "source.mp3")
    else:
        stitch_sources(paths, "source.mp3")
    upload_mp3("source.mp3", f"{title} (Source)")
    for path in paths:
        os.remove(path)
    os.remove("source.mp3")


def upload_mp3(input_path, title):
    audio = AudioFileClip(input_path)
    image = ImageClip("thumbnail.png").set_duration(audio.duration)
    video = image.set_audio(audio)
    video.write_videofile(
        os.path.join("output", f"{title}.mp4"),
        codec="libx264",
        audio_codec="aac",
        fps=1,
    )


def parse_input(input_path):
    def convert_timestamp(timestamp):
        minutes, seconds = map(int, timestamp.split(":"))
        return minutes * 60 + seconds

    with open(input_path, "r") as f:
        inputs = yaml.safe_load(f.read())
    for input in inputs:
        for i, timestamp in enumerate(input["timestamps"]):
            input["timestamps"][i][0] = convert_timestamp(timestamp[0])
            input["timestamps"][i][1] = convert_timestamp(timestamp[1])
        input["audio_id"] = input["audio_url"].split("/d/")[1].split("/view")[0]
    return inputs


def main():
    if len(sys.argv) < 2 or not os.path.exists(sys.argv[1]):
        print(f"Usage: python3 {sys.argv[0]} <input_path>")
        sys.exit(1)
    if not os.path.exists("partSeparators"):
        os.makedirs("partSeparators")
        for i in range(1, 10):
            generate_part_separator(i)
    if not os.path.exists("output"):
        os.makedirs("output")

    for input in parse_input(sys.argv[1]):
        do_audio(input["title"], input["audio_id"], input["timestamps"])
        do_source(input["title"], input["source_urls"])


if __name__ == "__main__":
    main()
