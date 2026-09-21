"""Shared pagination helper."""

import math
from types import SimpleNamespace


def paginate(query, page: int, per_page: int = 25):
    """Return paginated results from a SQLAlchemy query.

    Returns a SimpleNamespace with attributes:
        items        – list of ORM objects for the current page
        total        – total number of matching records
        total_pages  – total number of pages
        page         – current (clamped) page number
        per_page     – page size used
        has_prev     – whether a previous page exists
        has_next     – whether a next page exists
    """
    total = query.count()
    total_pages = max(1, math.ceil(total / per_page))
    page = max(1, min(page, total_pages))

    items = query.offset((page - 1) * per_page).limit(per_page).all()

    return SimpleNamespace(
        items=items,
        total=total,
        total_pages=total_pages,
        page=page,
        per_page=per_page,
        has_prev=page > 1,
        has_next=page < total_pages,
    )

