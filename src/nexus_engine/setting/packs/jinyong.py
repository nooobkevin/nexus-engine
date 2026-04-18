from __future__ import annotations


from nexus_engine.setting.setting_pack import (
    SettingPack,
    Archetype,
    ControlledVocabulary,
    PowerSystemSpec,
    StyleGuide,
)


JINYONG_VOCABULARY = ControlledVocabulary(
    namespaces=frozenset(["material", "technique", "school", "rank", "element", "body_part"]),
    tags_by_namespace={
        "material": frozenset(["steel", "jade", "wood", "bone"]),
        "technique": frozenset(["sword", "palm", "fist", "staff", "inner_force"]),
        "school": frozenset(["shaolin", "wudang", "emei", "songliao"]),
        "rank": frozenset(["junior", "senior", "master", "grandmaster"]),
        "element": frozenset(["fire", "water", "earth", "wood", "metal"]),
        "body_part": frozenset(["hand", "foot", "eye", "meridian"]),
    },
)


def create_jinyong_setting_pack() -> SettingPack:
    from nexus_engine.core.value_objects import ArchetypeId, Tag, TierLevel

    archetypes = {
        ArchetypeId("swordsman"): Archetype(
            id=ArchetypeId("swordsman"),
            name="劍客",
            description="擅長劍術的武俠人物",
            base_tags=frozenset([
                Tag("technique", "sword"),
                Tag("school", "neutral"),
            ]),
            base_properties={"martial_arts_style": "sword"},
            default_abilities=["basic_sword_strike", "defensive_stance"],
            power_tier=TierLevel.MUNDANE,
        ),
        ArchetypeId("internal_art_practitioner"): Archetype(
            id=ArchetypeId("internal_art_practitioner"),
            name="內功修煉者",
            description="擅長內功的武俠人物",
            base_tags=frozenset([
                Tag("technique", "inner_force"),
                Tag("body_part", "meridian"),
            ]),
            base_properties={"martial_arts_style": "internal"},
            default_abilities=["qi_circulation", "inner_force_shield"],
            power_tier=TierLevel.MUNDANE,
        ),
    }

    from nexus_engine.setting.setting_pack import ResourcePoolDef, TierDef

    power_system = PowerSystemSpec(
        resource_pools=[
            ResourcePoolDef(id="qi", name="氣", max_at_tier=[100, 200, 400, 800, 1600]),
            ResourcePoolDef(id="jing", name="精", max_at_tier=[50, 100, 200, 400, 800]),
        ],
        tier_levels=[
            TierDef(level=0, name="不入流", abilities=["basic_movement"]),
            TierDef(level=1, name="三流", abilities=["basic_techniques"]),
            TierDef(level=2, name="二流", abilities=["advanced_techniques"]),
            TierDef(level=3, name="一流", abilities=["master_techniques"]),
            TierDef(level=4, name="宗師", abilities=["grandmaster_techniques"]),
        ],
        advancement_rules=[],
        ability_taxonomy={},
    )

    return SettingPack(
        id="jinyong_wuxia",
        version="1.0.0",
        archetypes=archetypes,
        power_system=power_system,
        vocabulary=JINYONG_VOCABULARY,
        narrative_style=StyleGuide(tone="wuxia", perspective="third_person_limited"),
    )
