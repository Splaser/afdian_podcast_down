import argparse
import os
from random import randint, random
from time import sleep
import browser_cookie3
import eyed3
import requests
import re



AFDIAN_DOMAIN = 'ifdian.net'
SLEEP_TIME = 8

session = requests.Session()


headers = {
    'authority': AFDIAN_DOMAIN,
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'referer': f'https://{AFDIAN_DOMAIN}/album/c6ae1166a9f511eab22c52540025c377',
    'sec-ch-ua': '" Not A;Brand";v="99", "Chromium";v="100"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Linux"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.75 Safari/537.36',
}


def ffmpeg_convert(infile):
    outfile = infile + ".tmp.mp3"
    ret = os.system(f'ffmpeg -i "{infile}" "{outfile}"')
    if ret == 0:
        os.remove(infile)
        os.rename(outfile, infile)
        return True
    return False


def get_album_name(album_id: str):
    """
    获取专辑标题，用于创建文件夹
    """
    try:
        url = f"https://{AFDIAN_DOMAIN}/api/user/get-album-info"
        resp = session.get(url,
                           params={"album_id": album_id}).json()

        album_title = resp.get("data", {}).get("album", {}).get("title")
        if album_title:
            return album_title
    except Exception as e:
        print("[WARN] 获取专辑信息失败:", e)

    # fallback: 返回 album_id
    return album_id

def download_page(albums, list_only: bool, album_path: str = ".", n: int = -1, session=session):
    os.makedirs(album_path, exist_ok=True)
    for album in albums:
        # 下载n期
        if not n == -1:
            if n > 0:
                n -= 1
            elif n == 0:
                break
        title = album["title"]
        author = album["user"]["name"]
        description = album["content"]
        cover_url = album["audio_thumb"]
        audio_url: str = album["audio"]
        # 是否仅列出
        if list_only:
            print(title)
            print(description.replace("\n\n", "\n"))  # 去除多余空行
            print("="*40)
        else:
            safe_title = re.sub(r'[<>:"/\\|?*]', '', title)
            filename = os.path.join(album_path, f"{safe_title}.mp3")
            print(f"正在处理：{title}")
            # 显式跳过已存在文件
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
                print(f"封面下载失败：{cover_url}")
                print(e)
            try:
                # 没有下载过
                if not os.path.exists(filename):
                    mp3 = session.get(audio_url).content

                    # 删除文件名中的非法字符
                    with open(filename, "xb") as file:
                        file.write(mp3)
                    print(f"{filename} 下载完成")
                audio: eyed3.core.AudioFile = eyed3.load(filename)
                if audio is None and os.path.exists(filename):
                    # 不知道为什么有些是ISO Media, MP4 Base Media v1，eyed3识别不了
                    print("不支持的音频格式，转码中")
                    # 使用ffmpeg转码
                    ffmpeg_convert(filename)

                audio: eyed3.core.AudioFile = eyed3.load(filename)
                if audio.tag is None:
                    audio.initTag()
                audio.tag.artist = author
                audio.tag.title = title
                audio.tag.album = album_path
                audio.tag.comments.set(description)
                if cover:
                    audio.tag.images.set(3, cover, "image/jpeg")
                audio.tag.save()
                print("已完成.\n")
            except Exception as e:
                print("下载失败", e)

        sleep(SLEEP_TIME + random()*3)


def extract_album_list(resp_data):
    """
    根据不同接口结构提取 album 列表和是否还有更多
    """
    albums = []
    has_more = 0

    # 直接是列表
    if isinstance(resp_data, list):
        albums = resp_data
        has_more = 0
        return albums, has_more

    # 如果是字典
    if isinstance(resp_data, dict):
        # 常见字段
        for key in ["list", "items", "posts"]:
            if key in resp_data and isinstance(resp_data[key], list):
                albums = resp_data[key]
                has_more = resp_data.get("has_more", 0)
                return albums, has_more
        # fallback: dict value 本身是 list
        for v in resp_data.values():
            if isinstance(v, list):
                albums = v
                has_more = resp_data.get("has_more", 0)
                return albums, has_more

    if not albums:
        print("[WARN] 当前 cookie 可能失效，或请求过快导致空返回。请刷新浏览器或稍后重试。")
        
    return albums, has_more


