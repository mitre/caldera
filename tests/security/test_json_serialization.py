import json
import pickle
import unittest


class TestJsonSerialization(unittest.TestCase):
    def test_json_round_trip(self):
        data = {'agents': [{'paw': 'abc123'}], 'operations': []}
        serialized = json.dumps(data).encode('utf-8')
        deserialized = json.loads(serialized.decode('utf-8'))
        self.assertEqual(data, deserialized)

    def test_json_decode_error_on_pickle(self):
        data = {'key': 'value'}
        pickled = pickle.dumps(data)
        with self.assertRaises((json.JSONDecodeError, UnicodeDecodeError)):
            json.loads(pickled.decode('utf-8'))

    def test_fallback_detects_pickle(self):
        """Verify pickle data can be distinguished from JSON."""
        data = {'agents': []}
        pickled = pickle.dumps(data)
        json_data = json.dumps(data).encode('utf-8')

        # JSON should start with { or [
        self.assertTrue(json_data.startswith(b'{') or json_data.startswith(b'['))
        # Pickle starts with protocol bytes, not valid JSON
        self.assertFalse(pickled.startswith(b'{'))


if __name__ == '__main__':
    unittest.main()
