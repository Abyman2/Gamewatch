'''
Test Suite: Cloudflare D1 Integration & Fast Local Hydration
============================================================
Author: TSEGA Labs
'''

import unittest
import json
import sqlite3
import os
import sys

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from unittest import mock

for mod in ['cv2', 'numpy', 'flask', 'werkzeug']:
    try:
        __import__(mod)
    except ImportError:
        sys.modules[mod] = mock.MagicMock()

import cloudflare_d1





class TestCloudflareD1Integration(unittest.TestCase):

    def setUp(self):
        self.client = cloudflare_d1.CloudflareD1Client()


    def test_client_configuration_check(self):
        '''Test that unconfigured client behaves gracefully without throwing exceptions.'''
        # With empty credentials
        empty_client = cloudflare_d1.CloudflareD1Client('', '', '')
        self.assertFalse(empty_client.is_configured())

        test_res = empty_client.test_connection()
        self.assertFalse(test_res['success'])
        self.assertEqual(test_res['status'], 'NOT_CONFIGURED')

    def test_schema_statements_validity(self):
        '''Test that all 16 schema DDL statements are valid SQLite syntax.'''
        test_conn = sqlite3.connect(':memory:')
        cur = test_conn.cursor()

        for idx, stmt in enumerate(cloudflare_d1.SCHEMA_DDL):
            try:
                cur.executescript(stmt)
            except Exception as e:
                self.fail(f'Failed executing schema statement {idx}: {e}\nSQL:\n{stmt}')

        cur.execute('SELECT count(*) FROM sqlite_master WHERE type=\'table\' AND name NOT LIKE \'sqlite_%\'')
        table_count = cur.fetchone()[0]
        self.assertGreaterEqual(table_count, 15, 'All core tables must be created in memory.')
        test_conn.close()

    def test_api_system_d1_telemetry(self):
        '''Test Cloudflare D1 telemetry output structure.'''
        telemetry = self.client.get_cloud_telemetry()
        self.assertIn('status', telemetry)
        self.assertIn('configured', telemetry)
        self.assertFalse(telemetry['configured'])
        self.assertEqual(telemetry['status'], 'LOCAL_SQLITE_MODE')

    def test_sync_unconfigured_rejection(self):
        '''Test that attempting to sync without credentials safely rejects.'''
        empty_client = cloudflare_d1.CloudflareD1Client('', '', '')
        res = empty_client.push_local_to_d1('gamewatch.db')
        self.assertFalse(res['success'])
        self.assertIn('not configured', res['error'].lower())


    def test_response_envelope_parsing(self):
        '''Test that Cloudflare v4 envelope formats are parsed properly.'''
        dummy_client = cloudflare_d1.CloudflareD1Client('acc', 'db', 'tok')

        # Mock successful list format
        mock_resp_list = {
            'result': [{
                'results': [{'id': 1, 'name': 'TV 1'}],
                'success': True,
                'meta': {'changes': 0}
            }],
            'success': True
        }
        dummy_client._request = lambda endpoint, payload: mock_resp_list

        query_out = dummy_client.execute_query('SELECT * FROM tvs')
        self.assertTrue(query_out['success'])
        self.assertEqual(len(query_out['rows']), 1)
        self.assertEqual(query_out['rows'][0]['name'], 'TV 1')

        # Mock successful dict format
        mock_resp_dict = {
            'result': {
                'results': [{'id': 2, 'name': 'TV 2'}],
                'success': True,
                'meta': {'changes': 0}
            },
            'success': True
        }
        dummy_client._request = lambda endpoint, payload: mock_resp_dict

        query_out2 = dummy_client.execute_query('SELECT * FROM tvs')
        self.assertTrue(query_out2['success'])
        self.assertEqual(len(query_out2['rows']), 1)
        self.assertEqual(query_out2['rows'][0]['name'], 'TV 2')


if __name__ == '__main__':
    unittest.main()
