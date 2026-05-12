# tagging.py
import eyed3

def tag_audio(filename, title, artist, album, cover=None, description=""):
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
    if cover:
        audio.tag.images.set(3, cover, "image/jpeg")
    audio.tag.save()
    return True