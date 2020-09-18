from glob import glob
from .collect import collect_subjects
import os.path as op
import pandas as pd


def get_stats(wd, pipeline):

    scores_fn = glob(op.join(wd, pipeline, 'ratings',
                     'scores_%s_*.xls' % pipeline))

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
    review = pd.DataFrame(review, columns=columns, index=names)
    review = review.sort_values(by='reviewed', ascending=False)
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
            col1.append('@@@1%s@@@2' % i)
            col2.append('@@@3%s@@@4' % row['index'])

        comments['XNAT'] = col1
        comments['snaprate'] = col2

        del comments['index']
        pd.set_option('display.max_colwidth', -1)

        comments = comments.to_html()
        d = {'@@@1': '<a href="https://barcelonabrainimaging.org/data/'
                     'experiments/',
             '@@@2': '?format=html">link</a>',
             '@@@3': '<a href="/?s=%s&id=' % pipeline,
             '@@@4': '">link</a>'}
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
