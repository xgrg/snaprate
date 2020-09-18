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


def collect_snapshots(wd, subjects):
    folders = [op.basename(e) for e in glob(op.join(wd, '*')) if op.isdir(e)]
    snapshots = {}
    log.info('=== Summary of snapshots ===')
    for f in folders:
        sd = op.join(wd, f, 'snapshots')
        if not op.isdir(sd):
            msg = 'Snapshot directory not found (%s)' % sd
            raise Exception(msg)
        else:
            snapshots[f] = {}
            for s in subjects[f]:
                jpg = op.join(sd, '%s.jpg' % s)
                png = op.join(sd, '%s.png' % s)
                if not op.isfile(jpg) and not op.isfile(png):
                    raise Exception('Snapshot not found %s/%s' % (jpg, png))
                elif op.isfile(jpg) and op.isfile(png):
                    raise Exception('Snapshot shoud be unique %s/%s'
                                    % (jpg, png))
                elif op.isfile(jpg):
                    fp = jpg
                else:
                    fp = png

                snapshots[f][s] = '.' + op.abspath(fp)[len(op.dirname(wd)):]

        log.info('[%s] %s snapshots found'
                 % (f, len(snapshots[f])))

    return snapshots


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
