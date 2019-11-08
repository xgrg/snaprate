import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import pandas as pd
from snaprate import settings
from glob import glob
import random
import os.path as op
import json
from tornado.options import define, options
import logging as log
import argparse


define("port", default=8890, help="run on the given port", type=int)

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
        fp = op.join(self.wd, 'users.json')
        if not op.isfile(fp):
            log.error('File not found (%s). Using default user: guest')
            users = ['guest']
        else:
            users = json.load(open(fp))
        log.info('Known users: %s'%users)

        for each in users:
            if username == each and password == each:
                return True
        return False

    def post(self):
        username = str(self.get_argument("username", ""))
        password = str(self.get_argument("password", ""))
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

class DownloadHandler(BaseHandler):
    def get(self):
        username = str(self.current_user[1:-1], 'utf-8')
        wd = self.get_argument('s', None)
        log.info('Snapshot type: %s'%wd)

        fn = op.join(self.wd, wd, 'ratings', 'scores_%s_%s.xls'%(wd, username))

        buf_size = 4096
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename=' + op.basename(fn))
        with open(fn, 'rb') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                self.write(data)
        self.finish()

    def initialize(self, wd):
        self.wd = wd

def find_next_bad(subject, tests, subjects):
    test_names = tests.columns
    tn = test_names[0]

    failed = sorted([int(subjects.index(e))+1 for e in tests.query('not %s'%tn).index])
    if subject in failed:
        failed.remove(subject)
    failed.append(subject)
    failed = sorted(failed)
    i = failed.index(subject)
    ns = failed[i + 1] if i + 1 < len(failed) else failed[0]
    return ns

