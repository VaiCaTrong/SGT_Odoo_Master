"""The newest approved Content posts of Project XINYANG (text + first image) for the Dashboard Content page (Update_022).

Strictly read-only. "Approved" and "newest" follow the Content KPI: the publications of Project XINYANG that are currently
approved, ordered by the post's Last Reviewed (reviewed_at), newest first. Only the first image of each post is read (the
other media are only counted; videos are never downloaded). Images are re-encoded on the Xinyang server (Pillow, JPEG): a
small one for the card and a larger one for the viewer, so 9 posts stay around 2-3 MB. The same dict is what a saved version
keeps, so the posts still show when social360 is down.
"""
from __future__ import annotations

import base64
import logging
from typing import Any

from . import evidence as ev
from .content import MAX_PUBLICATIONS, _ids, _read_chunks, _relation_id
from .sgt import GbError, PROJECT_MODEL

_logger = logging.getLogger(__name__)
LATEST = 9
TEXT_MAX = 3000
THUMB = (360, 76)      # longest side px, JPEG quality
LARGE = (1280, 80)
POST_MODEL = "sgt.social.post"
MEDIA_MODEL = "sgt.social.post.image"


def _text(value: Any, limit: int) -> str:
    text = value if isinstance(value, str) else ""
    text = text.replace("\r\n", "\n").strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + "…"


def _first_image(service, post_id: int, media: list[dict]) -> tuple[dict | None, str | None]:
    """(image, error): the first image of the post as two JPEG sizes (base64), or an explanation why there is none."""
    first = next((m for m in media if (m.get("media_type") or "image") == "image"), None)
    if first is None:
        return None, None
    try:
        rows = service._call(MEDIA_MODEL, "read", [[first["id"]]], {"fields": ["image"]})
        raw = rows[0].get("image") if isinstance(rows, list) and rows else None
        data = ev._decode(raw)
        ev.sniff(data)
        thumb, _ = ev.render_box(data, *THUMB)
        large, _ = ev.render_box(data, *LARGE)
    except (GbError, ev.EvidenceError) as exc:
        return None, str(exc)[:160]
    return {"thumb": base64.b64encode(thumb).decode(), "large": base64.b64encode(large).decode()}, None


def load_latest(service, count: int = LATEST) -> dict[str, Any]:
    """{"posts": [...], "count": n}; raises GbError (message shown to the admin) when the posts cannot be read / verified."""
    meta = service._call(POST_MODEL, "fields_get", [], {"attributes": ["type"]})
    if not isinstance(meta, dict) or not all(f in meta for f in ("name", "content", "reviewed_at")):
        raise GbError("Model sgt.social.post không có đủ field name / content / reviewed_at; tài khoản dịch vụ cần quyền xem Content.")
    pid = service._project()
    rows = service._call(PROJECT_MODEL, "read", [[pid]], {"fields": ["id", "name", "approved_publication_ids"]})
    if not isinstance(rows, list) or len(rows) != 1 or rows[0].get("name") != "XINYANG":
        raise GbError("Không xác nhận được Project XINYANG khi đọc bài Content.")
    pub_ids = _ids(rows[0].get("approved_publication_ids"), "approved_publication_ids")
    if not pub_ids:
        return {"posts": [], "count": 0}
    pubs = _read_chunks(service, "sgt.social.post.publication", pub_ids, ["id", "post_id", "destination_id"], MAX_PUBLICATIONS)
    post_ids: set[int] = set()
    for pub in pubs.values():
        if _relation_id(pub.get("destination_id")) != pid:
            raise GbError("Publication không thuộc Project XINYANG; từ chối dữ liệu sai Project.")
        post_id = _relation_id(pub.get("post_id"))
        if post_id is None or post_id < 1:
            raise GbError("Publication thiếu liên kết Content gốc.")
        post_ids.add(post_id)
    fields = ["id", "name", "content", "reviewed_at"] + [f for f in ("author_display_name", "create_date") if f in meta]
    posts = service._call(POST_MODEL, "search_read", [[["id", "in", sorted(post_ids)], ["reviewed_at", "!=", False]]],
                          {"fields": fields, "order": "reviewed_at desc, id desc", "limit": count})
    if not isinstance(posts, list):
        raise GbError("SGT không trả về danh sách bài Content hợp lệ.")
    ids = [p["id"] for p in posts if type(p.get("id")) is int]
    media_by_post: dict[int, list[dict]] = {i: [] for i in ids}
    if ids:
        media = service._call(MEDIA_MODEL, "search_read", [[["post_id", "in", ids]]],
                              {"fields": ["id", "post_id", "name", "media_type", "sequence"], "order": "sequence, id"})
        for m in media if isinstance(media, list) else []:
            owner = _relation_id(m.get("post_id"))
            if owner in media_by_post and type(m.get("id")) is int:
                media_by_post[owner].append(m)
    out = []
    for post in posts:
        pid_ = post.get("id")
        if type(pid_) is not int:
            continue
        media = media_by_post.get(pid_, [])
        image, error = _first_image(service, pid_, media)
        videos = [str(m.get("name") or "video")[:80] for m in media if m.get("media_type") == "video"][:3]
        out.append({
            "id": pid_, "title": _text(post.get("name"), 200), "text": _text(post.get("content"), TEXT_MAX),
            "author": _text(post.get("author_display_name"), 120), "reviewed_at": str(post.get("reviewed_at") or ""),
            "created_at": str(post.get("create_date") or ""), "media_count": len(media), "videos": videos,
            "image": image, "image_error": error})
    return {"posts": out, "count": len(out)}


def public_view(data: dict[str, Any]) -> list[dict[str, Any]]:
    """The posts without the image bytes (what the browser gets as JSON; the images come from the image route)."""
    return [{k: v for k, v in p.items() if k != "image"} | {"has_image": bool(p.get("image"))} for p in data.get("posts", [])]


def image_bytes(data: dict[str, Any], post_id: int, size: str) -> bytes | None:
    for post in data.get("posts", []):
        if post.get("id") == post_id and post.get("image") and size in post["image"]:
            try:
                return base64.b64decode(post["image"][size], validate=True)
            except ValueError:
                return None
    return None
