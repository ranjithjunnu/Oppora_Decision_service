"""Offline tests for the Jev lead path: questions, decisions, transport retries, place cleanup and LLM fallback.

Run: .\\venv\\Scripts\\python.exe -m unittest discover -s tests
No network calls: Jev is replaced by httpx.MockTransport or a stub, and storage uses a temporary SQLite file.
"""
import asyncio
import dataclasses
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import httpx

from core.config import JevSettings
from engines.jev_engine import JevEngine
from engines.llm_engine import LLMTransportError
from models.lead_lists import SearchPlan
from scoring import batch, repository
from scoring.jev_scoring import build_questions, decide
from scoring.search_validation import clean_place, validate_plan

BASE_FILTERS = {'titles': [], 'countries': [], 'locations': [], 'exclude_locations': [], 'departments': [],
                'management_levels': [], 'experience_min': None, 'experience_max': None}
JEV = JevSettings(api_key='test-key', base_url='https://jev.test', model='jev-1.13.0', timeout_seconds=5,
                  concurrency=1, match_threshold=0.5, input_cost_per_million=0.042, breaker_failures=3, max_attempts=3)


def filters(**values):
    return {**BASE_FILTERS, **values}


def fit(score):
    return {'type': 'score', 'score': score, 'confidence': 0.8,
            'legend': {str(level): f'level {level}' for level in range(4)},
            'probabilities': {'0': 0.0, '1': 0.1, '2': 0.4, '3': 0.5}}


class QuestionTests(unittest.TestCase):
    def test_only_used_filters_become_questions(self):
        questions = build_questions(filters(titles=['Software Engineer'], countries=['United States'], experience_min=5))
        self.assertEqual(set(questions), {'role_match', 'location_match', 'experience_match', 'fit'})
        self.assertEqual(questions['experience_match']['instructions']['requirement'], 'at least 5 years')

    def test_exclusion_department_and_seniority_questions(self):
        questions = build_questions(filters(countries=['Canada'], exclude_locations=['Toronto'],
                                            departments=['Sales'], management_levels=['Director']))
        self.assertEqual(set(questions), {'location_match', 'in_excluded_location', 'department_match', 'seniority_match', 'fit'})

    def test_yes_no_questions_define_both_answers(self):
        for name, question in build_questions(filters(titles=['Nurse'], countries=['Australia'],
                                                      exclude_locations=['Sydney'])).items():
            if name != 'fit':
                self.assertEqual(question['type'], 'noul')
                self.assertTrue(question['criteria']['true'] and question['criteria']['false'])

    def test_role_rules_are_not_sales_specific(self):
        rules = ' '.join(build_questions(filters(titles=['Software Engineer']))['role_match']['instructions']['rules'])
        for phrase in ('Mechanical Engineer', 'recruiter', 'interns', 'individual-contributor target'):
            self.assertIn(phrase, rules)


class DecideTests(unittest.TestCase):
    def test_all_gates_must_pass_and_exclusion_is_inverted(self):
        answers = {'role_match': {'type': 'noul', 'noul': 0.9}, 'location_match': {'type': 'noul', 'noul': 0.8},
                   'in_excluded_location': {'type': 'noul', 'noul': 0.1}, 'fit': fit(2.4)}
        decision = decide(answers, 0.5)
        self.assertTrue(decision['selected'])
        self.assertEqual(decision['gates']['in_excluded_location'], 0.9)
        self.assertEqual(decision['score'], 80)
        self.assertEqual(decision['weakest_requirement'], 'location_match')

    def test_one_failing_gate_rejects(self):
        answers = {'role_match': {'type': 'noul', 'noul': 0.95}, 'in_excluded_location': {'type': 'noul', 'noul': 0.97},
                   'fit': fit(2.0)}
        decision = decide(answers, 0.5)
        self.assertFalse(decision['selected'])
        self.assertEqual(decision['weakest_requirement'], 'in_excluded_location')

    def test_threshold_is_inclusive(self):
        self.assertTrue(decide({'role_match': {'type': 'noul', 'noul': 0.5}, 'fit': fit(1.5)}, 0.5)['selected'])

    def test_fit_only_target_selects_everyone(self):
        self.assertTrue(decide({'fit': fit(0.0)}, 0.5)['selected'])

    def test_malformed_answers_raise(self):
        for answers in ({'role_match': {'type': 'noul', 'noul': 1.4}, 'fit': fit(2)},
                        {'role_match': {'type': 'noul', 'noul': float('nan')}, 'fit': fit(2)},
                        {'role_match': {'type': 'score', 'score': 2}, 'fit': fit(2)},
                        {'role_match': {'type': 'noul', 'noul': 0.7}},
                        {'role_match': {'type': 'noul', 'noul': 0.7}, 'fit': fit(5)}):
            with self.assertRaises((ValueError, KeyError, TypeError)):
                decide(answers, 0.5)


