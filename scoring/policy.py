"""Versioned business policy, independent of the semantic decision provider."""


def axis_coverage(factors, axis):
    items = [f for f in factors if not f.hard_requirement and f.axis == axis]
    total = sum(f.weight for f in items)
    return sum(f.weight for f in items if f.outcome != 'unknown') / total if total else None


def recommend(profile, factors, status, fit):
    """Return a recommendation, its reasons, and hard-rule eligibility.

    Scores are ranking aids. They cannot override a failed eligibility rule,
    missing evidence, or a buyer mismatch. Thresholds are profile policy,
    not calibrated conversion probabilities.
    """
    hard = [f for f in factors if f.hard_requirement]
    failed = [f.criterion_id for f in hard if f.outcome == 'miss']
    if failed:
        return 'no', ['Mandatory requirements failed: ' + ', '.join(failed) + '.'], 'ineligible'
    eligibility = 'unknown' if any(f.outcome != 'match' for f in hard) else 'eligible'
    reasons = []
    if status == 'failed':
        reasons.append('An evaluation failed; retry before making a recommendation.')
    if eligibility == 'unknown':
        reasons.append('One or more mandatory requirements are unresolved.')
    if not profile.offering or not profile.buyer_persona:
        reasons.append('Supply the offering and target buyer persona to assess buyer relevance.')
    people = [f for f in factors if f.field.startswith('person.')]
    semantic_people = [f for f in people if f.evaluator == 'llm']
    if not semantic_people:
        reasons.append('Add a semantic job-title or role-responsibilities criterion for the target buyer.')
    if not any(f.field.startswith('company.') for f in factors):
        reasons.append('Add company criteria to assess account fit.')
    unknown = [f.criterion_id for f in factors if f.outcome == 'unknown']
    if unknown:
        reasons.append('Evidence is missing or unresolved for: ' + ', '.join(unknown) + '.')
    if reasons:
        return 'needs_review', reasons, eligibility
    misses = [f.criterion_id for f in people if f.outcome == 'miss']
    if misses:
        return 'no', ['The supplied evidence contradicts buyer criteria: ' + ', '.join(misses) + '.'], eligibility
    if any(f.outcome == 'partial' for f in people):
        return 'needs_review', ['Buyer relevance is only partially supported.'], eligibility
    if status != 'scored' or fit is None:
        return 'needs_review', ['There is insufficient fit evidence for a recommendation.'], eligibility
    if fit < profile.warm_threshold:
        return 'no', ['Fit is below the configured minimum recommendation threshold.'], eligibility
    if fit < profile.hot_threshold:
        return 'needs_review', ['Fit is between the configured review and recommendation thresholds.'], eligibility
    return 'yes', ['Mandatory rules pass, buyer criteria match, and fit meets the configured recommendation threshold.'], eligibility
