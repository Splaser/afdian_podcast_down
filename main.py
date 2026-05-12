import argparse
from af_podcast.api import parse_input_url
from af_podcast.session_utils import get_authenticated_session
from af_podcast.download import get_all_albums, download_latest_n, download_single_post
from config import DEFAULT_BROWSER

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="爱发电播客下载")
    parser.add_argument("--id", type=str, help="URL里的id")
    parser.add_argument("--url", type=str, help="完整 URL，支持 /album/{id} 和 /p/{id}")
    parser.add_argument("--list", action="store_true", help="仅列出，不下载")
    parser.add_argument("--latest", metavar="n", type=int, default=None, help="下载最新n期")
    parser.add_argument("--browser", type=str, default=DEFAULT_BROWSER, help="选择浏览器: firefox 或 chrome")
    args = parser.parse_args()

    session = get_authenticated_session(browser=args.browser)

    if args.url:
        url_kind, resource_id = parse_input_url(args.url)

        if url_kind == "album":
            if args.latest:
                download_latest_n(resource_id, args.list, args.latest, session=session)
            else:
                get_all_albums(resource_id, args.list, session=session)

        elif url_kind == "post":
            if args.latest:
                print("[WARN] /p/ 单条资源不支持 --latest 参数，已忽略")
            download_single_post(resource_id, args.list, session=session)

    elif args.id:
        # 兼容旧逻辑：--id 默认仍然视为 album id
        album_id = args.id

        if args.latest:
            download_latest_n(album_id, args.list, args.latest, session=session)
        else:
            get_all_albums(album_id, args.list, session=session)

    else:
        parser.error("请提供 --id 或 --url 参数")