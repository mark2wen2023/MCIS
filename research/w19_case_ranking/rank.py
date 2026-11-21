"""Research only: explicit reviewed tag vocabulary, no retrieval/auth/publication.
Rows must come from an independently authorized Published Case selection in any
future integration. JSON status is not proof of authorization or publication.
"""
from fractions import Fraction
import re


def tags(values):
    if not isinstance(values, (list, tuple)) or any(not isinstance(v, str) for v in values):
        raise ValueError('tags must be strings')
    return {v.strip().casefold() for v in values if v.strip()}


def rank_cases(query_tags, cards, *, reviewed_vocabulary):
    """Top at most five positive Jaccard matches, equal scores by cardId ascending.
    Unknown/unreviewed tags never match. Labels and vocabulary are research
    inputs, not invented production fields or inferred accident mechanisms.
    """
    vocabulary = tags(reviewed_vocabulary)
    query = tags(query_tags) & vocabulary
    if not query:
        return []
    ranked, seen = [], set()
    for card in cards:
        if not isinstance(card, dict):
            raise ValueError('invalid card')
        content = card.get('content')
        if card.get('status') != 'Published' or not isinstance(content, dict) or content.get('kind') != 'Case':
            continue
        identity = card.get('cardId')
        if not isinstance(identity, str) or not re.fullmatch(r'KC-[a-f0-9]{32}', identity) or identity in seen:
            raise ValueError('invalid or duplicate eligible identity')
        seen.add(identity)
        features = tags(content.get('tags')) & vocabulary
        shared = query & features
        if not shared:
            continue
        union = query | features
        score = Fraction(len(shared), len(union))
        ranked.append((score, identity, {'cardId': identity,
            'score': {'numerator': score.numerator, 'denominator': score.denominator},
            'sharedTags': sorted(shared), 'queryOnlyTags': sorted(query-features),
            'cardOnlyTags': sorted(features-query)}))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    return [item[2] for item in ranked[:5]]
