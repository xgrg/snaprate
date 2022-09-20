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
    self.scores = scores
    self.h5 = h5


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
        from snaprate import settings
        username = str(self.current_user[1:-1], 'utf-8')
        fn = op.join(settings.STATIC_PATH, 'annotations.xlsx')
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


class PostHandler(BaseHandler, utils.ScoreManager, utils.SnapshotMaker):

    @tornado.web.authenticated
    def post(self):

        username = str(self.current_user[1:-1], 'utf-8')
        n_cases = len(self.h5)

        # Parse passed data
        polygons = json.loads(self.get_argument("polygons", None))
        comments = self.get_argument("comments", None)
        index = int(self.get_argument("index", None))
        then = self.get_argument("then", None)
        score = self.get_argument("score", None)
        if score != '':
            score = int(score)

        print('*** %s is pushing score=%s (%s) with %s polygons'\
            % (username, score, comments, len(polygons)))

        fp = self.h5[index]
        print('Previous image (%s): %s' % (index, fp))

        self.scores[fp] = [index, score, comments, polygons, username]
        print(self.scores)

        self.save(self.scores)

        # Update index
        new_index = index
        if then == 'next':
            new_index = index + 1 if index < n_cases - 1 else 0
        elif then == 'previous':
            new_index = index - 1 if index > 0 else n_cases - 1

        # Get snapshot
        fp = self.h5[new_index]
        log.info('Next image: %s (%s)' % (fp, new_index))
        jf = self.snap(fp)

        # Get annotation info if available and return it
        blank = [None, '', '', [], None]
        scores = self.scores.get(fp, blank)
        _, score, comment, polygons, username = scores

        res = {'index':new_index, 'snapshot':jf,
            'polygons': polygons, 'comment': comment,
            'score':score}
        self.write(json.dumps(res))

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)


class MainHandler(BaseHandler, utils.HTMLFactory, utils.SnapshotMaker):

    @tornado.web.authenticated
    def get(self):
        index = int(self.get_argument('i', 0))  # get subject index
        username = str(self.current_user[1:-1], 'utf-8')
        n_subjects = len(self.h5)

        rate_code = self.rate_code(index, self.h5, username)

        fp = self.h5[max(index, 0)]
        jf = self.snap(fp)
        scores = self.scores.get(fp, None)

        polygons = scores[-2] if scores is not None else []

        if index == -1:
            jf = self.static_url('tests/sydney.jpg')
            polygons = []

        fp1 = op.join(op.dirname(__file__), '../web/html/modal.html')
        fp2 = op.join(op.dirname(__file__), '../web/data/labels.json')
        labels = json.load(open(fp2))

        html = ''
        tpl = '<option style="background:%s" value="%s">%s</option>'
        for k, (label, color) in labels.items():
            html += tpl % (color, k, label)
        html = '<option selected ' + html[8:]
        colors = {k:c for k, (_, c) in labels.items()}
        modals = open(fp1).read().format(labels=html)

        args = {'rate_code': rate_code,
                'h5': json.dumps(self.h5),
                'index': index,
                'polygons': json.dumps(polygons),
                'jf': jf,
                'modals': modals,
                'colors': json.dumps(colors)}

        log.info('User %s has given following scores: %s'
                 % (username, scores))
        self.render("html/index.html", username=username, **args)

    def initialize(self, **kwargs):
        _initialize(self, **kwargs)
