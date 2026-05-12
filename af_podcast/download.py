# download.py
import os
import re
from time import sleep
from random import random
from config import AFDIAN_DOMAIN, POST_OUTPUT_DIR, SLEEP_TIME

from af_podcast.tagging import tag_audio
from af_podcast.ffmpeg_utils import ffmpeg_convert
from af_podcast.api import extract_album_list, get_post_from_page, get_album_name


def download_page(
    albums,
    list_only: bool,
    album_path: str = ".",
    session=None,
    sleep_time: int = SLEEP_TIME,
    write_track_num: bool = False,
):
    os.makedirs(album_path, exist_ok=True)

    total = len(albums)

    for index, album in enumerate(albums):
        track_num = index + 1 if write_track_num else None
        track_total = total if write_track_num else None

        title = album["title"]
        author = album["user"]["name"]
        description = album["content"]
        cover_url = album["audio_thumb"]
        audio_url: str = album["audio"]

        if list_only:
            print(title)
            print(description.replace("\n\n", "\n"))
            print("=" * 40)
        else:
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
            filename = os.path.join(album_path, f"{safe_title}.mp3")

            print(f"正在处理：{title}")

            if os.path.exists(filename):
                print(f"[INFO] 文件已存在，跳过：{filename}")
                continue

            if audio_url.strip() == "":
                print("本条动态没有音频文件，跳过")
                continue

            cover = None

            try:
                cover = session.get(cover_url).content
                print("封面下载完毕.")
            except Exception as e:
                print(f"封面下载失败：{cover_url}", e)

            try:
                if not os.path.exists(filename):
                    mp3 = session.get(audio_url).content

                    with open(filename, "xb") as file:
                        file.write(mp3)

                    print(f"{filename} 下载完成")

                audio = tag_audio(
                    filename,
                    title,
                    author,
                    album_path,
                    cover,
                    description,
                    track_num=track_num,
                    track_total=track_total,
                )

                if not audio:
                    ffmpeg_convert(filename)
                    tag_audio(
                        filename,
                        title,
                        author,
                        album_path,
                        cover,
                        description,
                        track_num=track_num,
                        track_total=track_total,
                    )

                print("已完成.\n")

            except Exception as e:
                print("下载失败", e)

        if index < total - 1:
            sleep(sleep_time + random() * 3)

def get_all_albums(album_id: str, list_only: bool, session=None, sleep_time: int = SLEEP_TIME):
    from af_podcast.api import get_album_name
    album_name = get_album_name(album_id, session)
    safe_album_name = re.sub(r'[<>:"/\\|?*]', '', album_name)
    params = {'album_id': album_id, 'lastRank': 0, 'rankOrder': 'asc', 'rankField': 'rank'}
    while True:
        resp = session.get(f'https://ifdian.net/api/user/get-album-post', params=params).json()
        data = resp.get("data", {})
        albums, has_more = extract_album_list(data)
        if not albums:
            print("[WARN] 当前返回数据为空，跳过本次循环")
            break
        download_page(albums, list_only, album_path=safe_album_name, session=session, write_track_num=True)
        if albums:
            params["lastRank"] = albums[-1].get("rank", params["lastRank"] + 10)
        if not has_more:
            break

def get_latest_n(album_id: str, n: int = 0, session=None) -> list:
    albums = []
    has_more = True
    params = {
        'album_id': album_id,
        'lastRank': 0,
        'rankOrder': 'desc',
        'rankField': 'publish_sn',
    }
    while len(albums) < n and has_more:
        resp = session.get(f'https://ifdian.net/api/user/get-album-post', params=params).json()
        albums_page, has_more = extract_album_list(resp.get("data", {}))
        albums += albums_page
        if albums:
            params['lastRank'] = albums[-1].get('rank', params['lastRank'] + 10)
    return albums[:n]

def download_latest_n(album_id: str, list_only: bool, n: int = 0, session=None, sleep_time: int = SLEEP_TIME):
    album_name = get_album_name(album_id, session)
    safe_album_name = re.sub(r'[<>:"/\\|?*]', '', album_name)
    os.makedirs(safe_album_name, exist_ok=True)
    albums = get_latest_n(album_id, n, session)
    download_page(albums, list_only, album_path=safe_album_name, session=session, sleep_time=sleep_time)


def download_single_post(post_id: str, list_only: bool, session=None):
    """
    下载单条 /p/{post_id} 资源。
    复用 download_page()，避免重新写下载和写 tag 逻辑。
    """
    post = get_post_from_page(post_id, session=session, domain=AFDIAN_DOMAIN)
    download_page(
        [post],
        list_only=list_only,
        album_path=POST_OUTPUT_DIR,
        session=session,
    )