"""CS2 item category classification.

Classifies item names into categories based on naming patterns:
knives, gloves, rifles, pistols, SMGs, shotguns, machineguns,
stickers, cases, graffiti, music kits, patches, keys, agents, other.
"""
from __future__ import annotations

from beartype import beartype

# All valid categories
CATEGORIES: tuple[str, ...] = (
    "knife",
    "gloves",
    "rifle",
    "pistol",
    "smg",
    "shotgun",
    "machinegun",
    "sticker",
    "case",
    "graffiti",
    "music_kit",
    "patch",
    "key",
    "agent",
    "other",
)

# Weapon base name -> category
_WEAPON_MAP: dict[str, str] = {
    # Rifles
    "AK-47": "rifle",
    "M4A4": "rifle",
    "M4A1-S": "rifle",
    "AWP": "rifle",
    "SSG 08": "rifle",
    "SCAR-20": "rifle",
    "G3SG1": "rifle",
    "SG 553": "rifle",
    "AUG": "rifle",
    "FAMAS": "rifle",
    "Galil AR": "rifle",
    # Pistols
    "Desert Eagle": "pistol",
    "USP-S": "pistol",
    "Glock-18": "pistol",
    "P250": "pistol",
    "Five-SeveN": "pistol",
    "Tec-9": "pistol",
    "CZ75-Auto": "pistol",
    "Dual Berettas": "pistol",
    "P2000": "pistol",
    "R8 Revolver": "pistol",
    # SMGs
    "MAC-10": "smg",
    "MP9": "smg",
    "UMP-45": "smg",
    "PP-Bizon": "smg",
    "P90": "smg",
    "MP7": "smg",
    "MP5-SD": "smg",
    # Shotguns
    "Nova": "shotgun",
    "XM1014": "shotgun",
    "MAG-7": "shotgun",
    "Sawed-Off": "shotgun",
    # Machine guns
    "M249": "machinegun",
    "Negev": "machinegun",
}

# Known CS2 agent factions (substring in part after " | ")
_AGENT_FACTIONS: tuple[str, ...] = (
    "FBI",
    "KSK",
    "SAS",
    "SEAL",
    "SWAT",
    "Sabre",
    "Phoenix",
    "Elite Crew",
    "Guerrilla",
    "Professional",
    "Ground Rebel",
    "Balkans",
    "TACP",
    "USAF",
    "NSWC",
    "Frogman",
    "Ricksaw",
)


@beartype
def classify(name: str) -> str:
    """Classify a CS2 item name into a category.

    Strips StatTrak/Souvenir prefixes, then checks patterns in order:
    star -> gloves -> keyword items -> weapon map -> agents -> other.
    """
    # Strip prefixes that don't affect category
    clean = name
    if clean.startswith("StatTrak\u2122 "):
        clean = clean[len("StatTrak\u2122 "):]
    if clean.startswith("Souvenir "):
        clean = clean[len("Souvenir "):]

    # Star prefix = knife or gloves
    if clean.startswith("\u2605"):
        # Check gloves before defaulting to knife
        if "Gloves" in clean:
            return "gloves"
        return "knife"

    # Keyword-based items (order matters)
    if clean.startswith("Sealed Graffiti"):
        return "graffiti"

    if clean.startswith("Music Kit"):
        return "music_kit"

    if clean.startswith("Patch |"):
        return "patch"

    if clean.startswith("Sticker |"):
        return "sticker"

    # Keys must be checked before cases (both contain "Case"/"Capsule")
    # Also check for "Key" at end of name (e.g. "Community Sticker Capsule 1 Key")
    if "Case Key" in clean or "Capsule Key" in clean or clean.endswith(" Key"):
        return "key"

    # Cases and capsules
    if "Case" in clean or "Capsule" in clean:
        return "case"

    # Weapon lookup: extract base name (part before " | ")
    base = clean.split(" | ")[0].strip()
    if base in _WEAPON_MAP:
        return _WEAPON_MAP[base]

    # Agent detection: items with " | FACTION" pattern
    if " | " in clean:
        faction_part = clean.split(" | ", 1)[1]
        for faction in _AGENT_FACTIONS:
            if faction in faction_part:
                return "agent"
        # Also check if the name starts with common agent title words
        agent_titles = ("Master Agent", "Agent", "Cmdr.", "Lt. Commander",
                        "Sir Bloody", "Operator", "Special Agent",
                        "Chem-Haz", "Engineer", "Dragomir",
                        "'Medium Rare' Crasswater", "Buckshot",
                        "Street Soldier", "Enforcer", "Slingshot",
                        "Sergeant", "Officer", "Commander", "Doctor")
        for title in agent_titles:
            if base.startswith(title) or title in base:
                return "agent"

    return "other"
