from tornado.testing import AsyncTestCase, AsyncHTTPTestCase
import argparse
from snaprate.server import main, create_parser, MainHandler
import mock
from urllib.parse import urlencode


class UserAPITest(AsyncHTTPTestCase):
    def get_app(self):
        self.app = Application([('/', MainHandler)])
        return self.app


class TestSnaprateApp(AsyncHTTPTestCase):
    def get_app(self):
        parser = create_parser()
        args = parser.parse_args(['-d', 'tests/data', '--port', '8899'])
        server, t = main(args)
        return server

    def test_homepage(self):
        response = self.fetch('/')
        with mock.patch.object(MainHandler, 'get_secure_cookie') as m:
            m.return_value = bytes('"tornado"', 'utf-8')
            response = self.fetch('/', method='GET')
            data = {"score": 0,
               "comments": 'hey',
               "subject":1,
               "pipeline":'toto',
               "then":2}
            response = self.fetch('/post', method='POST', body=urlencode(data))
            print(response.body)
