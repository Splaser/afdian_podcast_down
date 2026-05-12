# af_podcast/api.py
import html
import json
import re
from typing import Any, Literal, Tuple

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

def _find_first_post_dict(obj: Any) -> dict | None:
    """
    从接口返回 JSON 中递归找最像 post 详情的 dict。
    """
    if isinstance(obj, dict):
        keys = set(obj.keys())

        # 爱发电 post 详情一般会包含这些字段中的几个
        if (
            "title" in keys
            or "content" in keys
            or "audio" in keys
            or "audio_thumb" in keys
            or "medias" in keys
            or "media" in keys
        ):
            return obj

        for value in obj.values():
            found = _find_first_post_dict(value)
            if found:
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = _find_first_post_dict(item)
            if found:
                return found

    return None


def _find_audio_url(obj: Any) -> str:
    """
    递归查找音频 URL。
    优先查找明确的 audio/audio_url 字段；
    其次查找 type/media_type 标记为 audio 的 media 对象。
    """
    audio_keys = {
        "audio",
        "audio_url",
        "audioUrl",
        "media_url",
        "mediaUrl",
        "file_url",
        "fileUrl",
        "download_url",
        "downloadUrl",
        "url",
    }

    if isinstance(obj, dict):
        # 1. 明确字段优先
        for key in audio_keys:
            value = obj.get(key)
            if isinstance(value, str) and value.startswith("http"):
                # 避免把封面、头像这种图片 URL 当音频
                lowered = value.lower()
                if not any(x in lowered for x in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
                    return value

        # 2. media 对象里可能有 type/audio 标记
        type_value = str(
            obj.get("type")
            or obj.get("media_type")
            or obj.get("mediaType")
            or obj.get("file_type")
            or ""
        ).lower()

        if "audio" in type_value or "mp3" in type_value or "sound" in type_value:
            for key in ["url", "src", "file_url", "fileUrl", "media_url", "mediaUrl", "download_url"]:
                value = obj.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    return value

        # 3. 递归
        for value in obj.values():
            found = _find_audio_url(value)
            if found:
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = _find_audio_url(item)
            if found:
                return found

    return ""


def _find_thumb_url(obj: Any) -> str:
    """
    递归查找封面图 URL。
    """
    thumb_keys = {
        "audio_thumb",
        "audioThumb",
        "cover",
        "cover_url",
        "coverUrl",
        "thumb",
        "thumbnail",
        "pic",
        "image",
        "image_url",
        "imageUrl",
    }

    if isinstance(obj, dict):
        for key in thumb_keys:
            value = obj.get(key)
            if isinstance(value, str) and value.startswith("http"):
                return value

        for value in obj.values():
            found = _find_thumb_url(value)
            if found:
                return found

    elif isinstance(obj, list):
        for item in obj:
            found = _find_thumb_url(item)
            if found:
                return found

    return ""


def _normalize_post_detail(raw: dict, post_id: str) -> dict:
    """
    把 /api/post/get-detail 返回的 post 详情统一转成 download_page() 能吃的结构。
    """
    title = raw.get("title") or raw.get("name") or post_id
    content = raw.get("content") or raw.get("desc") or raw.get("description") or ""

    user = raw.get("user") or raw.get("author") or {}
    if isinstance(user, dict):
        author = user.get("name") or user.get("user_name") or user.get("userName") or "unknown"
    else:
        author = "unknown"

    audio = (
        raw.get("audio")
        or raw.get("audio_url")
        or raw.get("audioUrl")
        or _find_audio_url(raw)
    )

    audio_thumb = (
        raw.get("audio_thumb")
        or raw.get("audioThumb")
        or raw.get("cover")
        or raw.get("cover_url")
        or raw.get("coverUrl")
        or raw.get("thumb")
        or _find_thumb_url(raw)
    )

    return {
        "title": title,
        "user": {
            "name": author,
        },
        "content": content,
        "audio_thumb": audio_thumb,
        "audio": audio,
    }


def get_post_from_page(post_id: str, session, domain: str = AFDIAN_DOMAIN) -> dict:
    """
    读取 /p/{post_id} 对应的真实接口：
    /api/post/get-detail?post_id=xxx&album_id=

    然后把单条 post 包装成 download_page() 可消费的 album item 结构。
    """
    if session is None:
        raise ValueError("get_post_from_page() 需要传入已认证的 session")

    api_url = f"https://{domain}/api/post/get-detail"

    params = {
        "post_id": post_id,
        "album_id": "",
    }

    try:
        resp = session.get(api_url, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()

        post_like = _find_first_post_dict(data)
        if not post_like:
            print("[WARN] /api/post/get-detail 没找到 post-like 结构")
            return {
                "title": post_id,
                "user": {"name": "unknown"},
                "content": "",
                "audio_thumb": "",
                "audio": "",
            }

        item = _normalize_post_detail(post_like, post_id)

        if item.get("audio"):
            print("[INFO] /p/ 资源通过 /api/post/get-detail 解析成功")
            return item

        print("[WARN] /api/post/get-detail 返回成功，但未解析到 audio")
        print("[WARN] 建议临时打开 debug json，搜索 audio、media、url、file_url、download_url。")

        return item

    except Exception as e:
        print("[WARN] /api/post/get-detail 请求失败:", e)

    # fallback：HTML 解析逻辑
    url = f"https://{domain}/p/{post_id}"
    resp = session.get(url)
    resp.raise_for_status()

    text = resp.text

    title = _regex_json_field(text, "title")
    content = _regex_json_field(text, "content")
    audio = _regex_json_field(text, "audio")
    audio_thumb = _regex_json_field(text, "audio_thumb")
    author = _extract_user_name(text)

    if not audio_thumb:
        audio_thumb = _regex_json_field(text, "thumb") or _regex_json_field(text, "cover")

    if not title:
        title = post_id

    if not audio:
        print("[WARN] 当前 /p/ 页面没有解析到 audio 字段，可能是页面结构变化。")

    return {
        "title": title,
        "user": {
            "name": author,
        },
        "content": content,
        "audio_thumb": audio_thumb,
        "audio": audio,
    }