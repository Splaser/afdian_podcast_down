# af_podcast/api.py
import re

from config import AFDIAN_DOMAIN


def parse_album_id(album_url: str) -> str:
    """
    从完整 album URL 提取 album_id
    """
    m = re.search(r"/album/([0-9a-f]+)", album_url)
    if m:
        return m.group(1)

    raise ValueError(f"无法从 URL 解析 album_id: {album_url}")


def get_album_name(album_id: str, session, domain: str = AFDIAN_DOMAIN) -> str:
    """
    获取专辑标题，用于创建文件夹
    """
    if session is None:
        raise ValueError("get_album_name() 需要传入已认证的 session")

    try:
        url = f"https://{domain}/api/user/get-album-info"
        resp = session.get(url, params={"album_id": album_id}).json()

        album_title = resp.get("data", {}).get("album", {}).get("title")
        if album_title:
            return album_title

    except Exception as e:
        print("[WARN] 获取专辑信息失败:", e)

    return album_id


def extract_album_list(resp_data):
    """
    根据不同接口结构提取 album 列表和是否还有更多
    """
    albums = []
    has_more = 0

    # 直接是列表
    if isinstance(resp_data, list):
        return resp_data, 0

    # 如果是字典
    if isinstance(resp_data, dict):
        # 常见字段
        for key in ["list", "items", "posts"]:
            if key in resp_data and isinstance(resp_data[key], list):
                albums = resp_data[key]
                has_more = resp_data.get("has_more", 0)
                return albums, has_more

        # fallback：dict value 本身是 list
        for value in resp_data.values():
            if isinstance(value, list):
                albums = value
                has_more = resp_data.get("has_more", 0)
                return albums, has_more

    print("[WARN] 当前 cookie 可能失效，或请求过快导致空返回。")
    return albums, has_more