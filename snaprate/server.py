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
from datetime import datetime

class My404Handler(tornado.web.RequestHandler):
    # Override prepare() instead of get() to cover all possible HTTP methods.
    def prepare(self):
        self.set_status(404)
        self.redirect('/')

def _initialize(self, wd, subjects, scores, snapshots, tests):
    self.wd = wd
    self.subjects = subjects
    self.scores = scores
    self.snapshots = snapshots
    self.tests = tests

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
        types = ''

        fp = op.join(self.wd, 'users.json')
        if not op.isfile(fp):
            msg = '''<img width=16 src="https://upload.wikimedia.org/wikipedia/en/2/28/Information.svg"><span style="color:darksalmon">
                <i>Guest account activated (guest/guest)</i></span>'''
            errormessage = errormessage + '<br>' + msg


        folders = [op.basename(e) for e in glob(op.join(self.wd, '*')) if op.isdir(e)]
        snapshots_types = folders
        for each in snapshots_types:
            types = types + '<li><a href="#" resource="%s">%s</a></li>'%(each, each)
        self.render("html/login.html", errormessage = errormessage, types=types)

    def check_permission(self, password, username):
        fp = op.join(self.wd, 'users.json')
        if not op.isfile(fp):
            log.error('File not found (%s). Using default user: guest'%fp)
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
        resource = str(self.get_argument("resource", ""))

        auth = self.check_permission(password, username)
        if auth:
            self.set_current_user(username)
            self.redirect(u"/?s=%s"%resource)
        else:
            error_msg = u"?error=" + tornado.escape.url_escape("Wrong login/password.")
            self.redirect(u"/auth/login/" + error_msg)

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")

    def initialize(self, wd):
        self.wd = wd

class DownloadHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        username = str(self.current_user[1:-1], 'utf-8')
        wd = self.get_argument('s', None)
        log.info('Snapshot type: %s'%wd)

        fn = op.join(self.wd, wd, 'ratings', 'scores_%s_%s.xls'%(wd, username))
        if not op.isfile(fn):
            self.write('<script>alert("Please review at least one subject before downloading Excel table.")"</script>')
            return

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
    @tornado.web.authenticated
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

        current_subject = self.subjects[wd][subject - 1]


        res = self.scores[wd][username].get(current_subject, ['', '', '', ''])
        old_score, old_comments, _, old_dt = res

        has_changed = not current_subject in self.scores[wd][username].keys() \
            or (old_score != score or old_comments != comments)

        if has_changed:
            dt = datetime.strftime(datetime.now(), '%Y%m%d-%H%M%S')
        else:
            dt = old_dt

        if score != '':
            score = int(score)

        self.scores[wd][username][current_subject] = [score, comments, subject, dt]
        fn = op.join(self.wd, wd, 'ratings', 'scores_%s_%s.xls'%(wd, username))

        if not op.isdir(op.dirname(fn)):
            import os
            log.info('Creating folder %s'%op.dirname(fn))
            os.mkdir(op.dirname(fn))

        log.info('Writing %s...'%fn)
        data = []
        for s, v in self.scores[wd][username].items():
            row = [s]
            row.extend(v)
            data.append(row)
        columns = ['ID', 'score', 'comments', 'index', 'datetime']
        pd.DataFrame(data, columns=columns).set_index('ID').sort_index().to_excel(fn)

        if then == 'next':
            subject = subject + 1 if subject < n_subjects else 1
        elif then == 'prev':
            subject = subject - 1 if subject > 1 else n_subjects
        elif then == 'nextbad':
            subject = find_next_bad(subject, self.tests[wd], self.subjects[wd])

        log.info('User %s has given following scores: %s'
            %(username, self.scores[wd][username]))

        current_subject = self.subjects[wd][subject - 1]

        res = self.scores[wd][username].get(current_subject, ['', '', '', ''])
        score, comments, index, dt = res
        res = [score, comments, username, subject]


        if not self.tests[wd] is None:

            test_names = self.tests[wd].columns
            tn = test_names[0]

            test = str(self.tests[wd].loc[self.subjects[wd][subject-1]][tn])
            c = [str(self.tests[wd].loc[self.subjects[wd][subject-1]][each])\
                for each in test_names]

            res.append(test)
            res.append([(i,j) for i,j in zip(test_names, c)])
            print(res)

        log.info('Next subject: %s (%s) (%s)'
            %(subject, score, comments))
        self.write(json.dumps(res))

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        pipelines = list(self.snapshots.keys())
        wd = self.get_argument('s', pipelines[0])
        folders = [op.basename(e) for e in glob(op.join(self.wd, '*')) \
            if op.isdir(e)]
        if not wd in folders:
            self.clear()
            self.redirect('/')
            return

        log.info('Snapshot type: %s'%wd)

        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.snapshots[wd].keys())
        id = int(self.get_argument('id', 1))

        fn = op.join(self.wd, wd, 'ratings',
            'scores_%s_%s.xls'%(wd, username))
        log.info('Reading %s...'%fn)

        self.scores.setdefault(wd , {})

        if op.isfile(fn):
            x = pd.read_excel(fn, converters={'ID':str, 'score': str}).set_index('ID')
            data = {}
            for i, row in x.iterrows():
                r = []
                for e in row.to_list():
                    aux = '' if pd.isna(e) else e
                    r.append(aux)
                data[i] = r
            self.scores[wd][username] = data
            value, comment, index, dt = self.scores[wd][username].get(self.subjects[wd][id-1], ['', '', '', ''])
        else:
            self.scores[wd][username] = {}
            value, comment = ('', '')

        if not self.tests[wd] is None:
            test_names = self.tests[wd].columns
            tn = test_names[0]

            test = self.tests[wd].loc[self.subjects[wd][id-1]][tn]
            c = [self.tests[wd].loc[self.subjects[wd][id-1]][each] \
                for each in test_names]
            test_unit = '<span href="#" data-toggle="tooltip" class="badge badge-light" id="test%s">%s%s</span>'
            test_section = ''
            for i, (test_key, test_value) in enumerate(zip(test_names, c)):
                if test_value == True:
                    tu = test_unit.replace('badge-light', 'badge-success')
                    test_section += tu%(i, test_key, '')
                elif test_value == False:
                    tu = test_unit.replace('badge-light', 'badge-danger')
                    test_section += tu%(i, test_key, '')
                else:
                    if len(test_value) > 7:
                        test_value = str(test_value)[:7] + '…'
                    tu = test_unit%(i, test_key, ': %s'%test_value)
                    tu = tu.replace(' id', 'title="%s" id'%test_value)
                    test_section += tu



            color_test = {True:'success', False:'danger'}[test]

            test_section = '''<a class="btn btn-secondary" id="nextbad" href="nextbad/">
                Go to next predicted failed case</a>
                <span class="btn btn-{color_test}" id="test">Automatic prediction</span><br>'''.format(color_test=color_test)\
                + test_section
        else:
            test_section = ''

        html = '''<div id="image-gallery">
                  <div class="image-container"></div>
                </div>'''

        images_code = 'images = ['

        for i, s in enumerate(self.subjects[wd]):
            img = self.snapshots[wd][s]
            img_code = '{small: "%s", big: "%s"},'%(self.static_url(img), self.static_url(img))

            images_code = images_code + img_code
        images_code = images_code + '];'
        images_code = images_code + '''wrapper = $("div #image-gallery");
                viewer = new ImageViewer($(".image-container")[0]);
                window.viewer = viewer;'''



        code = '''<div class="container">{html}</div>
                <div class="container">
                    <button class="btn btn-info">
                        subject #
                        <span class="badge badge-light" id="subject_number">{id}</span>
                        /<span class="badge badge-light">{n_subjects}</span>
                    </button>
                    <a class="btn btn-info" id="xnat">Go to XNAT</a>

                    {test_section}

                    <span class="badge badge-secondary" id="username">{username}</span>
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
        print(value)
        if value != '':
            value = int(value)
        color_btn = {-1: 'danger', '' : 'secondary', 1: 'warning', 0:'success'}[value]
        code = code.format(html=html, id=id, n_subjects=n_subjects,
            test_section=test_section, pipeline=wd,
            username=username, color_btn=color_btn, comment=comment)
        args = {'danger':'', 'datasource':'', 'database':'/tmp',
            'rate_subjects': code,
            'n_subjects': n_subjects,
            'visible_subject': id,
            'images':images_code}

        log.info('User %s has given following scores: %s'
            %(username, self.scores[wd][username]))
        self.render("html/index.html", username = username, **args)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


def get_stats(wd, pipeline):

    scores_fn = glob(op.join(wd, pipeline, 'ratings',
        'scores_%s_*.xls'%pipeline))

    subjects = collect_subjects(wd)[pipeline]

    df = [pd.read_excel(e).set_index('ID') for e in scores_fn]
    if len(df) == 0:
        return ('', 0, 0, '')

    names = [e.split('_')[-1].split('.')[0] for e in scores_fn]
    threshold = 140
    columns = ['seen', 'reviewed', 'has_finished', 'failed', 'doubtful',
            'ok', 'commented']

    review = []
    total_reviews = 0
    for e, n in zip(df, names):
        commented = len(e['comments'].dropna())
        e['experiment_id'] = [i for i in list(e.index)]
        vc = e['score'].value_counts()
        failed = vc.loc[-1] if -1 in vc.index else 0
        doubtful = vc.loc[1] if 1 in vc.index else 0
        ok = vc.loc[0] if 0 in vc.index else 0

        reviewed = failed + doubtful + ok
        has_reviewed = reviewed > threshold
        total_reviews = total_reviews + has_reviewed

        row = [len(e), reviewed, has_reviewed, failed, doubtful, ok,
            commented]
        review.append(row)
    review = pd.DataFrame(review,
        columns=columns, index=names).sort_values(by='reviewed',
            ascending=False)
    del review['has_finished']

    # Compiling comments in a table
    comments = []
    for e, n in zip(df, names):
        e['author'] = n
        e = e.dropna()
        comments.append(e)

    if len(comments) != 0:
        comments = pd.concat(comments).sort_index()

        for each in ['datetime', 'experiment_id']:
            del comments[each]

        col1, col2 = [], []
        for i, row in comments.iterrows():
            col1.append('@@@1%s@@@2'%i)
            col2.append('@@@3%s@@@4'%row['index'])

        comments['XNAT'] = col1
        comments['snaprate'] = col2

        del comments['index']
        pd.set_option('display.max_colwidth', -1)

        comments = comments.to_html()
        d = {'@@@1' : '<a href="https://barcelonabrainimaging.org/data/'\
            'experiments/',
             '@@@2' : '?format=html">link</a>',
             '@@@3' : '<a href="/?s=%s&id='%pipeline,
             '@@@4' : '">link</a>'}
        for k, v in d.items():
            comments = comments.replace(k, v)

    for each in ['comments', 'experiment_id', 'index', 'datetime', 'author']:
        for e in df:
            del e[each]

    # Joining ratings from all users in columns. Each row is a subject
    data = df[0]
    for each, name in zip(df[1:], names[1:]):
        data = data.join(each, rsuffix=name, how='outer')
    data = data.rename(columns=dict(zip(list(data.columns), names)))
    data = pd.DataFrame(data, columns=names)

    total_pc = len(data.index[~data.isnull().all(1)]) / float(len(subjects)) * 100.0
    return (review.to_html(), total_pc, total_reviews, comments)

class StatsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):

        pipelines = list(self.snapshots.keys())
        pipeline = self.get_argument('s', None)

        fp = op.join(self.wd, 'users.json')

        if pipeline is None:
            html = ''
            for each in pipelines:
                row = '<div><a href="%s">%s</a>: %s</div><br>'
                res = get_stats(self.wd, each)
                row = row%('/stats/?s=%s'%each, each, '%.2f'%float(res[1]))
                html = html + row

            self.render('html/stats.html', table=html,
                total_counter='', comments='')
            return

        res = get_stats(self.wd, pipeline)
        review, total_pc, total_reviews, comments = res

        total_counter = '''<h2><span class="timer count-title count-number" data-to="{total_pc}"
            data-speed="1500" data-decimals="3"></span><span> % of snapshots
            have been reviewed</span></h2>'''.format(total_pc=total_pc)

        self.render('html/stats.html', table=review,
            total_counter=total_counter, comments=comments)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


class XNATHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        src = self.get_argument('src')
        import os.path as op
        eid = op.basename(src).split('?')[0].split('.')[0]

        url = 'https://barcelonabrainimaging.org/data/'\
            'experiments/%s?format=html' % eid
        self.write('"%s"'%eid)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)

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
            tests[f] = pd.read_excel(fp, converters={'ID':str}).set_index('ID')

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
                if not op.isfile(fp):
                    raise Exception('Snapshot not found %s'%fp)
                snapshots[f][s] = '.' + op.abspath(fp)[len(op.dirname(wd)):]

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
            subjects[f] = sorted(l)
        else:
            subjects[f] = json.load(open(fp))

        log.info('[%s] %s subjects found'%(f, len(subjects[f])))
    return subjects


class Application(tornado.web.Application):
    def __init__(self, args):
        self.scores = {}
        wd = op.abspath(args.d)
        log.info('Data directory: %s'%wd)

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
            (r"/download/", DownloadHandler, dict(wd=wd)) ]

        s = {
            "autoreload": False,
            "template_path": settings.TEMPLATE_PATH,
            "static_path": settings.STATIC_PATH,
            "debug": settings.DEBUG,
            "cookie_secret": settings.COOKIE_SECRET,
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers,
            default_handler_class=My404Handler, autoescape=None, **s)


def main(args):
    http_server = tornado.httpserver.HTTPServer(Application(args))
    http_server.listen(args.port)

    t = tornado.ioloop.IOLoop.instance()
    return http_server, t

def create_parser():
    parser = argparse.ArgumentParser(description='sample argument')
    parser.add_argument('-d', required=False, default='web/data')
    parser.add_argument('--port', required=False, default=8890)
    return parser



if __name__ == "__main__":
    parser = create_parser()
    args = parser.parse_args()
    server, t = main(args)
    t.start()
