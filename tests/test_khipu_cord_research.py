# SPDX-License-Identifier: Apache-2.0
"""Finite controls for modern Khipu-inspired reconciliation; not historical claims."""
from __future__ import annotations

import copy
import json
import random
from pathlib import Path
import tempfile
import unittest

from research.khipu_math.audit_cli import main as audit_main
from research.khipu_math.cord_witness import (
    SCHEMA, PRIME, TEST_PRIME, CordError, validate, load_record, commitment,
    encode_decimal, decode_decimal, fingerprint, root_collision_bound,
    compare_committed,
)


def sample():
    return {'schema': SCHEMA, 'scope': 'synthetic-census', 'source_revision': 'a' * 40,
            'rights_class': 'SYNTHETIC', 'units': 'counts', 'top_total': 400,
            'children': [{'cord': 'p1', 'value': 120},
                         {'cord': 'p2', 'value': 250},
                         {'cord': 'p3', 'value': 30}]}


class KhipuResearchTests(unittest.TestCase):
    def test_exact_reference_reconciles_but_grants_no_authority(self):
        s = sample()
        r = compare_committed(s, copy.deepcopy(s), expected_reference_sha256=commitment(s), challenge=7)
        self.assertEqual(r['state'], 'RECONCILED_FIXED_REFERENCE')
        self.assertTrue(r['reference_conserved'] and r['candidate_conserved'])
        self.assertTrue(r['exact_content_match'])
        self.assertFalse(r['independent_custody_proved'])
        self.assertFalse(r['history_decipherment_proved'])
        self.assertFalse(r['model_evaluated'])
        self.assertEqual(r['action_authority'], 'NONE')

    def test_decimal_examples_historic_numeric_classification_only(self):
        self.assertEqual(encode_decimal(0), [])
        self.assertEqual(encode_decimal(1), [{'place': 0, 'kind': 'figure_eight', 'count': 1}])
        self.assertEqual(encode_decimal(135), [
            {'place': 0, 'kind': 'long', 'count': 5},
            {'place': 1, 'kind': 'single', 'count': 3},
            {'place': 2, 'kind': 'single', 'count': 1},
        ])
        self.assertEqual(decode_decimal(encode_decimal(135)), 135)

    def test_exhaustive_0_to_9999_round_trip(self):
        for n in range(10000):
            self.assertEqual(decode_decimal(encode_decimal(n)), n)

    def test_roundtrip_large_known_place_values(self):
        for n in (10**k for k in range(12)):
            self.assertEqual(decode_decimal(encode_decimal(n)), n)

    def test_invalid_decimal_token_spoofed_or_duplicated(self):
        for tokens in (
            [{'place': 0, 'kind': 'single', 'count': 1}],
            [{'place': 1, 'kind': 'figure_eight', 'count': 1}],
            [{'place': 0, 'kind': 'long', 'count': 1}],
            [{'place': 0, 'kind': 'long', 'count': 2}] * 2,
            [{'place': -1, 'kind': 'single', 'count': 1}],
            [{'place': 12, 'kind': 'single', 'count': 1}],
            [{'place': 0, 'kind': 'long', 'count': True}],
            [{'place': 2, 'kind': 'single', 'count': 0}],
            [{'place': 3, 'kind': 'single', 'count': 10}],
            [{'place': 0, 'kind': 'long', 'count': 2, 'payload': 'secret'}],
        ):
            with self.subTest(tokens=tokens), self.assertRaises(CordError):
                decode_decimal(tokens)

    def test_scope_and_mutability(self):
        s = sample()
        v = validate(s)
        self.assertEqual(s, v)
        self.assertIsNot(s, v)
        s['children'][0]['value'] = 999
        self.assertEqual(v['children'][0]['value'], 120)

    def test_duplicate_children_and_wrong_types_denied(self):
        variants = []
        for f in ('schema', 'scope', 'source_revision', 'rights_class', 'units', 'top_total', 'children'):
            s = sample(); del s[f]; variants.append(s)
        for k, v in [('extra', 'false'), ('top_total', False), ('children', []),
                     ('scope', '<html>'), ('rights_class', 'PRIVATE'),
                     ('source_revision', 'main'), ('rights_class', [])]:
            s = sample(); s[k] = v; variants.append(s)
        s = sample(); s['children'][1]['cord'] = 'p1'; variants.append(s)
        s = sample(); s['children'][0]['value'] = -1; variants.append(s)
        s = sample(); s['children'][0]['value'] = 1.5; variants.append(s)
        s = sample(); s['children'][0]['value'] = True; variants.append(s)
        for row in variants:
            with self.subTest(row=row), self.assertRaises(CordError):
                validate(row)

    def test_load_json_duplicate_keys_nonfinite_and_byte_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'cord.json'
            for raw in ('{"schema":1,"schema":2}', '{"top_total":NaN}', 'x' * 24577):
                p.write_text(raw)
                with self.assertRaises(CordError):
                    load_record(p)
            p.write_text(json.dumps(sample()))
            self.assertEqual(load_record(p), validate(sample()))

    def test_conserved_total_can_still_hide_reallocation(self):
        s = sample(); b = copy.deepcopy(s)
        b['children'][0]['value'] += 5
        b['children'][1]['value'] -= 5
        self.assertEqual(sum(x['value'] for x in s['children']), sum(x['value'] for x in b['children']))
        r = compare_committed(s, b, expected_reference_sha256=commitment(s), challenge=13)
        self.assertEqual(r['state'], 'DENY_REFERENCE_OR_CONSERVATION_MISMATCH')
        self.assertTrue(r['reference_conserved'] and r['candidate_conserved'])
        self.assertFalse(r['exact_content_match'])
        self.assertFalse(r['challenge_fingerprint_match'])

    def test_fingerprint_collision_cannot_override_exact_digest(self):
        s = sample(); b = copy.deepcopy(s)
        b['children'][0]['value'] += 1
        b['children'][1]['value'] -= 1
        # r=1 exposes a deliberate collision for equal-total vectors.
        r = compare_committed(s, b, expected_reference_sha256=commitment(s), challenge=1)
        self.assertTrue(r['challenge_fingerprint_match'])
        self.assertFalse(r['exact_content_match'])
        self.assertTrue(r['candidate_conserved'])
        self.assertEqual(r['state'], 'DENY_REFERENCE_OR_CONSERVATION_MISMATCH')

    def test_tampered_trusted_expected_reference_denied(self):
        with self.assertRaisesRegex(CordError, 'REFERENCE_COMMITMENT_MISMATCH'):
            compare_committed(sample(), sample(), expected_reference_sha256='b' * 64, challenge=13)

    def test_scope_revision_rights_and_cord_order_denied(self):
        s = sample()
        for field, value in (('scope', 'other'), ('source_revision', 'b' * 40),
                             ('rights_class', 'PUBLIC_RIGHTS_DECLARED'), ('units', 'other')):
            bad = copy.deepcopy(s); bad[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(CordError, 'SCOPE_OR_REVISION_MISMATCH'):
                compare_committed(s, bad, expected_reference_sha256=commitment(s), challenge=3)
        b = copy.deepcopy(s); b['children'].reverse()
        with self.assertRaisesRegex(CordError, 'CORD_ORDER_OR_COVERAGE_MISMATCH'):
            compare_committed(s, b, expected_reference_sha256=commitment(s), challenge=3)

    def test_exhaustive_101_prime_two_cord_root_bound(self):
        # Nonzero (x-y) = (1,-1): polynomial 1-r; exactly one root.
        ref = (40, 50); altered = (41, 49)
        collisions = sum(fingerprint(ref, r, TEST_PRIME) == fingerprint(altered, r, TEST_PRIME)
                         for r in range(TEST_PRIME))
        self.assertEqual(collisions, 1)
        bound = root_collision_bound(2, TEST_PRIME)
        self.assertEqual((bound['numerator'], bound['denominator']), (1, TEST_PRIME))
        self.assertLessEqual(collisions, bound['numerator'])

    def test_multi_record_finite_root_upper_bound(self):
        rng = random.Random(20261117)
        for n in range(2, 13):
            for trial in range(40):
                a = [rng.randrange(0, TEST_PRIME) for _ in range(n)]
                b = a.copy()
                k = rng.randrange(n)
                b[k] = (b[k] + rng.randint(1, TEST_PRIME - 1)) % TEST_PRIME
                collisions = sum(fingerprint(a, r, TEST_PRIME) == fingerprint(b, r, TEST_PRIME)
                                 for r in range(TEST_PRIME))
                self.assertLessEqual(collisions, n - 1, (n, trial, collisions))

    def test_not_a_signature_or_trained_model(self):
        report = compare_committed(sample(), sample(), expected_reference_sha256=commitment(sample()), challenge=99)
        self.assertNotIn('signed', report)
        self.assertEqual(report['action_authority'], 'NONE')
        self.assertIn('uniform post-commit challenge', report['collision_bound_if_fixed_distinct']['hypotheses'])

    def test_cli_append_only_private_receipt_and_mismatch_exit(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            reference = folder / 'reference.json'
            candidate = folder / 'candidate.json'
            reference.write_text(json.dumps(sample()), encoding='utf-8')
            candidate.write_text(json.dumps(sample()), encoding='utf-8')
            out = folder / 'receipt.json'
            args = ['--reference', str(reference), '--candidate', str(candidate),
                    '--expected-reference-sha256', commitment(sample()),
                    '--challenge', '7', '--out', str(out)]
            self.assertEqual(audit_main(args), 0)
            rows = json.loads(out.read_text())
            self.assertEqual(rows['training_authority'], 'NONE')
            self.assertEqual(rows['comparison']['state'], 'RECONCILED_FIXED_REFERENCE')
            before = out.read_bytes()
            self.assertEqual(audit_main(args), 2)  # exclusive output creation
            self.assertEqual(out.read_bytes(), before)
            b = sample(); b['children'][0]['value'] += 1
            b['children'][1]['value'] -= 1
            candidate.write_text(json.dumps(b), encoding='utf-8')
            denied_out = folder / 'denied.json'
            changed = args[:-1] + [str(denied_out)]
            self.assertEqual(audit_main(changed), 3)
            self.assertEqual(json.loads(denied_out.read_text())['comparison']['state'],
                             'DENY_REFERENCE_OR_CONSERVATION_MISMATCH')

    def test_cli_invalid_source_pin_stops_without_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            p = folder / 'data.json'; p.write_text(json.dumps(sample()))
            out = folder / 'none.json'
            self.assertEqual(audit_main(['--reference', str(p), '--candidate', str(p),
                                          '--expected-reference-sha256', 'wrong',
                                          '--challenge', '7', '--out', str(out)]), 2)
            self.assertFalse(out.exists())

    def test_invalid_field_challenges(self):
        for challenge in (-1, PRIME, 1.2, True, '1'):
            with self.subTest(challenge=challenge), self.assertRaises(CordError):
                fingerprint([1, 2], challenge)
        for values in ([], [True], [PRIME], [-1], ['1']):
            with self.subTest(values=values), self.assertRaises(CordError):
                fingerprint(values, 1)
        with self.assertRaises(CordError):
            fingerprint([1], 0, 100)  # composite/unreviewed modulus


if __name__ == '__main__':
    unittest.main()
