"""Existing demo industries choices and explicit-text patterns."""

INDUSTRIES = {
    "none_specified": "No target industry is stated. A job title or location is not an industry.",
    "it_services": "IT services, IT consulting, managed IT, software development agencies and technology outsourcing.",
    "b2b_saas": "SaaS, cloud software and subscription software products.",
    "healthcare": "Healthcare, hospitals, clinics, medical devices, biotech and pharmaceuticals.",
    "fintech": "Fintech, financial technology, banking, payments, investment and crypto.",
    "ecommerce_retail": "E-commerce, retail, DTC and marketplaces.",
    "general_business": "Explicit cross-industry business services or general consulting.",
    "other": "An explicitly requested industry outside this demo's supported industry catalog.",
}


INDUSTRY_PATTERNS = {
    "it_services": r"\b(?:it[ -]services?|information technology services?|it consulting|managed it(?: services?)?|technology outsourcing|software development agenc(?:y|ies))\b",
    "b2b_saas": r"\b(?:saas|software[ -]as[ -]a[ -]service|cloud software|software products?)\b",
    "healthcare": r"\b(?:healthcare|medical|hospitals?|clinics?|biotech|pharmaceuticals?)\b",
    "fintech": r"\b(?:fintech|financial technology|banking|payments?|investment|crypto)\b",
    "ecommerce_retail": r"\b(?:e[ -]?commerce|retail|dtc|marketplaces?)\b",
    "general_business": r"\b(?:cross[ -]industry|general business|consulting)\b",
    "other": r"\b(?:manufacturing|education|insurance|construction|automotive|energy|logistics|telecom|hospitality|real estate|agriculture|software)\b",
}