class PostHandler(BaseHandler):
    def post(self):

        wd = self.get_argument('pipeline', None)
        log.info('Snapshot type: %s'%wd)
        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.snapshots[wd].keys())

        log.info(self.scores[wd])
        log.info('User %s has given following scores: %s'
            %(username, self.scores[wd][username]))
        score = self.get_argument("score", None)
        comments = self.get_argument("comments", None)
        subject = int(self.get_argument("subject", None))
        then = self.get_argument("then", None)

        log.info('%s (%s) was given %s (out of %s) (comments: %s)'
            %(subject, self.subjects[wd][subject - 1], score, n_subjects, comments))

        self.scores[wd][username][self.subjects[wd][subject-1]] = [score, comments, subject]



        fn = op.join(self.wd, wd, 'ratings', 'scores_%s_%s.xls'%(wd, username))
        log.info('Writing %s...'%fn)
        data = []
        for s, v in self.scores[wd][username].items():
            row = [s]
            row.extend(v)
            data.append(row)
        columns = ['ID', 'score', 'comments', 'index']
        pd.DataFrame(data, columns=columns).set_index('ID').sort_index().to_excel(fn)

        if then == 'next':
            subject = subject + 1 if subject < n_subjects else 1
        elif then == 'prev':
            subject = subject - 1 if subject > 1 else n_subjects
        elif then == 'nextbad':
            subject = find_next_bad(subject, self.tests[wd], self.subjects[wd])

        log.info('User %s has given following scores: %s'
            %(username, self.scores[wd][username]))

        score, comments, index = self.scores[wd][username].get(self.subjects[wd][subject - 1], ['', '', ''])
        res = [score, comments, username, subject]

        if not self.tests is None:

            test_names = self.tests[wd].columns
            tn = test_names[0]

            test = str(self.tests[wd].loc[self.subjects[wd][subject-1]][tn])
            c = [str(self.tests[wd].loc[self.subjects[wd][subject-1]][each])\
                for each in test_names]

            res.append(test)
            res.append([(i,j) for i,j in zip(test_names, c)])

        log.info('Next subject: %s (%s) (%s)'
            %(subject, score, comments))
        self.write(json.dumps(res))

    def initialize(self, wd, subjects, scores, snapshots, tests):
        self.wd = wd
        self.subjects = subjects
        self.scores = scores
        self.snapshots = snapshots
        self.tests = tests


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        pipelines = list(self.snapshots.keys())
        print(pipelines)
        wd = self.get_argument('s', pipelines[0])
        log.info('Snapshot type: %s'%wd)

        print(self.current_user)
        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.snapshots[wd].keys())
        id = int(self.get_argument('id', 1))

        fn = op.join(self.wd, wd, 'ratings',
            'scores_%s_%s.xls'%(wd, username))
        log.info('Reading %s...'%fn)

        if op.isfile(fn):
            x = pd.read_excel(fn).set_index('ID')
            data = {}
            for i, row in x.iterrows():
                r = []
                for e in row.to_list():
                    aux = '' if pd.isna(e) else e
                    r.append(aux)
                data[i] = r
            self.scores.setdefault(wd , {})
            self.scores[wd][username] = data
            value, comment, index = self.scores[wd][username].get(self.subjects[wd][id-1], ['', '', ''])

        else:
            self.scores[wd] = {}
            self.scores[wd][username] = {}
            value, comment = ('', '')

        if not self.tests[wd] is None:
            test_names = self.tests[wd].columns
            tn = test_names[0]

            test = self.tests[wd].loc[self.subjects[wd][id-1]][tn]
            c = [self.tests[wd].loc[self.subjects[wd][id-1]][each] \
                for each in test_names]
            test_unit = '<span class="btn btn-light" id="test%s">%s: %s</span>'
            test_section = ''.join([test_unit%(i, test_key, test_value) \
                for i, (test_key, test_value) in enumerate(zip(test_names, c))])

            color_test = {True:'success', False:'danger'}[test]

            test_section = '''<a class="btn btn-secondary" id="nextbad" href="nextbad/">
                Go to next predicted failed case</a>
                <span class="btn btn-{color_test}" id="test">Automatic prediction</span>'''.format(color_test=color_test)\
                + test_section
        else:
            test_section = ''

        html = ''

        for i, s in enumerate(self.subjects[wd]):
            img = self.snapshots[wd][s]
            img_code = '<img class="subject subject%s" id="image%s" '\
                'src="%s">'\
                %(i+1, 1, self.static_url(img))
            html = html + img_code



        code = '''<div class="container">{html}</div>
                <div class="container">
                    <button class="btn btn-info">
                        subject #
                        <span class="badge badge-light" id="subject_number">{id}</span>
                        /<span class="badge badge-light">{n_subjects}</span>
                    </button>
                    <a class="btn btn-info" id="xnat">Go to XNAT</a>

                    {test_section}

                    <span class="badge badge-light" id="username">{username}</span>
                    <span class="success" style="display:none">SAVED</span>
                    <span class="skipped" style="display:none">SKIPPED</span>
                </div>
                <div class="container">
                    <a class="btn btn-{color_btn}" id="score">Your score</a>
                    <input class="form-control" placeholder="Your comment" type="text" name="lname" value="{comment}">
                </div>
                <div class="container">
                    <a class="btn btn-primary" id="prevsubj" href="">
                        previous subject</a>
                    <a class="btn btn-primary" id="nextsubj" href="">
                        next subject</a>
                    <a class="btn btn-info" id="download" href="download/?s={pipeline}">
                        download</a>
                    <a class="btn btn-danger" id="logout" href="/auth/logout/">
                        logout</a>
                </div>
        '''
        color_btn = {-1: 'danger', '' : 'light', 1: 'warning', 0:'success'}[value]
        code = code.format(html=html, id=id, n_subjects=n_subjects,
            test_section=test_section, pipeline=wd,
            username=username, color_btn=color_btn, comment=comment)
        args = {'danger':'', 'datasource':'', 'database':'/tmp',
            'rate_subjects': code,
            'n_subjects': n_subjects,
            'visible_subject': id}

        log.info('User %s has given following scores: %s'
            %(username, self.scores[wd][username]))
        self.render("html/index.html", username = username, **args)

    def initialize(self, wd, subjects, scores, snapshots, tests):
        self.wd = wd
        self.subjects = subjects
        self.scores = scores
        self.snapshots = snapshots
        self.tests = tests

