import pandas as pd
import logging as log
from datetime import datetime
import os.path as op


def find_next_bad(subject, tests, subjects):
    test_names = tests.columns
    tn = test_names[0]

    failed = sorted([int(subjects.index(e))+1 for e in tests.query('not %s' % tn).index])
    if subject in failed:
        failed.remove(subject)
    failed.append(subject)
    failed = sorted(failed)
    i = failed.index(subject)
    ns = failed[i + 1] if i + 1 < len(failed) else failed[0]
    return ns


def other_pipelines(subject, pipeline, subjects):
    # current_subject = subjects[pipeline][subject - 1]
    pipelines = {}
    for p, subj in subjects.items():
        if p == pipeline:
            continue
        if subject in subj:
            pipelines[p] = subj.index(subject) + 1

    types = ''
    for p, subject_id in pipelines.items():
        types += '<button type="button" class="dropdown-item" pipeline="%s" subject="%s">%s</button>' % (p, subject_id, p)

    if len(pipelines.items()) != 0:
        html = """<span id="otherp" class="dropdown"><button class="btn btn-info dropdown-toggle" type="button"
                    data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
                    Pipelines
                    </button>
                <div class="dropdown-menu" aria-labelledby="dropdownMenuButton">
                {types}
                </div>
                </span>"""
        return html.format(types=types)
    return '<span id="otherp"></span>'


class HTMLFactory():

    def read_scores(self, pipeline, subject, username):
        fp = 'scores_%s_%s.xls' % (pipeline, username)
        fn = op.join(self.wd, pipeline, 'ratings', fp)
        log.info('Reading %s...' % fn)

        self.scores.setdefault(pipeline, {})

        # Look up previous score or define blank one.
        if op.isfile(fn):
            x = pd.read_excel(fn, converters={'ID': str, 'score': str})
            x = x.set_index('ID')
            data = {}
            for i, row in x.iterrows():
                r = []
                for e in row.to_list():
                    aux = '' if pd.isna(e) else e
                    r.append(aux)
                data[i] = r
            self.scores[pipeline][username] = data
            score, comment, index, dt = data.get(subject, ['', '', '', ''])
        else:
            self.scores[pipeline][username] = {}
            score, comment = ('', '')

        if score != '':
            score = int(score)
        return score, comment

    def add_tests(self, tests, subject):
        tsp = """<a class="btn btn-secondary" id="nextbad" href="nextbad/">
                    Go to next predicted failed case
                 </a>
                 <span class="btn btn-{color_test}" id="test">
                 Automatic prediction
                 </span><br>"""

        test_unit = """<span href="#" data-toggle="tooltip" class="badge
                    badge-light" id="test{id}">
                    {mesg}
                    </span>
                    &nbsp;"""

        if tests is not None:
            test_names = tests.columns
            tn = test_names[0]

            test = tests.loc[subject][tn]
            c = [tests.loc[subject][each] for each in test_names]

            test_section = ''
            # For each test name:value, add it to the GUI
            for i, (test_key, test_value) in enumerate(zip(test_names, c)):

                # Change test button background color
                if test_value == True:
                    tu = test_unit.replace('badge-light', 'badge-success')
                    test_section += tu.format(id=i, mesg=test_key)
                elif test_value == False:
                    tu = test_unit.replace('badge-light', 'badge-danger')
                    test_section += tu.format(id=i, mesg=test_key)
                else:
                    # Trim message if too long
                    if len(test_value) > 20:
                        tu = test_unit.format(id=i,
                                              mesg=str(test_value)[:20] + '…')
                    else:
                        tu = test_unit.format(id=i, mesg=test_value)

                    title = 'title="%s: %s" id' % (test_key, test_value)
                    tu = tu.replace(' id', title)
                    test_section += tu

            color_test = {True: 'success', False: 'danger'}[test]
            test_section_preamble = tsp.format(color_test=color_test)
            test_section = test_section_preamble + test_section
        else:
            test_section = ''
        return test_section

    def rate_code(self, subject, n_subjects, username, pipeline):

        color_btn = {-1: 'danger',
                     '': 'secondary',
                     1: 'warning',
                     0: 'success'}

        fp = op.join(op.dirname(__file__), '..', 'web', 'html', 'viewer.html')
        html = open(fp).read()

        score, comment = self.read_scores(pipeline, subject, username)
        test_section = self.add_tests(self.tests[pipeline], subject)

        pipelines = other_pipelines(subject, pipeline, self.subjects)
        print(pipelines)

        html = html.format(id=id,
                           n_subjects=n_subjects,
                           test_section=test_section,
                           pipeline=pipeline,
                           username=username,
                           color_btn=color_btn[score],
                           comment=comment,
                           pipelines=pipelines)
        return html

    def images_code(self, subjects, snapshots):
        import random
        import string
        # Building html code
        images_code = 'images = ['

        for s in subjects:
            x = random.choices(string.ascii_letters + string.digits, k=16)
            url = '/static/%s?v=%s' % (snapshots[s], ''.join(x))
            img_code = '{small: "%s", big: "%s"},' % (url, url)
            images_code = images_code + img_code

        images_code = images_code + '];'
        images_code = images_code + '''wrapper = $("div #image-gallery");
                viewer = new ImageViewer($(".image-container")[0]);
                window.viewer = viewer;'''
        return images_code


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
