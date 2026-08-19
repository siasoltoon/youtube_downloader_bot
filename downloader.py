import yt_dlp


def get_video_data(url):

    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
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
