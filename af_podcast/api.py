# af_podcast/api.py
import html
import json
import re
from typing import Literal, Tuple

from config import AFDIAN_DOMAIN


UrlKind = Literal["album", "post"]


def parse_album_id(album_url: str) -> str:
    """
    从完整 album URL 提取 album_id
    保留旧函数，兼容原调用。
    """
    m = re.search(r"/album/([0-9a-f]+)", album_url)
    if m:
        return m.group(1)

    raise ValueError(f"无法从 URL 解析 album_id: {album_url}")


def parse_post_id(post_url: str) -> str:
    """
    从 /p/{post_id} URL 提取 post_id
    """
    m = re.search(r"/p/([0-9a-f]+)", post_url)
    if m:
        return m.group(1)

    raise ValueError(f"无法从 URL 解析 post_id: {post_url}")


def parse_input_url(url: str) -> Tuple[UrlKind, str]:
    """
    自动识别 URL 类型：
    - https://ifdian.net/album/{album_id}
    - https://ifdian.net/p/{post_id}
    """
    if re.search(r"/album/[0-9a-f]+", url):
        return "album", parse_album_id(url)

    if re.search(r"/p/[0-9a-f]+", url):
        return "post", parse_post_id(url)

    raise ValueError(f"不支持的 URL 格式: {url}")


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

    if isinstance(resp_data, list):
        return resp_data, 0

    if isinstance(resp_data, dict):
        for key in ["list", "items", "posts"]:
            if key in resp_data and isinstance(resp_data[key], list):
                albums = resp_data[key]
                has_more = resp_data.get("has_more", 0)
                return albums, has_more

        for value in resp_data.values():
            if isinstance(value, list):
                albums = value
                has_more = resp_data.get("has_more", 0)
                return albums, has_more

    print("[WARN] 当前 cookie 可能失效，或请求过快导致空返回。")
    return albums, has_more


def _decode_json_string(raw: str) -> str:
    """
    把页面里类似 https:\\/\\/xxx 或 unicode 转义的字符串解出来。
    """
    if raw is None:
        return ""

    raw = html.unescape(raw)

    try:
        return json.loads(f'"{raw}"')
    except Exception:
        return raw.replace("\\/", "/")


def _regex_json_field(text: str, key: str) -> str:
    """
    从 HTML / 内嵌 JSON 中粗暴提取字段。
    适合先做最小兼容，不强依赖某个 API endpoint。
    """
    pattern = rf'"{re.escape(key)}"\s*:\s*"((?:\\.|[^"\\])*)"'
    m = re.search(pattern, text)
    if not m:
        return ""

    return _decode_json_string(m.group(1))


def _extract_user_name(text: str) -> str:
    """
    尝试从 user.name / name 字段里找作者。
    页面结构可能变化，所以这里做 fallback。
    """
    m = re.search(
        r'"user"\s*:\s*\{.*?"name"\s*:\s*"((?:\\.|[^"\\])*)"',
        text,
        re.S,
    )
    if m:
        return _decode_json_string(m.group(1))

    name = _regex_json_field(text, "name")
    return name or "unknown"


def get_post_from_page(post_id: str, session, domain: str = AFDIAN_DOMAIN) -> dict:
    """
    读取 /p/{post_id} 页面，把单条 post 包装成 download_page() 可消费的 album item 结构。

    返回结构：
    {
        "title": ...,
        "user": {"name": ...},
        "content": ...,
        "audio_thumb": ...,
        "audio": ...
    }
    """
    if session is None:
        raise ValueError("get_post_from_page() 需要传入已认证的 session")

    url = f"https://{domain}/p/{post_id}"
    resp = session.get(url)
    resp.raise_for_status()

    text = resp.text

    title = _regex_json_field(text, "title")
    content = _regex_json_field(text, "content")
    audio = _regex_json_field(text, "audio")
    audio_thumb = _regex_json_field(text, "audio_thumb")
    author = _extract_user_name(text)

    # 有些页面可能不用 audio_thumb，而是 thumb / cover 字段
    if not audio_thumb:
        audio_thumb = _regex_json_field(text, "thumb") or _regex_json_field(text, "cover")

    if not title:
        title = post_id

    if not audio:
        print("[WARN] 当前 /p/ 页面没有解析到 audio 字段，可能是 cookie 权限不足或页面结构变化。")

    return {
        "title": title,
        "user": {
            "name": author,
        },
        "content": content,
        "audio_thumb": audio_thumb,
        "audio": audio,
    }