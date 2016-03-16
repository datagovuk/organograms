'''
Produces an index of all the organograms published on the TSO triplestore. Each
should have an XLS file - either from the upload site or we generate from the
triplestore data.
'''
import argparse
import csv
import os.path
import traceback
import time
import sys

from compare_departments import date_to_year_first
from csv2xls import csv2xls
from uploads_scrape import munge_org
from compare_posts import MOD_AGGREGATED_SUBPUBS
from etl_to_csv import load_senior, load_junior, verify_graph, ValidationFatalError

args = None


def combine():
    in_filename = 'uploads_report_tidied.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)

        # ignore some rows that are duplicates
        ignore_xls = (
            '/data/geo/2011-09-30/Copy-of-Final_20110930_08.11.xls',
            '/data/apa/2012-03-31/APA-government-staff-and-salary-data-blank-template---Sept-2012-FINAL.xls',
            '/data/hotmail/2012-03-31/DfT(C)-Transparency-Final-Return-31.03.12.xls',
            '/data/plr/2012-09-30/300912-PublicLendingRight-OrganogramV1.xls',
            )

        uploads = dict(
            ((date_to_year_first(row['version']), row['org_name']), row)
            for row in csv_reader
            if row['xls_path'] not in ignore_xls
            and row['state'] == 'published'
            and row['org_name'] not in MOD_AGGREGATED_SUBPUBS)
        # mod get added from triplestore

    in_filename = 'compare_post_counts.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        post_counts = [row for row in csv_reader]

    out_rows = []
    for post_count in post_counts:
        print post_count['body_title'], post_count['graph']
        senior_posts_triplestore = int(post_count['senior_posts_triplestore'] or 0)
        senior_posts_uploads = int(post_count['senior_posts_uploads'] or 0)

        if post_count['body_title'] == 'Ministry of Defence' or \
                 senior_posts_triplestore > senior_posts_uploads:
            # generate an XLS from the triplestore data
            print 'Triplestore'
            xls_filepath = get_xls_filepath(
                org_name=post_count['body_title'],
                graph=post_count['graph'])
            csv_filepath = get_csv_filepath(
                org_name=post_count['body_title'],
                graph=post_count['graph'],
                junior_or_senior='junior')
            csv2xls_filepath = os.path.join(sys.path[0],
                                            'csv2xls.py')
            if not os.path.exists(xls_filepath) or \
                    (time.ctime(os.path.getmtime(xls_filepath)) <
                     time.ctime(os.path.getmtime(csv_filepath))) or \
                    (time.ctime(os.path.getmtime(xls_filepath)) <
                     time.ctime(os.path.getmtime(csv2xls_filepath))):
                print 'Converting CSV to XLS', csv_filepath
                if not os.path.exists(csv_filepath):
                    print 'CSV not found'
                    import pdb; pdb.set_trace()
                xls_filepath_ = csv2xls([csv_filepath])
                assert xls_filepath
                assert xls_filepath == xls_filepath_
            print xls_filepath
            if args.check:
                valid = check(xls_filepath)
                if not valid:
                    import pdb; pdb.set_trace()
            upload = None
        elif senior_posts_triplestore == senior_posts_uploads == 0:
            continue
        else:
            # XLS comes from the uploads
            try:
                upload = uploads[(post_count['graph'], post_count['body_title'])]
            except KeyError:
                traceback.print_exc()
                import pdb; pdb.set_trace()
            if not upload['state'] == 'published':
                print 'Not published'
                import pdb; pdb.set_trace()
            xls_filepath = upload['xls_path']

        row = dict(
            body_title=post_count['body_title'],
            graph=post_count['graph'],
            xls_path=xls_filepath,
            upload_date=upload['upload_date'] if upload else None,
            publish_date=upload['action_datetime'] if upload else None,
        )
        out_rows.append(row)

    # save
    headers = ['body_title', 'graph', 'xls_path', 'upload_date', 'publish_date']
    out_filename = 'tso_combined.csv'
    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        csv_writer.writeheader()
        for row in out_rows:
            csv_writer.writerow(row)
    print 'Written', out_filename


def check(xls_filename):
    errors = []
    senior = load_senior(xls_filename, errors)
    junior = load_junior(xls_filename, errors)
    try:
        verify_graph(senior, junior, errors)
    except ValidationFatalError, e:
        print "VALIDATION ERROR (fatal):", e
        return False
    for error in list(set(errors)):
        print "VALIDATION ERROR:", error
    return bool(not errors)


def date_to_day_first(date_year_first):
    return '/'.join(date_year_first.split('-')[::-1])


def get_xls_filepath(org_name, graph):
    '''How csv2xls writes them'''
    path = 'data/dgu/xls-from-triplestore'
    filename = '{org}-{date}-organogram.{format_}'.format(
        org=munge_org(org_name),
        date=graph,
        format_='xls')
    return os.path.join(path, filename)


def get_csv_filepath(org_name, graph, junior_or_senior):
    '''How compare_posts.py writes them'''
    path = 'data/dgu/csv-from-triplestore'
    filename = '{org}-{date}-{junior_or_senior}.{format_}'.format(
        org=munge_org(org_name),
        date=graph,
        junior_or_senior=junior_or_senior,
        format_='csv')
    return os.path.join(path, filename)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='Check the XLS validates')
    args = parser.parse_args()
    combine()
