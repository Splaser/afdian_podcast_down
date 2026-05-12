# af_podcast/tagging.py
import eyed3


def tag_audio(
    filename,
    title,
    artist,
    album,
    cover=None,
    description="",
    track_num=None,
    track_total=None,
):
    audio = eyed3.load(filename)

    if audio is None:
        print("不支持的音频格式，可能需要转码")
        return False

    if audio.tag is None:
        audio.initTag()

    audio.tag.artist = artist
    audio.tag.title = title
    audio.tag.album = album
    audio.tag.comments.set(description)

    if track_num is not None:
        if track_total is not None:
            audio.tag.track_num = (track_num, track_total)
        else:
            audio.tag.track_num = track_num

    if cover:
        audio.tag.images.set(3, cover, "image/jpeg")

    audio.tag.save()
    return True