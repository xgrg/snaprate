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

define("port", default=8890, help="run on the given port", type=int)

tn = 'HasNormalSubfieldVolumes'
test_names = ['HasNormalSubfieldVolumes', 'HasAllSubfields']

def collect_snapshots(fp='/tmp/snapshots.json'):
    '''Build a dict made of lists of snapshots per each subject.
    Every subject should have a list of same size and every list is shuffled.
    The resulting dictionary is stored in `fp`. If this file `fp` exists
    already, then load its content instead of recollecting new lists.
    '''
    snapshots = {}

    if not op.isfile(fp):
        dd = op.join('/'.join(op.abspath(__file__).split('/')[:-3]), 'web')

        ft = op.join(dd, 'images', 'snapshots', 'ashs', '*%s*.jpg')
        subjects = ['_'.join(op.basename(e)[6:].split('_')[:2]) for e in glob(ft%'*')]
        print(subjects)

        json.dump(subjects, open('/tmp/subjects.json','w'))
        #subjects = json.load(open('/tmp/subjects.json'))

        log.info('Collecting snapshots and shuffling. (%s)'%ft)
        for s in subjects:
            snapshots[s] = []
            fn = ft%(s)
            snapshots[s].append(glob(fn)[0][len(dd):][1:])
        json.dump(snapshots, open(fp, 'w'), indent=4)
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
        users = ['greg', 'gemma', 'raffaele', 'oriol', 'gonzalo', 'juando',
            'carles', 'jordi', 'mahnaz', 'anna', 'eider', 'natalia', 'joseluis',
             'karine', 'marc', 'mmila', 'mcrous', 'aleix', 'chema']
        log.info('Default users: %s'%users)
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

        file_name = '/tmp/scores_%s.xls'%username
        buf_size = 4096
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename=' + op.basename(file_name))
        with open(file_name, 'rb') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                self.write(data)
        self.finish()


def find_next_bad(subject, tests):
    subjects = json.load(open('/tmp/subjects.json'))

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
        subjects = json.load(open('/tmp/subjects.json'))
        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.snapshots.keys())

        log.info(self.scores)
        log.info('User %s has given following scores: %s'
            %(username, self.scores[username]))
        score = self.get_argument("score", None)
        comments = self.get_argument("comments", None)
        subject = int(self.get_argument("subject", None))
        then = self.get_argument("then", None)

        log.info('%s was given %s (out of %s) (comments: %s)'
            %(subject, score, n_subjects, comments))
        self.scores[username][subject] = [score, comments]

        fn = '/tmp/scores_%s.xls'%username
        log.info('Writing %s...'%fn)
        data = []
        for s, v in self.scores[username].items():
            row = [s]
            row.extend(v)
            data.append(row)
        columns = ['ID', 'score', 'comments']
        pd.DataFrame(data, columns=columns).set_index('ID').sort_index().to_excel(fn)

        if then == 'next':
            subject = subject + 1 if subject < n_subjects else 1
        elif then == 'prev':
            subject = subject - 1 if subject > 1 else n_subjects
        elif then == 'nextbad':
            subject = find_next_bad(subject, self.tests)

        log.info('User %s has given following scores: %s'
            %(username, self.scores[username]))

        score, comments = self.scores[username].get(subject, ['', ''])
        res = [score, comments, username, subject]

        if not self.tests is None:


            test = str(self.tests.loc[subjects[subject-1]][tn])
            c = [str(self.tests.loc[subjects[subject-1]][each]) for each in test_names]

            res.append(test)
            res.append([(i,j) for i,j in zip(test_names, c)])

        log.info('Next subject: %s (%s) (%s)'
            %(subject, score, comments))
        self.write(json.dumps(res))

    def initialize(self, scores, snapshots, tests):
        self.scores = scores
        self.snapshots = snapshots
        self.tests = tests

class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):

        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.snapshots.keys())
        id = int(self.get_argument('id', 1))
        #wd = int(self.get_argument('wd', 'snapshots'))

        fn = '/tmp/scores_%s.xls'%username
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
            self.scores[username] = data
            value, comment = self.scores[username].get(id, ['',''])

        else:
            self.scores[username] = {}
            value, comment = ('', '')


        subjects = json.load(open('/tmp/subjects.json'))

        if not self.tests is None:
            test = self.tests.loc[subjects[id-1]][tn]
            c = [self.tests.loc[subjects[id-1]][each] for each in test_names]
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

        for i, s in enumerate(subjects):
            imgs = self.snapshots[s]
            for j, img in enumerate(imgs):
                img_code = '<img class="subject subject%s" id="image%s" '\
                    'src="%s">'\
                    %(i+1, j+1, self.static_url(img))
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
                    <input class="form-control" type="text" name="lname" value="{comment}">
                </div>
                <div class="container">
                    <a class="btn btn-primary" id="prevsubj" href="">
                        previous subject</a>
                    <a class="btn btn-primary" id="nextsubj" href="">
                        next subject</a>
                    <a class="btn btn-info" id="download" href="download/">
                        download</a>
                    <a class="btn btn-danger" id="logout" href="/auth/logout/">
                        logout</a>
                </div>
        '''
        color_btn = {-1: 'danger', '' : 'light', 1: 'warning', 0:'success'}[value]
        code = code.format(html=html, id=id, n_subjects=n_subjects,
            test_section=test_section,
            username=username, color_btn=color_btn, comment=comment)
        args = {'danger':'', 'datasource':'', 'database':'/tmp',
            'rate_subjects': code,
            'n_subjects': n_subjects,
            'visible_subject': id}

        log.info('User %s has given following scores: %s'
            %(username, self.scores[username]))
        self.render("html/index.html", username = username, **args)

    def initialize(self, scores, snapshots, tests):
        self.scores = scores
        self.snapshots = snapshots
        self.tests = tests

class XNATHandler(BaseHandler):
    def post(self):
        src = self.get_argument('src')
        import os.path as op
        eid = '_'.join(op.basename(src).split('?')[0][6:].split('_')[:2])
        print(eid)
        url = 'https://barcelonabrainimaging.org/data/'\
            'experiments/%s?format=html' % eid
        print(url)
        self.write('"%s"'%eid)

    def initialize(self, scores, snapshots, tests):
        self.scores = scores
        self.snapshots = snapshots
        self.tests = tests

class Application(tornado.web.Application):
    def __init__(self, args):
        self.scores = {}
        self.tests = None if args.data is None else\
            pd.read_excel(args.data).set_index('ID')

        self.snapshots = collect_snapshots()
        log.info('Images: %s'%self.snapshots)

        handlers = [
            (r"/", MainHandler, dict(snapshots=self.snapshots, scores=self.scores, tests=self.tests)),
            (r"/auth/login/", AuthLoginHandler),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/post/", PostHandler, dict(snapshots=self.snapshots, scores=self.scores, tests=self.tests)),
            (r"/xnat/", XNATHandler, dict(snapshots=self.snapshots, scores=self.scores, tests=self.tests)),
            (r"/download/", DownloadHandler)

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


def main(args):
    http_server = tornado.httpserver.HTTPServer(Application(args))
    http_server.listen(args.port)

    t = tornado.ioloop.IOLoop.instance()
    t.start()


import argparse
import pandas as pd


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='sample argument')
    parser.add_argument('--data', required=False, default=None)
    parser.add_argument('--port', required=False, default=8890)
    args = parser.parse_args()
    main(args)
