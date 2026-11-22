"""One-attempt experimental live test for Member 3 on the CityUCS/DeepSeek gateway.

Opt-in (RUN_AZURE_LIVE=1). Uses only the synthetic certificate and the configured
school endpoint. At most one generation attempt, no retries. Asserts the expected
values and derived flags (a failed extraction fails the test). Prints actual
provider-reported usage separately from the experimental estimate. Never prints
credentials. This does NOT verify REQ-COST-001.
"""

import os
from pathlib import Path

import pytest

from src.ai import PROMPT_VERSION, extract

from .cityu_experimental import ExperimentalCityUProvider

ENV_FILE = Path.home() / 'CS5351' / 'Project' / 'agent.env'
CERTIFICATE = ('Hospital: City Clinic\nVisit date: 2026-10-21\n'
               'Recommended rest: 3 days\nDiagnosis: acute migraine')
EXPECTED = dict(hospital_name='City Clinic', visit_date='2026-10-21',
                rest_days='3 days', diagnosis='acute migraine')


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


@pytest.mark.skipif(os.environ.get('RUN_AZURE_LIVE') != '1',
                    reason='set RUN_AZURE_LIVE=1 to run the experimental CityU live test')
def test_cityu_experimental_single_attempt():
    _load_env(ENV_FILE)
    base_url = os.environ['AZURE_FOUNDRY_BASE_URL']
    model_version = os.environ['DEEPSEEK_V4_FLASH_DEPLOYMENT'].strip()
    assert base_url.startswith('https://llm.cs.cityu.edu.hk'), base_url

    from openai import OpenAI

    client = OpenAI(base_url=base_url, api_key=os.environ['AZURE_INFERENCE_CREDENTIAL'])
    provider = ExperimentalCityUProvider(client, model_version=model_version)

    result = extract(CERTIFICATE, provider=provider, ai_allowed=True)

    print('\n--- cityu experimental live report ---')
    print(f'model: {model_version}')
    print(f'prompt: {PROMPT_VERSION}')
    print(f'generate_attempts: 1 (no retries)')
    print(f'experimental_prompt_upper_bound_bytes: '
          f'{provider.observed.get("prompt_upper_bound_bytes")}')
    print(f'finish_reason: {provider.observed.get("finish_reason")}')
    print(f'reasoning_present: {provider.observed.get("reasoning_present")}')
    print('ACTUAL provider usage (not an estimate):')
    print(f'  prompt_tokens: {provider.observed.get("usage_prompt")}')
    print(f'  completion_tokens: {provider.observed.get("usage_completion")}')
    print(f'  total_tokens: {provider.observed.get("usage_total")}')
    print('NOTE: the byte upper bound is experimental and is NOT a token count; '
          'REQ-COST-001 is NOT verified by this run.')
    for name in EXPECTED:
        f = getattr(result, name)
        print(f'{name}: value={f.value!r} derived={f.derived} confidence={f.confidence}')

    if provider.observed.get('usage_total') is None:
        print('provider_reported_total: unknown')

    for name, expected in EXPECTED.items():
        field = getattr(result, name)
        assert field.value == expected, f'{name} mismatch: {field.value!r}'
        assert field.derived is True, f'{name} not derived'
        assert field.confidence >= 0.75, f'{name} low confidence {field.confidence}'
    assert 'sk-' not in repr(provider.observed), 'credential leaked'
