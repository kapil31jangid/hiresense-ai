import re
from typing import List, Dict, Tuple, Optional

_SKILL_ALIASES: Dict[str, Tuple[str, ...]] = {
    "python": ("python", "python3", "python 3"),
    "fastapi": ("fastapi", "fast api"),
    "postgresql": ("postgresql", "postgres", "postgreSQL", "psql"),
    "spacy": ("spacy", "spaCy"),
    "faiss": ("faiss", "facebook ai similarity search"),
    "react": ("react", "react.js", "reactjs"),
    "next.js": ("next.js", "nextjs", "next js"),
    "docker": ("docker", "containerization", "containers"),
    "aws": ("aws", "amazon web services"),
    "distributed_systems": ("distributed systems", "distributed system", "distributed architecture"),
    "machine_learning": ("machine learning", "ml"),
    "nlp": ("nlp", "natural language processing"),
}

def normalize_skill(skill_text: str) -> Optional[str]:
    """Matches a skill string to its canonical skill name if it matches an alias synonym."""
    lowered = skill_text.strip().lower()
    for canonical, aliases in _SKILL_ALIASES.items():
        if lowered == canonical.lower():
            return canonical
        for alias in aliases:
            if lowered == alias.lower():
                return canonical
    return None

def find_skills_in_text(source_text: str) -> List[str]:
    """Searches a block of text for skill aliases and returns a list of matching canonical names."""
    found: List[str] = []
    lowered = source_text.lower()
    for canonical_skill, aliases in _SKILL_ALIASES.items():
        for alias in aliases:
            pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
            if re.search(pattern, lowered):
                if canonical_skill not in found:
                    found.append(canonical_skill)
                break
    return found
