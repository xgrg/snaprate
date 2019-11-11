from tornado.testing import AsyncTestCase, AsyncHTTPTestCase
import argparse
from snaprate.server import main, create_parser, MainHandler, BaseHandler
import mock
from urllib.parse import urlencode


class UserAPITest(AsyncHTTPTestCase):
    def get_app(self):
        self.app = Application([('/', MainHandler)])
        return self.app


class TestSnaprateApp(AsyncHTTPTestCase):
    def get_app(self):
        parser = create_parser()
        args = parser.parse_args(['-d', 'web/tests', '--port', '8899'])
        server, t = main(args)
        return server

    def test_homepage(self):

        with mock.patch.object(BaseHandler, 'get_secure_cookie') as m:
            m.return_value = bytes('"tornado"', 'utf-8')
            response = self.fetch('/auth/login/')

            response = self.fetch('/', method='GET')
            data = {'username': 'guest',
               'password': 'guest',
               'resource':'PIPELINE1'}
            response = self.fetch('/auth/login/', method='POST',
                body=urlencode(data))
            response = self.fetch('/')

            for each in ['next', 'prev', 'nextbad']:
                data = {"score": 0,
                   "comments": 'comment',
                   "subject":1,
                   "pipeline":'PIPELINE1',
                   "then":each}
                response = self.fetch('/post/', method='POST',
                    body=urlencode(data))

            response = self.fetch('/download/?s=PIPELINE1', method='GET')
            data = {"src": 'BBRC02_E07373'}
            response = self.fetch('/xnat/', method='POST',
                body=urlencode(data))
            response = self.fetch('/auth/logout/')
