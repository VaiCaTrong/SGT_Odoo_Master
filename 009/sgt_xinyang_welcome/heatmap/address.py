"""Read-only address normalization for the map area filters (copied from Gearea Report Dashboard v4.16.0); NEVER geocodes."""
from __future__ import annotations

import re
import unicodedata

PROVINCES = [
    "Ha Noi", "Ho Chi Minh", "Sai Gon", "Da Nang", "Hai Phong", "Can Tho",
    "An Giang", "Ba Ria Vung Tau", "Bac Giang", "Bac Kan", "Bac Lieu",
    "Bac Ninh", "Ben Tre", "Binh Dinh", "Binh Duong", "Binh Phuoc", "Binh Thuan",
    "Ca Mau", "Cao Bang", "Dak Lak", "Dak Nong", "Dien Bien", "Dong Nai",
    "Dong Thap", "Gia Lai", "Ha Giang", "Ha Nam", "Ha Tinh", "Hai Duong",
    "Hau Giang", "Hoa Binh", "Hung Yen", "Khanh Hoa", "Kien Giang", "Kon Tum",
    "Lai Chau", "Lam Dong", "Lang Son", "Lao Cai", "Long An", "Nam Dinh",
    "Nghe An", "Ninh Binh", "Ninh Thuan", "Phu Tho", "Phu Yen", "Quang Binh",
    "Quang Nam", "Quang Ngai", "Quang Ninh", "Quang Tri", "Soc Trang",
    "Son La", "Tay Ninh", "Thai Binh", "Thai Nguyen", "Thanh Hoa", "Thua Thien Hue",
    "Hue", "Tien Giang", "Tra Vinh", "Tuyen Quang", "Vinh Long", "Vinh Phuc", "Yen Bai",
]
ALIASES = {"sai gon": "Ho Chi Minh", "tp hcm": "Ho Chi Minh", "tp.hcm": "Ho Chi Minh", "hcm": "Ho Chi Minh", "hanoi": "Ha Noi", "hue": "Hue", "ba ria-vung tau": "Ba Ria Vung Tau"}


def ascii_fold(text: str) -> str:
    value = unicodedata.normalize("NFKD", str(text or ""))
    value = "".join(ch for ch in value if not unicodedata.combining(ch))
    return value.replace("\u0111", "d").replace("\u0110", "D").casefold()


def normalize_address(value: object) -> str:
    if not isinstance(value, str):
        return ""
    value = unicodedata.normalize("NFC", value)
    text = re.sub(r"[\r\n\t]+", ", ", value)
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*,\s*", ", ", text)
    text = re.sub(r"(?:,\s*){2,}", ", ", text).strip(" ,;\t\r\n")
    return "" if ascii_fold(text) in {"", "-", ".", "n/a", "false", "null", "none"} else text


def address_key(raw: str) -> str:
    return ascii_fold(normalize_address(raw))


def province_from_address(raw: str) -> str:
    # Normalize hyphens/Unicode punctuation because Odoo and Goong commonly
    # spell "Ba Ria - Vung Tau" in different ways.
    folded = re.sub(r"[^a-z0-9]+", " ", ascii_fold(normalize_address(raw))).strip()
    if not folded:
        return ""
    padded = " " + folded + " "
    for alias, real in sorted(ALIASES.items(), key=lambda x: len(x[0]), reverse=True):
        cand = re.sub(r"[^a-z0-9]+", " ", ascii_fold(alias)).strip()
        if " " + cand + " " in padded:
            return real
    for value in sorted(PROVINCES, key=len, reverse=True):
        cand = re.sub(r"[^a-z0-9]+", " ", ascii_fold(value)).strip()
        if " " + cand + " " in padded:
            return value
    return ""


DISTRICT_PREFIX = re.compile(r"^(quan|q\.|q |huyen|h\.|thi xa|tx\.?|tx |thanh pho|tp\.?|tp |thi tran|district|thu duc)")
NOT_DISTRICT = re.compile(r"(^(phuong|p\.|p |xa |ward|khu|so |duong|d\.|ngo|hem|kiet|to |ap |thon|lo |kcn|toa|tang)|\d)")


def district_from_address(raw: str) -> str:
    """Quận/huyện/thị xã/TP thuộc tỉnh. Địa chỉ nhập 1 dòng (Street) vẫn tách được:
    ưu tiên đoạn có tiền tố (Q., Quận, Huyện, TX, TP…), nếu không có thì lấy đoạn ngay trước tỉnh/thành
    (vd "…, Hà Đông, Hà Nội" → "Hà Đông")."""
    segs = [seg.strip() for seg in normalize_address(raw).split(",") if seg.strip()]
    while segs and ascii_fold(segs[-1]).replace(" ", "") in {"vietnam"}:
        segs.pop()
    if not segs:
        return ""
    pidx = len(segs)
    for idx in range(len(segs) - 1, -1, -1):
        if province_from_address(segs[idx]):
            pidx = idx
            break
    for seg in reversed(segs[:pidx]):
        folded = ascii_fold(seg)
        if DISTRICT_PREFIX.search(folded) and not province_from_address(seg):
            return seg
    if pidx > 0 and pidx < len(segs):
        prev = segs[pidx - 1]
        if not NOT_DISTRICT.search(ascii_fold(prev)) and len(prev) <= 40:
            return prev
    return ""


def normalized_vietnamese(raw: str) -> str:
    text = normalize_address(raw)
    # Expand only unambiguous prefixes. Avoid replacing letters inside names.
    substitutions = [
        (r"(?i)(?<!\w)P\.?\s*(\d{1,3})(?=\b|,)", lambda m: "Ph\u01b0\u1eddng " + m.group(1)),
        (r"(?i)(?<!\w)Q\.?\s*(\d{1,3})(?=\b|,)", lambda m: "Qu\u1eadn " + m.group(1)),
        (r"(?i)(?<!\w)TP\.?\s*HCM\b", "Th\u00e0nh ph\u1ed1 H\u1ed3 Ch\u00ed Minh"),
        (r"(?i)(?<!\w)TP\.?\s*Vung Tau\b", "Th\u00e0nh ph\u1ed1 V\u0169ng T\u00e0u"),
        (r"(?i)(?<!\w)TP\.?\s*(?=[A-Za-z\u00c0-\u1ef9])", "Th\u00e0nh ph\u1ed1 "),
        (r"(?i)(?<!\w)TX\.?\s*(?=[A-Za-z\u00c0-\u1ef9])", "Th\u1ecb x\u00e3 "),
    ]
    for expression, replacement in substitutions:
        text = re.sub(expression, replacement, text)
    return normalize_address(text)


