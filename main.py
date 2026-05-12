import argparse
from af_podcast.api import parse_album_id
from af_podcast.session_utils import get_authenticated_session
from af_podcast.download import get_all_albums, download_latest_n
from config import SLEEP_TIME, DEFAULT_BROWSER

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="爱发电播客下载")
    parser.add_argument("--id", type=str, help="URL里的id")
    parser.add_argument("--url", type=str, help="完整 album URL，自动解析 ID")
    parser.add_argument("--list", action="store_true", help="仅列出，不下载")
    parser.add_argument("--latest", metavar="n", type=int, default=None, help="下载最新n期")
    parser.add_argument("--browser", type=str, default=DEFAULT_BROWSER, help="选择浏览器: firefox 或 chrome")
    args = parser.parse_args()

    if args.url:
        album_id = parse_album_id(args.url)
    elif args.id:
        album_id = args.id
    else:
        parser.error("请提供 --id 或 --url 参数")

    session = get_authenticated_session(browser=args.browser)

    if args.latest:
        download_latest_n(album_id, args.list, args.latest, session=session, sleep_time=SLEEP_TIME)
    else:
        get_all_albums(album_id, args.list, session=session, sleep_time=SLEEP_TIME)