from quakewatch.regions import region_from_place


def test_region_is_text_after_last_comma():
    assert region_from_place("24 km ENE of Beluga, Alaska") == "Alaska"


def test_state_codes_are_expanded():
    assert region_from_place("6 km NW of The Geysers, CA") == "California"


def test_place_without_comma():
    assert region_from_place("Off the coast of Japan") == "Japan"
    assert region_from_place("Fiji region") == "Fiji region"


def test_missing_place():
    assert region_from_place(None) == "Unknown"
