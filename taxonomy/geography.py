"""Existing demo geography choices and explicit-text patterns."""

GEOGRAPHIES = {
    "none_specified": "No location is stated. Do not assume the US or worldwide coverage.",
    "india": "India or Indian locations.",
    "california_west_us": "California, San Francisco, Silicon Valley, Los Angeles or the US West Coast.",
    "us_nationwide": "USA, US, United States, America or nationwide US coverage.",
    "europe": "Europe, European Union, UK, Germany, France or Netherlands.",
    "global": "Explicit worldwide, global, international or any-location coverage.",
    "other": "An explicitly requested location outside this demo's supported location catalog.",
}


GEOGRAPHY_PATTERNS = {
    "california_west_us": r"\b(?:california|san francisco|silicon valley|los angeles|west coast|bay area)\b",
    "india": r"\b(?:india|indian|bengaluru|bangalore|hyderabad|mumbai|delhi)\b",
    "us_nationwide": r"\b(?:usa|united states|america|american|us)\b|\bu\.s\.(?:a\.?)?",
    "europe": r"\b(?:europe|european|european union|uk|united kingdom|germany|france|netherlands|london|berlin|paris|amsterdam)\b",
    "global": r"\b(?:global|worldwide|international|anywhere|any location)\b",
    "other": r"\b(?:canada|canadian|singapore|australia|australian|japan|china|brazil|uae|dubai|africa|asia|new york|texas|boston|seattle)\b",
}
