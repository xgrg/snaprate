import os.path as op
import logging as log
from glob import glob
import pandas as pd
import json


def collect_tests(wd):
    folders = [op.basename(e) for e in glob(op.join(wd, '*')) if op.isdir(e)]
    tests = {}
    log.info('=== Summary of tests ===')
    for f in folders:
        fp = op.join(wd, f, '%s.xls' % f)
        if not op.isfile(fp):
            msg = 'File not found (%s)' % fp
            log.warning(msg)
            tests[f] = None
        else:
            tests[f] = pd.read_excel(fp, converters={'ID': str}).set_index('ID')

            log.info('[%s] %s subjects found - %s tests'
                     % (f, len(tests[f]), len(tests[f].columns)))
    return tests


def collect_h5(wd): #, subjects):
    from glob import glob
    import os.path as op
    h5 = glob(op.join(wd, '*.h5'))

    log.info('%s h5 found' % len(h5))

    return h5


def collect_subjects(wd):
    folders = [op.basename(e) for e in glob(op.join(wd, '*')) if op.isdir(e)]
    subjects = {}
    log.info('=== Summary of subjects ===')
    for f in folders:
        fp = op.join(wd, f, 'subjects.json')
        if not op.isfile(fp):
            msg = 'File not found (%s). Using default list based on snapshots' % fp
            log.warning(msg)
            l1 = [op.basename(e).split('.')[0]
                  for e in glob(op.join(wd, f, 'snapshots', '*.???'))]
            subjects[f] = sorted(l1)
        else:
            subjects[f] = json.load(open(fp))

        log.info('[%s] %s subjects found' % (f, len(subjects[f])))
    return subjects
