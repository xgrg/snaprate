import pandas as pd
import logging as log
from datetime import datetime
import os.path as op

class HTMLFactory():

    def rate_code(self, index, images, username):

        color_btn = {-1: 'danger',
                     '': 'secondary',
                     1: 'warning',
                     0: 'success'}

        fp = op.join(op.dirname(__file__),
                     '..', 'web', 'html', 'viewer.html')
        html = open(fp).read()

        blank = [None, '', '', [], None]
        scores = self.scores.get(images[index], blank)
        _, score, comment, polygons, _ = scores
        if score not in [None, '']:
            score = int(score)
        kwargs = {'index': index,
                  'username': username,
                  'n_cases': len(images),
                  'test_section': '',
                  'color_btn': color_btn[score],
                  'comment': comment }
        print(kwargs)

        html = html.format(**kwargs)
        return html

class SnapshotMaker():
    def snap(self, fp):
        import tempfile
        import os
        from snaprate import settings
        os.system('rm %s' % op.join(settings.STATIC_PATH, 'tmp*.jpg'))

        fh, jf = tempfile.mkstemp(dir=settings.STATIC_PATH, suffix='.jpg')
        os.close(fh)
        print(jf)

        if (fp == 'sydney.jpg'):
            fp = op.join(self.wd, 'sydney.jpg')
            os.system('cp %s %s' % (fp, jf))
            jf = self.static_url('tests/sydney.jpg')
            print('jf', fp)

        print('fp', fp)
        from nisnap import snap
        snap.plot_segment(fp, bg=fp, axes='x', opacity=0, savefig=jf)
        jf = self.static_url(op.basename(jf))

        print('jf', jf)
        return jf


class ScoreManager():

    def save(self, scores):
        from snaprate import settings
        import pandas as pd
        import json

        fn = op.join(settings.STATIC_PATH, 'annotations.xlsx')
        log.info('Writing %s...' % fn)
        data = []
        for k, v in scores.items():
            row = [k]
            row.extend(v[:-2])
            row.append(json.dumps(v[-2]))
            row.append(v[-1])
            data.append(row)
        columns = ['fp', 'index', 'score', 'comments', 'polygons', 'username']
        df = pd.DataFrame(data, columns=columns).set_index('fp').sort_index()
        df.to_excel(fn)
