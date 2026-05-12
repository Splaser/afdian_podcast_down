# api.py
import re

def parse_album_id(album_url: str) -> str:
    m = re.search(r'/album/([0-9a-f]+)', album_url)
    if m:
        return m.group(1)
    else:
        raise ValueError(f"无法从 URL 解析 album_id: {album_url}")

def get_album_name(album_id: str, session=None, AFDIAN_DOMAIN='ifdian.net'):
    try:
        url = f"https://{AFDIAN_DOMAIN}/api/user/get-album-info"
        resp = session.get(url, params={"album_id": album_id}).json()
        album_title = resp.get("data", {}).get("album", {}).get("title")
        if album_title:
            return album_title
    except Exception as e:
        print("[WARN] 获取专辑信息失败:", e)
    return album_id

def extract_album_list(resp_data):
    albums = []
    has_more = 0
    if isinstance(resp_data, list):
        albums = resp_data
        has_more = 0
        return albums, has_more
    if isinstance(resp_data, dict):
        for key in ["list", "items", "posts"]:
            if key in resp_data and isinstance(resp_data[key], list):
                albums = resp_data[key]
                has_more = resp_data.get("has_more", 0)
                return albums, has_more
        for v in resp_data.values():
            if isinstance(v, list):
                albums = v
                has_more = resp_data.get("has_more", 0)
                return albums, has_more
    if not albums:
        print("[WARN] 当前 cookie 可能失效，或请求过快导致空返回。")
    return albums, has_more