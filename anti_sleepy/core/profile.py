import json
from pathlib import Path
from typing import Optional

def profile_exists(path: str = "data/owner_profile.json") -> bool:
    """
    Check if the profile JSON file exists.
    """
    return Path(path).is_file()

def save_profile(profile: dict, path: str = "data/owner_profile.json") -> None:
    """
    Create the data directory if needed and save the profile dictionary 
    as pretty-printed JSON.
    """
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("w", encoding="utf-8") as f:
        json.dump(profile, f, indent=4)

def load_profile(path: str = "data/owner_profile.json") -> Optional[dict]:
    """
    Load the profile dictionary from the JSON file.
    Returns None if the file doesn't exist or holds invalid JSON.
    """
    p = Path(path)
    if not p.is_file():
        return None
        
    try:
        with p.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return None

def delete_profile(path: str = "data/owner_profile.json") -> None:
    """
    Delete the profile JSON file, effectively resetting registration.
    """
    p = Path(path)
    if p.is_file():
        p.unlink()