class PlaceCleanupTests(unittest.TestCase):
    def test_negation_words_are_removed(self):
        self.assertEqual(clean_place('excluding London'), 'London')
        self.assertEqual(clean_place('not in New York'), 'New York')
        self.assertEqual(clean_place('Except for the Netherlands.'), 'Netherlands')
        self.assertEqual(clean_place('outside of Sydney'), 'Sydney')

    def test_real_place_names_are_kept(self):
        for place in ('Norway', 'Nottingham', 'Notting Hill', 'the Netherlands', 'Minsk', 'New York'):
            self.assertEqual(clean_place(place), place)

    def test_validate_plan_cleans_and_records(self):
        plan = SearchPlan.model_validate({
            'filters': filters(titles=['HR Director'], countries=['United Kingdom'], exclude_locations=['excluding London']),
            'title_variants': ['HR Director'], 'company_names': [], 'issues': [],
            'requirements': [{'field': 'titles', 'quote': 'HR directors'},
                             {'field': 'countries', 'quote': 'United Kingdom'},
                             {'field': 'exclude_locations', 'quote': 'excluding London'}]})
        cleaned_filters, validation = validate_plan(plan, 'HR directors in the United Kingdom, excluding London')
        self.assertEqual(cleaned_filters['exclude_locations'], ['London'])
        self.assertEqual(validation['cleaned_values'], [{'field': 'exclude_locations', 'from': 'excluding London', 'to': 'London'}])
        self.assertEqual(validation['errors'], [])


ANSWERS = {'answers': {'role_match': {'type': 'noul', 'noul': 0.9}, 'fit': fit(2.7)},
           'model': 'jev-1.13.0', 'usage': {'input_tokens': 100, 'output_tokens': 10}}
QUESTIONS = {'role_match': {'type': 'noul'}, 'fit': {'type': 'score'}}


class TransportTests(unittest.IsolatedAsyncioTestCase):
    async def call(self, responses):
        calls = []

        def handler(request):
            calls.append(request)
            status, body = responses[min(len(calls), len(responses)) - 1]
            return httpx.Response(status, json=body)

        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            with mock.patch('engines.jev_engine.asyncio.sleep', new=mock.AsyncMock()):
                try:
                    return await JevEngine(JEV, client).system_one({}, QUESTIONS), calls
                except LLMTransportError as exc:
                    return exc, calls

    async def test_overload_then_success_is_retried(self):
        result, calls = await self.call([(529, {'error': 'overloaded'}), (200, ANSWERS)])
        self.assertEqual(len(calls), 2)
        self.assertEqual(result.attempts, 2)

    async def test_server_error_is_retried_until_attempts_run_out(self):
        result, calls = await self.call([(503, {'error': 'down'})])
        self.assertEqual(len(calls), 3)
        self.assertIsInstance(result, LLMTransportError)
        self.assertTrue(result.retryable)

    async def test_client_error_is_not_retried(self):
        result, calls = await self.call([(400, {'error': 'bad request'})])
        self.assertEqual(len(calls), 1)
        self.assertIsInstance(result, LLMTransportError)

    async def test_missing_answers_are_rejected(self):
        result, _ = await self.call([(200, {'answers': {'role_match': {'type': 'noul', 'noul': 0.9}}})])
        self.assertEqual(result.code, 'invalid_provider_response')

    async def test_secret_is_not_returned(self):
        result, _ = await self.call([(401, {'error': 'bad key test-key'})])
        self.assertNotIn('test-key', result.message)


@dataclasses.dataclass
class LLMStub:
    provider: str = 'deepseek'
    model: str = 'deepseek-test'
    lead_batch_size: int = 50
    lead_batch_concurrency: int = 2
    lead_prompt: str = 'oppora-filter-v2'


