import tornado
from tornado.options import define
import json
import os.path as op
from glob import glob
import logging as log
from snaprate.utils import ScoreManager
from snaprate.utils import HTMLFactory
from snaprate.utils import find_next_bad


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
        except Exception:
            errormessage = ""
        types = ''

        fp = op.join(self.wd, 'users.json')
        if not op.isfile(fp):
            msg = '''<img width=16 src="https://upload.wikimedia.org/wikipedia/en/2/28/Information.svg"><span style="color:darksalmon">
                <i>Guest account activated (guest/guest)</i></span>'''
            errormessage = errormessage + '<br>' + msg

        folders = [op.basename(e) for e in glob(op.join(self.wd, '*'))
                   if op.isdir(e)]
        snapshots_types = folders
        for each in snapshots_types:
            types = types + '<li><a href="#" resource="%s">%s</a></li>'\
                    % (each, each)
        self.render("html/login.html", errormessage=errormessage, types=types)

    def check_permission(self, password, username):
        fp = op.join(self.wd, 'users.json')
        if not op.isfile(fp):
            log.error('File not found (%s). Using default user: guest' % fp)
            users = ['guest']
        else:
            users = json.load(open(fp))
        log.info('Known users: %s' % users)

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
            self.redirect(u"/?s=%s" % resource)
        else:
            error_msg = u"?error=" + \
                        tornado.escape.url_escape("Wrong login/password.")
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
        pipeline = self.get_argument('s', None)
        log.info('Snapshot type: %s' % pipeline)

        fn = op.join(self.wd,
                     pipeline,
                     'ratings',
                     'scores_%s_%s.xls' % (pipeline, username))
        if not op.isfile(fn):
            self.write('<script>alert("Please review at least one subject '
                       'before downloading Excel table.")"</script>')
            return

        buf_size = 4096
        self.set_header('Content-Type', 'application/octet-stream')
        self.set_header('Content-Disposition', 'attachment; filename='\
                        + op.basename(fn))
        with open(fn, 'rb') as f:
            while True:
                data = f.read(buf_size)
                if not data:
                    break
                self.write(data)
        self.finish()

    def initialize(self, wd):
        self.wd = wd


class PostHandler(BaseHandler, ScoreManager):

    @tornado.web.authenticated
    def post(self):

        pipeline = self.get_argument('pipeline', None)
        log.info('Snapshot type: %s' % pipeline)
        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.snapshots[pipeline].keys())

        log.info(self.scores[pipeline])
        log.info('User %s has given following scores: %s'
                 % (username, self.scores[pipeline][username]))
        # Parse passed data
        score = self.get_argument("score", None)
        if score != '':
            score = int(score)

        comments = self.get_argument("comments", None)
        subject = int(self.get_argument("subject", None))
        then = self.get_argument("then", None)

        log.info('%s (%s) was given %s (out of %s) (comments: %s)'
                 % (subject, self.subjects[pipeline][subject - 1], score,
                    n_subjects, comments))

        fn = op.join(self.wd,
                     pipeline,
                     'ratings',
                     'scores_%s_%s.xls' % (pipeline, username))

        self.update(score, comments, subject,
                    self.subjects[pipeline],
                    self.scores[pipeline][username],
                    fn)

        if then == 'next':
            subject = subject + 1 if subject < n_subjects else 1
        elif then == 'prev':
            subject = subject - 1 if subject > 1 else n_subjects
        elif then == 'nextbad':
            subject = find_next_bad(subject,
                                    self.tests[pipeline],
                                    self.subjects[pipeline])

        log.info('User %s has given following scores: %s'
                 % (username, self.scores[pipeline][username]))

        score, comments, res = self.next(subject=subject,
                                         subjects=self.subjects[pipeline],
                                         tests=self.tests[pipeline],
                                         scores=self.scores[pipeline][username])

        log.info('Next subject: %s (%s) (%s)'
                 % (subject, score, comments))
        self.write(json.dumps(res))

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


from snaprate.utils import HTMLFactory
class MainHandler(BaseHandler, HTMLFactory):

    @tornado.web.authenticated
    def get(self):

        pipelines = list(self.snapshots.keys())
        p = self.get_argument('s', None)  # get pipeline name
        id = int(self.get_argument('id', 1))  # get subject index
        username = str(self.current_user[1:-1], 'utf-8')

        # Make sure passed pipeline is an existing folder
        folders = [op.basename(e) for e in glob(op.join(self.wd, '*'))
                   if op.isdir(e)]
        if p is None or p not in folders:
            self.clear()
            self.redirect('/auth/logout/')
            return

        log.info('Snapshot type: %s' % p)

        subject = self.subjects[p][id-1]  # first subject to be displayed
        n_subjects = len(self.snapshots[p])
        rate_code = self.rate_code(subject, n_subjects, username, p)
        images_code = self.images_code(self.subjects[p], self.snapshots[p])

        args = {'danger': '',
                'datasource': '',
                'database': '/tmp',
                'rate_subjects': rate_code,
                'n_subjects': n_subjects,
                'visible_subject': id,
                'images': images_code}

        log.info('User %s has given following scores: %s'
                 % (username, self.scores[p][username]))
        self.render("html/index.html", username=username, **args)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


class StatsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        from .stats import get_stats

        pipelines = list(self.snapshots.keys())
        pipeline = self.get_argument('s', None)

        fp = op.join(self.wd, 'users.json')

        if pipeline is None:
            html = ''
            for each in pipelines:
                row = '<div><a href="%s">%s</a>: %s</div><br>'
                res = get_stats(self.wd, each)
                row = row % ('/stats/?s=%s' % each, each, '%.2f' % float(res[1]))
                html = html + row

            self.render('html/stats.html', table=html, total_counter='',
                        comments='')
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
        self.write('"%s"' % eid)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)
