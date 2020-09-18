import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from snaprate import settings
import os.path as op
import logging as log
from .collect import collect_tests, collect_subjects, collect_snapshots
from .handlers import (MainHandler, AuthLoginHandler, AuthLogoutHandler,
                       PostHandler, StatsHandler, XNATHandler, DownloadHandler,
                       My404Handler)


class Application(tornado.web.Application):
    def __init__(self, args):
        self.scores = {}
        wd = op.abspath(args.data)
        log.info('Data directory: %s' % wd)

        self.subjects = collect_subjects(wd)
        self.tests = collect_tests(wd)
        self.snapshots = collect_snapshots(wd, self.subjects)

        params = {'subjects': self.subjects,
                  'snapshots': self.snapshots,
                  'scores': self.scores,
                  'tests': self.tests,
                  'wd': wd}

        handlers = [
            (r"/", MainHandler, params),
            (r"/auth/login/", AuthLoginHandler, dict(wd=wd)),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/post/", PostHandler, params),
            (r"/stats/", StatsHandler, params),
            (r"/xnat/", XNATHandler, params),
            (r"/download/", DownloadHandler, dict(wd=wd))]

        s = {
            "autoreload": False,
            "template_path": settings.TEMPLATE_PATH,
            "static_path": settings.STATIC_PATH,
            "debug": settings.DEBUG,
            "cookie_secret": settings.COOKIE_SECRET,
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers,
                                         default_handler_class=My404Handler,
                                         autoescape=None, **s)
