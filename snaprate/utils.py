import pandas as pd
import logging as log
from datetime import datetime
import os.path as op
from snaprate import settings




class HTMLFactory():


    def rate_code(self, subject, n_subjects, username):

        color_btn = {'-1': 'danger',
                     '': 'secondary',
                     '1': 'warning',
                     '0': 'success'}

        fp = op.join(op.dirname(__file__), '..', 'web', 'html', 'viewer.html')
        html = open(fp).read()

        scores = self.scores.get(self.h5[subject], [None, '', '', [], None]) # self.read_scores(pipeline, subject, username)
        id, score, comment, polygons, username = scores
        test_section = '' # self.add_tests(self.tests[pipeline], subject)

        # pipelines = other_pipelines(subject, pipeline, self.subjects)
        # print(pipelines)
        print(score, color_btn)
        kwargs = {'id': id,
                  'username': username,
                  'n_subjects': n_subjects,
                  'test_section': test_section,
                  'color_btn': color_btn[score],
                  'comment': comment }

        print(kwargs)
        html = html.format(**kwargs)
        return html

class H5Manager():
    def process_h5(self, fp):
        import tempfile
        import os
        from snaprate import settings
        os.system('rm %s' % op.join(settings.STATIC_PATH, 'tmp*.jpg'))

        fh, jf = tempfile.mkstemp(suffix='.jpg')
        os.close(fh)
        jf = op.join(settings.STATIC_PATH, op.basename(jf))
        print(jf)

        # fp = op.join(self.wd, 'sydney.jpg')
        # os.system('cp %s %s' % (fp, jf))
        # jf = self.static_url('tests/sydney.jpg')
        # print('jf', fp)

        print('fp', fp)
        from nisnap import snap
        snap.plot_segment(fp, bg=fp, axes='x', opacity=0, savefig=jf)
        jf = self.static_url(op.basename(jf))

        print('jf', jf)
        return jf


class ScoreManager():
    def update(self, score, comments, subject, subjects, scores, fn):
        current_subject = subjects[subject - 1]
        res = scores.get(current_subject, ['', '', '', ''])
        old_score, old_comments, _, old_dt = res

        has_changed = current_subject not in scores.keys() \
            or (old_score != score or old_comments != comments)

        if has_changed:
            dt = datetime.strftime(datetime.now(), '%Y%m%d-%H%M%S')
        else:
            dt = old_dt

        scores[current_subject] = [score, comments, subject, dt]

        if not op.isdir(op.dirname(fn)):
            import os
            log.info('Creating folder %s' % op.dirname(fn))
            os.mkdir(op.dirname(fn))

        log.info('Writing %s...' % fn)
        data = []
        for s, v in scores.items():
            row = [s]
            row.extend(v)
            data.append(row)
        columns = ['ID', 'score', 'comments', 'index', 'datetime']
        df = pd.DataFrame(data, columns=columns).set_index('ID').sort_index()
        df.to_excel(fn)

    def next(self, subject, subjects, tests, scores):

        current_subject = subjects[subject - 1]

        res = scores.get(current_subject, ['', '', '', ''])
        score, comments, index, dt = res
        res = [score, comments, subject]

        if tests is not None:

            test_names = tests.columns
            tn = test_names[0]

            test = str(tests.loc[subjects[subject-1]][tn])
            c = [str(tests.loc[subjects[subject-1]][each])
                 for each in test_names]

            res.append(test)
            res.append([(i, j) for i, j in zip(test_names, c)])
            print(res)
        return res
