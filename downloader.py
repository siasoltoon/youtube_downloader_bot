import os
import yt_dlp


def get_video_data(url):

    ydl_opts = {
        "quiet": False,
        "no_warnings": False,
        "noplaylist": True,

        "extractor_args": {
            "youtube": {
                "player_client": ["ٌWeb"]
            }
        }
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            url,
            download=False
        )

        video_info = {
            "title": info.get("title") or "نامشخص",
            "channel": info.get("channel") or info.get("uploader") or "نامشخص",
            "views": info.get("view_count") or 0,
            "likes": info.get("like_count") or 0,
            "duration": info.get("duration") or 0,
        }

        qualities = {}

        for f in info.get("formats", []):

            height = f.get("height")

            if (
                height
                and f.get("ext") == "mp4"
                and f.get("url")
            ):
                qualities[str(height)] = f["url"]

        qualities = dict(
            sorted(
                qualities.items(),
                key=lambda x: int(x[0]),
                reverse=True
            )
        )

        return video_info, qualities


def download_video(url, quality):

    output_dir = "/tmp/youtube_downloads"

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    output_template = os.path.join(
        output_dir,
        "%(id)s.%(ext)s"
    )

    ydl_opts = {
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,

        "format": (
            f"bestvideo[height<={quality}]"
            f"+bestaudio/"
            f"best[height<={quality}]"
        ),

        "outtmpl": output_template,

        "merge_output_format": "mp4",
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:

        info = ydl.extract_info(
            url,
            download=True
        )

        filename = ydl.prepare_filename(info)

        base, _ = os.path.splitext(filename)

        mp4_file = base + ".mp4"

        if os.path.exists(mp4_file):
            return mp4_file

        return filename
