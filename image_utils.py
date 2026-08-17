"""
image_utils.py
Encodage des images en base64 pour les intégrer directement dans des cards HTML
(st.image seul ne permet pas d'appliquer object-fit/border-radius/hauteur fixe
de façon cohérente à l'intérieur d'une card stylée en CSS).
"""

import base64
import mimetypes
from functools import lru_cache


@lru_cache(maxsize=32)
def image_en_base64(chemin: str) -> str:
    with open(chemin, "rb") as f:
        data = f.read()
    type_mime, _ = mimetypes.guess_type(chemin)
    type_mime = type_mime or "image/webp"
    return f"data:{type_mime};base64,{base64.b64encode(data).decode()}"