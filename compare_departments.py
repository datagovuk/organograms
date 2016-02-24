"""Tool for comparing between the uploads and legacy triplestore

Compare departments in the triplestores:

Requires: triplestore_departments_tidied.csv
          uploads_report_tidied.csv

$ python compare_departments.py -g all departments

"""
import argparse
from pprint import pprint
import csv
from collections import defaultdict

args = None


class InvalidGraph(Exception):
    pass


def departments_cmd():
    if args.graph and args.graph != 'all':
        versions = [args.graph]
    else:
        versions = VERSIONS
        args.query_quiet = True

    filename = 'compare_departments.csv'
    with open(filename, 'wb') as csv_file:
        csv_writer = csv.writer(csv_file)
        csv_writer.writerow(['version', 'upload', 'triplestore', 'matching', 'only_in_upload', 'only_in_triplestore', 'matching_depts', 'only_in_upload_depts', 'only_in_triplestore_depts'])
        for version in versions:
            uploads = UploadsData.instance().by_graph.get(version, [])
            depts_uploads = [u['title'] for u in uploads]

            depts_ts_ = TriplestoreData.instance().by_graph.get(version, [])
            depts_ts = [d['title'] for d in depts_ts_]

            print 'Compare %s:' % version
            matching, only_upload, only_ts = \
                print_difference(depts_uploads, depts_ts, 'upload', 'triplestore')
            csv_writer.writerow([
                version,
                len(depts_uploads),
                len(depts_ts),
                len(matching),
                len(only_upload),
                len(only_ts),
                ' | '.join(matching),
                ' | '.join(only_upload),
                ' | '.join(only_ts),
                ])
    print 'Written: ', filename


class UploadsData(object):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.by_graph = defaultdict(list)
        self.by_title = defaultdict(list)
        with open('uploads_report_tidied.csv', 'rb') as f:
            csv_reader = csv.DictReader(f)
            for upload in csv_reader:
                if upload['state'] != 'published':
                    continue
                upload['graph'] = date_to_year_first(upload['version'])
                upload['title'] = upload['org_name']
                self.by_graph[upload['graph']].append(upload)
                self.by_title[upload['org_name']].append(upload)


class TriplestoreData(object):
    _instance = None

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.by_graph = defaultdict(list)
        self.by_title = defaultdict(list)
        with open('triplestore_departments_tidied.csv', 'rb') as f:
            csv_reader = csv.DictReader(f)
            for dept in csv_reader:
                dept['graphs'] = dept['graphs'].split()
                self.by_title[dept['title']] = dept
                for graph in dept['graphs']:
                    self.by_graph[graph].append(dept)


def print_difference(a, b, name_a, name_b):
    '''Prints diff of two lists'''
    # convert to lists in case they are generators
    a = list(a)
    b = list(b)
    print '%s: %s  %s: %s' % (name_a, len(list(a)), name_b, len(list(b)))
    if not (a or b):
        return

    def print_some(keys, all_values):
        for key in sorted(keys)[:5]:
            print '   ' + key
        if len(keys) > 5:
            print '   ...'
        print '    (%s)' % len(keys)
    matching = set(a) & set(b)
    print 'Matching: %s' % len(matching)
    only_in_b = set(b) - set(a)
    if only_in_b:
        print 'Only in %s:' % name_b
        print_some(only_in_b, b)
    only_in_a = set(a) - set(b)
    if only_in_a:
        print 'Only in %s:' % name_a
        print_some(only_in_a, a)
    if not (only_in_b or only_in_a):
        print 'No differences'
    return matching, only_in_a, only_in_b


def date_to_year_first(date_day_first):
    return '-'.join(date_day_first.split('/')[::-1])

VERSIONS = [
    '2011-03-31',
    '2011-09-30',
    '2012-03-31',
    '2012-09-30',
    '2013-03-31',
    '2013-09-30',
    '2014-03-31',
    '2014-09-30',
    '2015-03-31',
    '2015-09-30',
    ]

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-g', '--graph',
        choices=VERSIONS + ['all'],
        dest='graph',
        help='select graph e.g. "all" or 2011-03-30')
    parser.add_argument(
        '-f', '--display-full',
        dest='display_full',
        action='store_true',
        help='Display full information about each result')
    parser.add_argument(
        '-q', '--query-quiet',
        dest='query_quiet',
        action='store_true',
        help='Don\'t display the queries made')
    subparsers = parser.add_subparsers()

    # create simple subparsers for commands which don't already have one
    commands = [(name.replace('_cmd', ''), func)
                for name, func in locals().items()
                if (callable(func) and name.endswith('_cmd')
                    and name not in subparsers.choices.keys())]
    for name, func in commands:
        if name not in subparsers.choices.keys():
            parser_properties = subparsers.add_parser(name)
            parser_properties.set_defaults(func=func)
    args = parser.parse_args()

    # call the function
    args.func()
