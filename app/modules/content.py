from typing import List, Dict


def select_top(contents: List[Dict], limit: int = 10, min_score: float = 0.0) -> List[Dict]:
    """Select top N contents by quality score, optionally filtering by minimum score"""
    filtered = [c for c in contents if c.get("quality_score", 0) >= min_score]
    return sorted(filtered, key=lambda x: x.get("quality_score", 0), reverse=True)[:limit]
