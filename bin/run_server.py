import tornado
from snaprate.server import Application
import argparse


def main(args):
    http_server = tornado.httpserver.HTTPServer(Application(args))
    http_server.listen(args.port)

    t = tornado.ioloop.IOLoop.instance()
    return http_server, t


def create_parser():
    parser = argparse.ArgumentParser(description='sample argument')
    parser.add_argument('-d', '--data', help='Path to the data/ folder',
                        required=False, default='web/data')
    parser.add_argument('--port', required=False, default=8890)
    return parser


if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    server, t = main(args)
    t.start()
