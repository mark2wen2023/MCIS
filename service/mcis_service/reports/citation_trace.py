"""Snapshot-local positional trace, without resolving or certifying sources."""
import json

NOTICE = ('引用逐次定位仅保留报告快照中的声明，不核验原件、当前来源、语义支持、作者或事实；'
          '位置编号仅适用于本份快照。请保留完整报告下载包以对照内容。 / '
          'Occurrence trace records snapshot declarations only, not verified originals, current sources, '
          'semantic support, authorship or facts. Positions apply only to this snapshot; retain the full report download bundle.')


def sentence_marker(section_index, sentence_index):
    return f'S{section_index}.{sentence_index}'


def citation_marker(sentence_key, citation_index):
    return 'C' + sentence_key[1:] + f'.{citation_index}'


def _json_display(value):
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
    # PDF paragraph layout collapses literal spaces: expose them losslessly.
    return "".join(f"\\u{ord(char):04x}" if char.isspace() else char for char in encoded)


def display_fields(value, keys):
    # JSON string display preserves whitespace/control characters unambiguously.
    # Missing flags are not silently coerced to false or treated as verified.
    return ' | '.join(key + '=' + (_json_display(value[key])
                     if key in value else 'not supplied') for key in keys)


def declaration_key(citation):
    return json.dumps(citation, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def sentence_lines(section, sentence, marker):
    yield marker + ' | ' + display_fields(section, ('sectionId',)) + ' | ' + display_fields(
        sentence, ('sentenceId', 'status', 'sourceStatus', 'missing'))
    citations = sentence.get('citations', [])
    if not citations:
        yield marker + ' | 未提供引用 / No citations supplied (not a finding of support)'
    for index, citation in enumerate(citations, 1):
        yield citation_marker(marker, index) + ' | ' + display_fields(citation, (
            'kind', 'id', 'registration', 'unregistered', 'needsReview', 'href', 'sourceRef'))
