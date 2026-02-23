from typing import List, Dict


def select_top(contents: List[Dict], limit: int = 10) -> List[Dict]:
    """Select top N contents by quality score"""
    # Sort by quality score descending
    sorted_contents = sorted(
        contents,
        key=lambda x: x.get("quality_score", 0),
        reverse=True
    )

    return sorted_contents[:limit]