class XNATHandler(BaseHandler):
    def post(self):
        src = self.get_argument('src')
        print(src)
        import os.path as op
        eid = op.basename(src).split('?')[0].split('.')[0]

        url = 'https://barcelonabrainimaging.org/data/'\
            'experiments/%s?format=html' % eid
        print(url)
        self.write('"%s"'%eid)

    def initialize(self, wd, subjects, scores, snapshots, tests):
        self.wd = wd
        self.subjects = subjects
        self.scores = scores
        self.snapshots = snapshots
        self.tests = tests

def collect_tests(wd):
    folders = [op.basename(e) for e in glob(op.join(wd, '*')) if op.isdir(e)]
    tests = {}
    log.info('=== Summary of tests ===')
    for f in folders:
        fp = op.join(wd, f, '%s.xls'%f)
        if not op.isfile(fp):
            msg = 'File not found (%s)'%fp
            log.warning(msg)
            tests[f] = None
        else:
            tests[f] = pd.read_excel(fp).set_index('ID')

            log.info('[%s] %s subjects found - %s tests'\
                %(f, len(tests[f]), len(tests[f].columns)))
    return tests

def collect_snapshots(wd, subjects):
    folders = [op.basename(e) for e in glob(op.join(wd, '*')) if op.isdir(e)]
    snapshots = {}
    log.info('=== Summary of snapshots ===')
    for f in folders:
        sd = op.join(wd, f, 'snapshots')
        if not op.isdir(sd):
            msg = 'Snapshot directory not found (%s)'%sd
            raise Exception(msg)
        else:
            snapshots[f] = {}
            for s in subjects[f]:
                fp = op.join(sd, '%s.jpg'%s)
                assert(op.isfile(fp))
                snapshots[f][s] = op.abspath(fp)

        log.info('[%s] %s snapshots found'\
            %(f, len(snapshots[f])))

    return snapshots

def collect_subjects(wd):
    folders = [op.basename(e) for e in glob(op.join(wd, '*')) if op.isdir(e)]
    subjects = {}
    log.info('=== Summary of subjects ===')
    for f in folders:
        fp = op.join(wd, f, 'subjects.json')
        if not op.isfile(fp):
            msg = 'File not found (%s). Using default list based on snapshots'%fp
            log.warning(msg)
            l = [op.basename(e).split('.')[0] \
                for e in glob(op.join(wd, f, 'snapshots', '*.jpg'))]
            subjects[f] = l
        else:
            subjects[f] = json.load(open(fp))

        log.info('[%s] %s subjects found'%(f, len(subjects[f])))
    return subjects


class Application(tornado.web.Application):
    def __init__(self, args):
        self.scores = {}
        wd = op.abspath(args.d)

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
            (r"/auth/login/", AuthLoginHandler),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/post/", PostHandler, params),
            (r"/xnat/", XNATHandler, params),
            (r"/download/", DownloadHandler, dict(wd=wd)) ]

        s = {
            "autoreload":False,
            "template_path":settings.TEMPLATE_PATH,
            "static_path":settings.STATIC_PATH,
            "debug":settings.DEBUG,
            "cookie_secret": settings.COOKIE_SECRET,
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers, autoescape=None, **s)


def main(args):
    http_server = tornado.httpserver.HTTPServer(Application(args))
    http_server.listen(args.port)

    t = tornado.ioloop.IOLoop.instance()
    return http_server, t

def create_parser():
    parser = argparse.ArgumentParser(description='sample argument')
    parser.add_argument('-d', required=True)
    parser.add_argument('--port', required=False, default=8890)
    return parser



if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    server, t = main(args)
    t.start()
