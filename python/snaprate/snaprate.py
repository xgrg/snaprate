import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import pandas as pd
import settings
from glob import glob
import random
import os.path as op
import json
from tornado.options import define, options
import logging as log

define("port", default=8891, help="run on the given port", type=int)


def collect_snapshots(fp='/tmp/snapshots.json'):
    '''Build a dict made of lists of snapshots per each subject.
    Every subject should have a list of same size and every list is shuffled.
    The resulting dictionary is stored in `fp`. If this file `fp` exists
    already, then load its content instead of recollecting new lists.
    '''
    snapshots = {}
    subjects = [10019, 10065, 10070, 10200, 10235, 10245, 10515, 10724,
        10779, 11042, 11114, 11127, 11248, 11257, 11262, 11387, 11478, 11593,
        11656, 11711, 11829, 12279, 12304, 12308, 12778, 13035, 13059, 13105,
        13244, 44660, 55630]

    if not op.isfile(fp):
        dd = op.join('/'.join(op.abspath(__file__).split('/')[:-3]), 'web')

        ft = op.join(dd, 'images', 'snapshots', 'FS6%s', 'snapshot_%s.png')

        log.info('Collecting snapshots and shuffling. (%s)'%ft)
        for s in subjects:
            snapshots[s] = []
            modes = ['', '-T1IR', '-T1T2']
            random.shuffle(modes)
            for mode in modes:
                fn = ft%(mode, s)
                snapshots[s].append(glob(fn)[0][len(dd):][1:])
        json.dump(snapshots, open(fp,'w'), indent=4)
        log.info('Saving file %s...'%fp)

    else:
        log.info('Reading existing file %s...'%fp)
        snapshots = json.load(open(fp))

    return snapshots


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("user")


class AuthLogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("user")
        self.redirect(self.get_argument("next", "/"))


class AuthLoginHandler(BaseHandler):
    def get(self):
        try:
            errormessage = self.get_argument("error")
        except:
            errormessage = ""
        self.render("html/login.html", errormessage = errormessage)

    def check_permission(self, password, username):
        users = ['greg', 'raffaele', 'oriol', 'gonzalo', 'juando', 'carles']
        log.info('Default users: %s'%users)
        for each in users:
            if username == each and password == each:
                return True
        return False

    def post(self):
        username = self.get_argument("username", "")
        password = self.get_argument("password", "")
        auth = self.check_permission(password, username)
        if auth:
            self.set_current_user(username)
            self.redirect(self.get_argument("next", u"/"))
        else:
            error_msg = u"?error=" + tornado.escape.url_escape("Login incorrect")
            self.redirect(u"/auth/login/" + error_msg)

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")


class PostHandler(BaseHandler):
    def post(self):
        username = self.current_user[1:-1]
        n_subjects = len(self.snapshots.keys())
        n_snapshots = 3
        log.info('User %s has given following scores: %s'
            %(username, self.scores[username]))
        rankings = self.get_argument("rankings", None)
        subject = int(self.get_argument("subject", None))
        then = self.get_argument("then", None)

        log.info('%s has given %s (out of %s)'%(subject, rankings, n_subjects))
        self.scores[username][subject] = rankings

        fn = '/tmp/scores_%s.xls'%username
        log.info('Writing %s...'%fn)
        pd.DataFrame.from_dict(self.scores[username], orient='index').to_excel(fn)

        if then == 'next':
            subject = subject + 1 if subject < n_subjects else 1
        elif then == 'prev':
            subject = subject - 1 if subject > 1 else n_subjects

        log.info('User %s has given following scores: %s'
            %(username, self.scores[username]))

        ns = self.scores[username].get(subject, '')
        log.info('Next subject: %s (%s)'
            %(subject, ns))
        self.write('["%s","%s"]'%(ns, username))

    def initialize(self, scores, snapshots):
        self.scores = scores
        self.snapshots = snapshots


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        username = self.current_user[1:-1]
        n_subjects = len(self.snapshots.keys())
        n_snapshots = 3

        fn = '/tmp/scores_%s.xls'%username
        log.info('Reading %s...'%fn)
        if op.isfile(fn):
            x = pd.read_excel(fn, converters={0:int}).dropna().to_dict()[0]
            self.scores[username] = x
        else:
            self.scores[username] = {}

        value = self.scores[username].get(1, '')

        html = ''
        for i, (s, imgs) in enumerate(self.snapshots.items()):
            for j, img in enumerate(imgs):
                img_code = '<img class="subject%s" id="image%s" '\
                    'style="height:900px; width:1250px; display:none" src="%s">'\
                    %(i+1, j+1, self.static_url(img))
                html = html + img_code

        code = '''<div class="container">%s</div>
                <div class="container">
                    <a class="btn btn-primary" id="prevsnap" href="">
                        previous snapshot</a>
                    <a class="btn btn-primary" id="nextsnap" href="">
                        next snapshot</a>
                    <button class="btn btn-info">
                        subject #
                        <span class="badge badge-light" id="subject_number">1</span>
                        /<span class="badge badge-light">%s</span>
                    </button>
                    <button class="btn btn-info">snapshot #
                        <span class="badge badge-light" id="image_number">1</span>
                    </button>
                    <span class="badge badge-light" id="username">%s</span>
                    <span class="success" style="display:none">SAVED</span>
                    <span class="skipped" style="display:none">SKIPPED</span>
                </div>
                <div class="container">
                    <input class="form-control" type="text" name="lname" value="%s">
                </div>
                <div class="container">
                    <a class="btn btn-primary" id="prevsubj" href="">
                        previous subject</a>
                    <a class="btn btn-primary" id="nextsubj" href="">
                        next subject</a>
                    <a class="btn btn-danger" id="logout" href="/auth/logout/">
                        logout</a>
                </div>
        '''

        code = code%(html, n_subjects, username, value)
        args = {'danger':'', 'datasource':'', 'database':'/tmp',
            'rate_subjects': code,
            'n_subjects': n_subjects,
            'n_snapshots': n_snapshots}

        log.info('User %s has given following scores: %s'
            %(username, self.scores[username]))
        self.render("html/index.html", username = username, **args)

    def initialize(self, scores, snapshots):
        self.scores = scores
        self.snapshots = snapshots


class Application(tornado.web.Application):
    def __init__(self):
        self.scores = {}
        self.snapshots = collect_snapshots()
        log.info('Images: %s'%self.snapshots)

        handlers = [
            (r"/", MainHandler, dict(snapshots=self.snapshots, scores=self.scores)),
            (r"/auth/login/", AuthLoginHandler),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/post/", PostHandler,  dict(snapshots=self.snapshots, scores=self.scores))
        ]
        s = {
            "autoreload":False,
            "template_path":settings.TEMPLATE_PATH,
            "static_path":settings.STATIC_PATH,
            "debug":settings.DEBUG,
            "cookie_secret": settings.COOKIE_SECRET,
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers, autoescape=None, **s)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