def get_all_albums(album_id: str, list_only: bool):
    params = {'album_id': album_id, 'lastRank': 0, 'rankOrder': 'asc', 'rankField': 'rank'}
    album_name = get_album_name(album_id)
    safe_album_name = re.sub(r'[<>:"/\\|?*]', '', album_name)
    while True:
        resp = session.get(f'https://{AFDIAN_DOMAIN}/api/user/get-album-post',
                           headers=headers, params=params).json()
        data = resp.get("data", {})

        albums, has_more = extract_album_list(data)
        if not albums:
            print("[WARN] 当前返回数据为空，跳过本次循环")
            break

        download_page(albums, list_only, album_path=safe_album_name)

        if albums:
            params["lastRank"] = albums[-1].get("rank", params["lastRank"] + 10)

        if not has_more:
            break


# 获取倒数第n期节目
def get_latest_n(album_id: str, n: int = 0) -> list:
    albums = []
    has_more = True
    params = {
        'album_id': album_id,
        'lastRank': 0,
        'rankOrder': 'desc',
        'rankField': 'publish_sn',
    }
    while len(albums) < n and has_more:
        resp = session.get(f'https://{AFDIAN_DOMAIN}/api/user/get-album-post',
                           headers=headers, params=params).json()
        albums_page, has_more = extract_album_list(resp.get("data", {}))
        albums += albums_page
        if albums:
            params['lastRank'] = albums[-1].get('rank', params['lastRank'] + 10)

        sleep(SLEEP_TIME + random()*3)
    return albums[:n]


# 下载倒数n期节目
def download_latest_n(album_id: str, list_only: bool, n: int = 0):
    # 获取专辑名
    album_name = get_album_name(album_id)
    safe_album_name = re.sub(r'[<>:"/\\|?*]', '', album_name)
    os.makedirs(safe_album_name, exist_ok=True)

    # 下载倒数 n 期节目
    albums = get_latest_n(album_id, n)
    download_page(albums, list_only, album_path=safe_album_name)


def get_authenticated_session(browser='firefox', domain=AFDIAN_DOMAIN):
    if browser.lower() == 'firefox':
        cj = browser_cookie3.firefox(domain_name=domain)
    elif browser.lower() == 'chrome':
        cj = browser_cookie3.chrome(domain_name=domain)
    else:
        raise ValueError('Unsupported browser')

    session = requests.Session()
    session.cookies.update(cj)
    return session

def parse_album_id(album_url: str) -> str:
    """
    从完整 URL 提取 album_id
    """
    m = re.search(r'/album/([0-9a-f]+)', album_url)
    if m:
        return m.group(1)
    else:
        raise ValueError(f"无法从 URL 解析 album_id: {album_url}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="爱发电播客下载")
    parser.add_argument("--id", type=str, help="URL里的id")
    parser.add_argument("--url", type=str, help="完整 album URL，自动解析 ID")
    parser.add_argument("--list", action="store_true", help="仅列出，不下载")
    parser.add_argument("--latest", metavar="n", type=int, default=None, help="下载最新n期")
    parser.add_argument("--browser", type=str, default="firefox", help="选择浏览器: firefox 或 chrome")
    args = parser.parse_args()

    if args.url:
        album_id = parse_album_id(args.url)
    elif args.id:
        album_id = args.id
    else:
        parser.error("请提供 --id 或 --url 参数")

    # 全局 session 初始化
    session = get_authenticated_session(browser=args.browser, domain=AFDIAN_DOMAIN)
    # for c in session.cookies:
    #     print(c.name, c.value[:20])
    # 先更新全局 headers
    session.headers.update(headers)
    print(f"[INFO] {args.browser.capitalize()} cookies loaded.")

    session.headers.update({
        "referer": f"https://{AFDIAN_DOMAIN}/album/{album_id}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:150.0) Gecko/20100101 Firefox/150.0",
        "Accept": "application/json, text/plain, */*",
    })

    if args.latest:
        download_latest_n(album_id, args.list, args.latest)
    else:
        # 默认下载全部
        get_all_albums(album_id, args.list)
