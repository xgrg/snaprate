import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from snaprate import settings
import os.path as op
import logging as log
from .collect import collect_tests, collect_subjects, collect_h5
from .handlers import (MainHandler, AuthLoginHandler, AuthLogoutHandler,
                       PostHandler, StatsHandler, XNATHandler, DownloadHandler,
                       My404Handler, PipelineHandler)


class Application(tornado.web.Application):
    def __init__(self, args):
        self.scores = {}
        import pandas as pd
        import json
        from snaprate import settings
        fp = op.join(settings.STATIC_PATH, 'annotations.xlsx')
        if op.isfile(fp):
            df = pd.read_excel(fp, converters={'score': str}, engine='openpyxl').set_index('fp')
            for i, row in df.iterrows():
                r = []
                for e in row.to_list():
                    aux = '' if pd.isna(e) else e
                    r.append(aux)
                r2 = r[:-2]
                r2.append(json.loads(r[-2]))
                print('poly', r2[-1])
                r2.append(r[-1])

                self.scores[i] = r2
        print(self.scores)

        wd = op.abspath(args.data)
        log.info('Data directory: %s' % wd)

        # self.subjects = collect_subjects(wd)
        # self.tests = collect_tests(wd)
        self.h5 = collect_h5(wd) #, self.subjects)

        params = {#'subjects': self.subjects,
                  'h5': self.h5,
                  'scores': self.scores,
                  #'tests': self.tests,
                  'wd': wd}

        handlers = [
            (r"/", MainHandler, params),
            (r"/auth/login/", AuthLoginHandler, dict(wd=wd)),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/post/", PostHandler, params),
            (r"/pipelines/", PipelineHandler, params),
            (r"/stats/", StatsHandler, params),
            (r"/xnat/", XNATHandler, params),
            (r"/download/", DownloadHandler, dict(wd=wd))]

        s = {
            "autoreload": True,
            "template_path": settings.TEMPLATE_PATH,
            "static_path": settings.STATIC_PATH,
            "debug": settings.DEBUG,
            "cookie_secret": settings.COOKIE_SECRET,
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers,
                                         default_handler_class=My404Handler,
                                         autoescape=None, **s)