def make_run(count, decision_model='jev'):
    people = [{'id': f'c{index}:0', 'company_id': f'c{index}', 'company_name': f'Company {index}', 'name': f'Person {index}',
               'title': 'Software Engineer', 'location': 'Austin, Texas, United States'} for index in range(count)]
    target = {'id': 'target_' + '0' * 32, 'description': 'Software engineers in the United States', 'objective': '',
              'filters': filters(titles=['Software Engineer'], countries=['United States'])}
    return batch.new_run(target, people, LLMStub(), persist=False, decision_model=decision_model,
                         jev_settings=JEV if decision_model == 'jev' else None)


class FallbackTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        patcher = mock.patch.object(repository, 'STORE', Path(self.tmp.name) / 'test.sqlite3')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self.tmp.cleanup)
        self.llm_batches = []

    async def fake_score_batch(self, run, settings, number, chunk, fallback=False):
        self.llm_batches.append((fallback, [item['person']['id'] for item in chunk]))
        for item in chunk:
            item.update(status='matched', score=77, decided_by='llm_fallback' if fallback else 'llm', error=None)
        batch.update_counts(run)

    def judge(self, failing):
        async def fake_judge(settings, person, target, client=None):
            trace = {'id': 'call_' + person['id'], 'error': None, 'error_code': None, 'status': 'failed',
                     'purpose': 'Judge one lead with Jev', 'prompt_version': 'test', 'model': 'jev-1.13.0',
                     'input_tokens': None, 'output_tokens': None, 'cached_input_tokens': None,
                     'reasoning_tokens': None, 'latency_ms': None, 'estimated_cost_usd': None}
            if failing(person):
                trace.update(error='Jev returned HTTP 529.', error_code='provider_overloaded')
                return None, trace
            trace['status'] = 'validated'
            return {'selected': True, 'score': 90, 'match_probability': 0.9, 'gates': {'role_match': 0.9},
                    'weakest_requirement': 'role_match', 'fit_confidence': 0.8, 'fit_probabilities': None}, trace
        return fake_judge

    async def execute(self, run, jev, failing):
        with mock.patch.object(batch, 'judge_lead', self.judge(failing)), \
                mock.patch.object(batch, 'score_batch', self.fake_score_batch):
            await batch.execute_run(run, LLMStub(), jev)

    async def test_jev_outage_falls_back_to_llm_and_opens_breaker(self):
        run = make_run(10)
        calls = []
        await self.execute(run, JEV, lambda person: calls.append(person['id']) or True)
        self.assertEqual(len(calls), JEV.breaker_failures)
        self.assertTrue(run['fallback']['circuit_opened'])
        self.assertEqual(run['fallback']['leads'], 10)
        self.assertEqual({item['decided_by'] for item in run['results']}, {'llm_fallback'})
        self.assertEqual((run['status'], run['matched'], run['failed'], run['fallback_count']), ('completed', 10, 0, 10))
        self.assertTrue(all(fallback for fallback, _ in self.llm_batches))

    async def test_only_failed_leads_fall_back(self):
        run = make_run(4)
        await self.execute(run, JEV, lambda person: person['id'] == 'c2:0')
        decided = {item['person']['id']: item['decided_by'] for item in run['results']}
        self.assertEqual(decided, {'c0:0': 'jev', 'c1:0': 'jev', 'c2:0': 'llm_fallback', 'c3:0': 'jev'})
        self.assertFalse(run['fallback']['circuit_opened'])
        self.assertEqual(self.llm_batches, [(True, ['c2:0'])])

    async def test_fallback_disabled_marks_failures(self):
        run = make_run(2)
        await self.execute(run, dataclasses.replace(JEV, fallback='none'), lambda person: True)
        self.assertEqual(self.llm_batches, [])
        self.assertEqual((run['status'], run['failed']), ('failed', 2))
        self.assertTrue(all('529' in item['error'] for item in run['results']))

    async def test_llm_run_is_labelled(self):
        run = make_run(3, decision_model='llm')
        await self.execute(run, None, lambda person: True)
        self.assertEqual({item['decided_by'] for item in run['results']}, {'llm'})
        self.assertEqual(run['fallback_count'], 0)


if __name__ == '__main__':
    unittest.main()
