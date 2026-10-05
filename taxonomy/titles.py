"""Existing demo titles choices and explicit-text patterns."""

TARGET_ROLES = {
    "none_specified": "No target job title or role is requested, including company-only and record-maintenance requests.",
    "founders_c_level": "Founders, co-founders, CEOs, CTOs and other chief executives.",
    "engineering_leaders": "VPs of Engineering, Engineering Directors, Heads of Engineering and Technical Leads.",
    "sales_leaders": "VPs of Sales, Sales Directors, Heads of Business Development and Chief Revenue Officers.",
    "marketing_leaders": "VPs of Marketing, Marketing Directors, Heads of Growth and Chief Marketing Officers.",
    "general_staff": "Individual contributors, developers, designers, managers or staff without a more specific supported leadership category.",
}


ROLE_PATTERNS = {
    "engineering_leaders": r"\b(?:vps?|vice[ -]presidents?|heads?|directors?|leads?)\s+(?:of\s+)?engineering\b|\b(?:engineering|technical)\s+(?:vps?|directors?|heads?|leads?|leaders?)\b",
    "sales_leaders": r"\b(?:vps?|vice[ -]presidents?|heads?|directors?)\s+(?:of\s+)?(?:sales|business development)\b|\b(?:sales leaders?|sales directors?|cros?|chief revenue officers?)\b",
    "marketing_leaders": r"\b(?:vps?|vice[ -]presidents?|heads?|directors?)\s+(?:of\s+)?(?:marketing|growth)\b|\b(?:marketing leaders?|marketing directors?|cmos?|chief marketing officers?)\b",
    "founders_c_level": r"\b(?:founders?|co[ -]founders?|ceos?|ctos?|chief executive officers?|chief technology officers?|c[ -]suite|chief officers?)\b",
    "general_staff": r"\b(?:people|contacts?|staff|employees?|executives?|decision[ -]makers?|developers?|designers?|managers?|leaders?|directors?|heads?|vps?|vice[ -]presidents?)\b",
}
