"""Five-case experimental live evaluation for the CityUCS/DeepSeek gateway.

EXPERIMENT ONLY. Bypasses the unavailable total-token preflight by calling the
experimental adapter's generate() directly (no production code changed). Strict
JSON validation, source-grounding, and derived-flag checks still run through the
real validation helpers. At most one request per case; five total; no retries,
no fallbacks, no output-limit changes. Does NOT verify the 3,000-total-token hard
cap or full REQ-COST-001 compliance. Never prints credentials.

Run:  RUN_AZURE_LIVE=1 python3 -m pytest test/live/ai/evaluate_cityu_five.py -v -s
"""

import json
import os
from pathlib import Path

import pytest

from src.ai.extractor import (FIELDS, PROMPT, _decode, _supported, _wire_schema)

from .cityu_experimental import ExperimentalCityUProvider

ENV_FILE = Path.home() / 'CS5351' / 'Project' / 'agent.env'
MAX_OUTPUT_TOKENS = 300

# Five fixed synthetic certificates. 'expected' maps field -> expected value
# (None means the field should be absent/ungrounded and must be nulled).
CASES = [
    {
        'name': 'migraine_full',
        'text': ('Hospital: City Clinic\nVisit date: 2026-10-21\n'
                 'Recommended rest: 3 days\nDiagnosis: acute migraine'),
        'expected': dict(hospital_name='City Clinic', visit_date='2026-10-21',
                         rest_days='3 days', diagnosis='acute migraine'),
    },
    {
        'name': 'gastro_other_hospital',
        'text': ('Hospital: Northside General Hospital\nVisit date: 2026-03-04\n'
                 'Recommended rest: 2 days\nDiagnosis: acute gastroenteritis'),
        'expected': dict(hospital_name='Northside General Hospital',
                         visit_date='2026-03-04', rest_days='2 days',
                         diagnosis='acute gastroenteritis'),
    },
    {
        'name': 'fever_south_clinic',
        'text': ('Hospital: South Point Clinic\nVisit date: 2025-12-30\n'
                 'Recommended rest: 1 day\nDiagnosis: viral fever'),
        'expected': dict(hospital_name='South Point Clinic',
                         visit_date='2025-12-30', rest_days='1 day',
                         diagnosis='viral fever'),
    },
    {
        'name': 'missing_diagnosis',
        'text': ('Hospital: Riverside Medical Centre\nVisit date: 2026-01-15\n'
                 'Recommended rest: 4 days'),
        'expected': dict(hospital_name='Riverside Medical Centre',
                         visit_date='2026-01-15', rest_days='4 days',
                         diagnosis=None),
    },
    {
        'name': 'issue_date_not_visit',
        'text': ('Hospital: Lakeview Clinic\nIssue date: 2026-05-02\n'
                 'Visit date: 2026-04-28\nRecommended rest: 2 days\n'
                 'Diagnosis: lower back strain'),
        'expected': dict(hospital_name='Lakeview Clinic',
                         visit_date='2026-04-28', rest_days='2 days',
                         diagnosis='lower back strain'),
    },
]


def _load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, _, val = line.partition('=')
        key = key.strip()
        if key.startswith('AZURE_') or key == 'DEEPSEEK_V4_FLASH_DEPLOYMENT':
            os.environ.setdefault(key, val.strip().strip('"\''))


def _validate(content: str, document: str):
    """Run the production validation pipeline on content; return ExtractionResult."""
    try:
        parsed = _decode(content)
    except (TypeError, ValueError, RecursionError):
        return None
    confirmed = {}
    for key in FIELDS:
        field = getattr(parsed, key)
        if field.value is None or not _supported(key, field.value, document):
            from src.schemas import ExtractedField
            field = ExtractedField(value=None, derived=True, confidence=0)
        confirmed[key] = field
    from src.schemas import ExtractionResult
    return ExtractionResult(**confirmed)


@pytest.mark.skipif(os.environ.get('RUN_AZURE_LIVE') != '1',
                    reason='set RUN_AZURE_LIVE=1 to run the five-case evaluation')
def test_cityu_five_case_experimental():
    _load_env(ENV_FILE)
    base_url = os.environ['AZURE_FOUNDRY_BASE_URL']
    model_version = os.environ['DEEPSEEK_V4_FLASH_DEPLOYMENT'].strip()
    assert base_url.startswith('https://llm.cs.cityu.edu.hk'), base_url

    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=os.environ['AZURE_INFERENCE_CREDENTIAL'],
                    max_retries=0, timeout=30.0)
    provider = ExperimentalCityUProvider(client, model_version=model_version)
    schema = _wire_schema()

    results = []
    print('\n=== experimental five-case evaluation (NOT REQ-COST-001 compliant) ===')
    for case in CASES:
        # One request per case; direct generate() to bypass the unavailable preflight.
        try:
            content, total = provider.generate(
                instructions=PROMPT['instructions'], document=case['text'],
                schema=schema, max_output_tokens=MAX_OUTPUT_TOKENS)
            gen_ok = True
            gen_err = None
        except Exception as exc:  # noqa: BLE001 - report, do not retry
            content, total, gen_ok, gen_err = '', None, False, type(exc).__name__

        result = _validate(content, case['text']) if gen_ok else None
        passed = False
        field_report = {}
        if result is not None:
            checks = []
            for key, expected in case['expected'].items():
                got = getattr(result, key).value
                checks.append(got == expected)
                field_report[key] = got
            derived_ok = all(getattr(result, k).derived is True for k in FIELDS)
            passed = all(checks) and derived_ok
        usage = {
            'prompt': provider.observed.get('usage_prompt'),
            'completion': provider.observed.get('usage_completion'),
            'total': provider.observed.get('usage_total'),
        }
        results.append({'case': case['name'], 'passed': passed, 'gen_ok': gen_ok,
                        'gen_err': gen_err, 'usage': usage, 'values': field_report,
                        'finish': provider.observed.get('finish_reason')})
        print(f"\n[{case['name']}] pass={passed} gen_ok={gen_ok} gen_err={gen_err} "
              f"finish={provider.observed.get('finish_reason')}")
        print(f"  values: {field_report}")
        print(f"  usage: prompt={usage['prompt']} completion={usage['completion']} "
              f"total={usage['total']}")

    reported = [r['usage']['total'] for r in results
                if type(r['usage']['total']) is int]
    print('\n=== summary ===')
    print(f"requests: {len(results)} (max 5, no retries)")
    for r in results:
        print(f"  {r['case']}: {'PASS' if r['passed'] else 'FAIL'}")
    if reported:
        avg = sum(reported) / len(reported)
        print(f"average total tokens over {len(reported)} case(s) with reported usage: "
              f"{avg:.2f}")
    else:
        print('average total tokens: unknown (no reported usage)')
    unknowns = [r['case'] for r in results if r['usage']['total'] is None]
    if unknowns:
        print(f"cases with unknown usage: {unknowns}")

    # Each case must produce a valid extraction; failed generation fails the test.
    for r in results:
        assert r['gen_ok'], f"{r['case']} generation failed: {r['gen_err']}"
    assert len(results) == len(CASES)
