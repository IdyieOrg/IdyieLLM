import unittest
from app import create_app


class PingTestCase(unittest.TestCase):
    def setUp(self):
        self.app = create_app()
        self.client = self.app.test_client()

    def test_ping_route(self):
        response = self.client.get('/api/ping')

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json, {"message": "pong"})


if __name__ == '__main__':
    unittest.main()
