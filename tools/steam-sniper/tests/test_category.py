"""Tests for CS2 item category classification."""
from __future__ import annotations

import pytest

from category import classify


class TestKnives:
    def test_star_knife_with_skin(self) -> None:
        assert classify("★ Karambit | Doppler (Factory New)") == "knife"

    def test_vanilla_knife_no_skin(self) -> None:
        assert classify("★ Karambit") == "knife"

    def test_stattrak_knife(self) -> None:
        assert classify("★ StatTrak™ Karambit | Doppler (Factory New)") == "knife"

    def test_butterfly_knife(self) -> None:
        assert classify("★ Butterfly Knife | Fade (Factory New)") == "knife"


class TestGloves:
    def test_sport_gloves(self) -> None:
        assert classify("★ Sport Gloves | Hedge Maze (Field-Tested)") == "gloves"

    def test_driver_gloves(self) -> None:
        assert classify("★ Driver Gloves | Crimson Weave (Minimal Wear)") == "gloves"

    def test_specialist_gloves(self) -> None:
        assert classify("★ Specialist Gloves | Fade (Factory New)") == "gloves"


class TestRifles:
    def test_ak47(self) -> None:
        assert classify("AK-47 | Redline (Field-Tested)") == "rifle"

    def test_m4a4(self) -> None:
        assert classify("M4A4 | Howl (Factory New)") == "rifle"

    def test_m4a1s(self) -> None:
        assert classify("M4A1-S | Knight (Factory New)") == "rifle"

    def test_awp(self) -> None:
        assert classify("AWP | Dragon Lore (Factory New)") == "rifle"

    def test_stattrak_rifle(self) -> None:
        assert classify("StatTrak™ AK-47 | Redline (Field-Tested)") == "rifle"

    def test_souvenir_rifle(self) -> None:
        assert classify("Souvenir M4A1-S | Knight (Factory New)") == "rifle"

    def test_ssg08(self) -> None:
        assert classify("SSG 08 | Blood in the Water (Factory New)") == "rifle"

    def test_aug(self) -> None:
        assert classify("AUG | Akihabara Accept (Factory New)") == "rifle"

    def test_galil(self) -> None:
        assert classify("Galil AR | Chatterbox (Battle-Scarred)") == "rifle"

    def test_famas(self) -> None:
        assert classify("FAMAS | Roll Cage (Minimal Wear)") == "rifle"

    def test_scar20(self) -> None:
        assert classify("SCAR-20 | Emerald (Factory New)") == "rifle"

    def test_g3sg1(self) -> None:
        assert classify("G3SG1 | The Executioner (Factory New)") == "rifle"

    def test_sg553(self) -> None:
        assert classify("SG 553 | Integrale (Factory New)") == "rifle"


class TestPistols:
    def test_deagle(self) -> None:
        assert classify("Desert Eagle | Blaze (Factory New)") == "pistol"

    def test_usps(self) -> None:
        assert classify("USP-S | Kill Confirmed (Factory New)") == "pistol"

    def test_glock(self) -> None:
        assert classify("Glock-18 | Fade (Factory New)") == "pistol"

    def test_p250(self) -> None:
        assert classify("P250 | See Ya Later (Factory New)") == "pistol"

    def test_five_seven(self) -> None:
        assert classify("Five-SeveN | Monkey Business (Minimal Wear)") == "pistol"

    def test_tec9(self) -> None:
        assert classify("Tec-9 | Fuel Injector (Factory New)") == "pistol"

    def test_cz75(self) -> None:
        assert classify("CZ75-Auto | Victoria (Factory New)") == "pistol"

    def test_dual_berettas(self) -> None:
        assert classify("Dual Berettas | Cobalt Quartz (Factory New)") == "pistol"

    def test_p2000(self) -> None:
        assert classify("P2000 | Ocean Foam (Factory New)") == "pistol"

    def test_r8(self) -> None:
        assert classify("R8 Revolver | Amber Fade (Factory New)") == "pistol"


class TestSMGs:
    def test_mac10(self) -> None:
        assert classify("MAC-10 | Neon Rider (Minimal Wear)") == "smg"

    def test_mp9(self) -> None:
        assert classify("MP9 | Hydra (Factory New)") == "smg"

    def test_ump45(self) -> None:
        assert classify("UMP-45 | Primal Saber (Factory New)") == "smg"

    def test_p90(self) -> None:
        assert classify("P90 | Asiimov (Factory New)") == "smg"

    def test_pp_bizon(self) -> None:
        assert classify("PP-Bizon | Judgement of Anubis (Factory New)") == "smg"

    def test_mp7(self) -> None:
        assert classify("MP7 | Nemesis (Factory New)") == "smg"

    def test_mp5sd(self) -> None:
        assert classify("MP5-SD | Phosphor (Factory New)") == "smg"


class TestShotguns:
    def test_nova(self) -> None:
        assert classify("Nova | Hyper Beast (Factory New)") == "shotgun"

    def test_xm1014(self) -> None:
        assert classify("XM1014 | Tranquility (Factory New)") == "shotgun"

    def test_mag7(self) -> None:
        assert classify("MAG-7 | Heat (Factory New)") == "shotgun"

    def test_sawed_off(self) -> None:
        assert classify("Sawed-Off | The Kraken (Factory New)") == "shotgun"


class TestMachineguns:
    def test_m249(self) -> None:
        assert classify("M249 | Magma (Factory New)") == "machinegun"

    def test_negev(self) -> None:
        assert classify("Negev | Loudmouth (Factory New)") == "machinegun"


class TestNonWeapons:
    def test_sticker(self) -> None:
        assert classify("Sticker | Natus Vincere (Holo) | Katowice 2014") == "sticker"

    def test_case(self) -> None:
        assert classify("Operation Breakout Weapon Case") == "case"

    def test_graffiti(self) -> None:
        assert classify("Sealed Graffiti | King Me (Shark White)") == "graffiti"

    def test_music_kit(self) -> None:
        assert classify("Music Kit | Darude, Sandstorm") == "music_kit"

    def test_patch(self) -> None:
        assert classify("Patch | Metal Silver Skull") == "patch"

    def test_case_key(self) -> None:
        assert classify("CS:GO Case Key") == "key"

    def test_capsule_key(self) -> None:
        assert classify("Community Sticker Capsule 1 Key") == "key"

    def test_agent(self) -> None:
        assert classify("Master Agent Ava | FBI") == "agent"

    def test_agent_with_faction(self) -> None:
        assert classify("Cmdr. Frank 'Wet Sox' Baroud | SEAL Frogman") == "agent"

    def test_unknown(self) -> None:
        assert classify("Some Unknown Item") == "other"

    def test_sticker_capsule_is_case(self) -> None:
        assert classify("Sticker Capsule 2") == "case"

    def test_stattrak_music_kit(self) -> None:
        assert classify("StatTrak™ Music Kit | Darude, Sandstorm") == "music_kit"

    def test_dreams_nightmares_case(self) -> None:
        assert classify("Dreams & Nightmares Case") == "case"

    def test_revolution_case(self) -> None:
        assert classify("Revolution Case") == "case"
