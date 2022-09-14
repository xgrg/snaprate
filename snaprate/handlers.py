import tornado
from tornado.options import define
import json
import os.path as op
from glob import glob
import logging as log
from snaprate import utils



class My404Handler(tornado.web.RequestHandler):
    # Override prepare() instead of get() to cover all possible HTTP methods.
    def prepare(self):
        self.set_status(404)
        self.redirect('/')


def _initialize(self, wd, scores, h5):
    self.wd = wd
    #self.subjects = subjects
    self.scores = scores
    self.h5 = h5
    #self.tests = tests


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

        self.render("html/login.html", errormessage=errormessage)

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

        auth = self.check_permission(password, username)
        if auth:
            self.set_current_user(username)
            self.redirect(u"/")
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

        fn = op.join(self.wd,

                     'ratings',
                     'scores_%s.xls' %username)
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


class PostHandler(BaseHandler, utils.ScoreManager, utils.H5Manager):


    @tornado.web.authenticated
    def post(self):
        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.h5)

        # Parse passed data
        polygons = json.loads(self.get_argument("polygons", None))

        score = self.get_argument("score", None)
        if score != '':
            score = int(score)

        comments = self.get_argument("comments", None)
        id = int(self.get_argument("subject", None))
        then = self.get_argument("then", None)

        print('*** %s is pushing score=%s (%s) with %s polygons'\
            % (username, score, comments, len(polygons)))
        print('h5:', self.h5[id])
        print(self.scores)


        self.scores[self.h5[id]] = [id, score, comments, polygons, username]

        from snaprate import settings
        import pandas as pd
        fn = op.join(settings.STATIC_PATH, 'annotations.xlsx')
        log.info('Writing %s...' % fn)
        data = []
        for k, v in self.scores.items():
            row = [k]
            row.extend(v[:-2])
            row.append(json.dumps(v[-2]))
            row.append(v[-1])
            data.append(row)
        columns = ['fp', 'id', 'score', 'comments', 'polygons', 'username']
        df = pd.DataFrame(data, columns=columns).set_index('fp').sort_index()
        df.to_excel(fn)

        # self.update(score, comments, subject,
        #             self.subjects[pipeline],
        #             self.scores[pipeline][username],
        #             fn)

        if then == 'next':
            id = id + 1 if id < n_subjects - 1 else 0
        elif then == 'prev':
            id = id - 1 if id > 0 else n_subjects - 1

        log.info('Next subject: %s (%s)'
                 % (self.h5[id], id))
        jf = self.process_h5(self.h5[id])
        scores = self.scores.get(self.h5[id], [None, '', '', [], None])

        print('NEW ID', id, scores)
        id, score, comment, polygons, username = scores
        self.write(json.dumps([id, jf, polygons, comment, score]))

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


class MainHandler(BaseHandler, utils.HTMLFactory, utils.H5Manager):

    @tornado.web.authenticated
    def get(self):
        id = int(self.get_argument('id', 0))  # get subject index
        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.h5)

        rate_code = self.rate_code(id, n_subjects, username)
        jf = self.process_h5(self.h5[id])
        scores = self.scores.get(self.h5[id], None)
        polygons = []
        if scores is not None:
            polygons = scores[-2]

        args = {'danger': '',
                'datasource': '',
                'database': '/tmp',
                'rate_subjects': rate_code,
                'n_subjects': len(self.h5),
                'index': id,
                'polygons': json.dumps(polygons),
                'images': '',
                'jf': jf}

        log.info('User %s has given following scores: %s'
                 % (username, scores))
        self.render("html/index.html", username=username, **args)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


class PipelineHandler(BaseHandler):

    @tornado.web.authenticated
    def post(self):

        pipelines = list(self.snapshots.keys())
        pipeline = self.get_argument('pipeline', None)  # get pipeline name
        id = int(self.get_argument('id', 1))  # get subject index
        username = str(self.current_user[1:-1], 'utf-8')
        current_subject = self.subjects[pipeline][id - 1]
        other_pipelines = utils.other_pipelines(current_subject,
                                                pipeline,
                                                self.subjects)
        self.write(other_pipelines)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


class StatsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        from .stats import get_stats

        pipelines = list(self.snapshots.keys())
        pipeline = self.get_argument('s', None)

        # fp = op.join(self.wd, 'users.json')

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

        url = 'https://xnat.barcelonabeta.org/data/'\
            'experiments/%s?format=html' % eid
        self.write('"%s"' % eid)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)
