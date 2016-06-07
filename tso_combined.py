'''
Produces an index of all the organograms published on the TSO triplestore. Each
should have an XLS file - either from the upload site or we generate from the
triplestore data.
'''
import argparse
import csv
import traceback
import sys

import unicodecsv

from compare_departments import date_to_year_first
from compare_posts import MOD_AGGREGATED_SUBPUBS
from etl_to_csv import load_xls_and_get_errors
from csv2xls import int_if_possible

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

    xls_index_filename = 'csv2xls-from-triplestore.csv'
    def get_index_key(row):
        return (row['body_title'], row['graph'])
    with open(xls_index_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        xls_index = dict((get_index_key(row), row)
                         for row in csv_reader)

    out_rows = []
    for post_count in post_counts:
        if args.graph and post_count['graph'] != args.graph:
            continue
        if args.body and post_count['body_title'] != args.body:
            continue
        print '\n' + post_count['body_title'], post_count['graph']

        senior_posts_triplestore = int(post_count['senior_posts_triplestore'] or 0)
        senior_posts_uploads = int(post_count['senior_posts_uploads'] or 0)

        out_row = {}
        if senior_posts_triplestore == senior_posts_uploads == 0:
            continue
        elif senior_posts_triplestore and \
                not can_we_use_the_upload_spreadsheet(
                post_count['body_title'], post_count['graph']):
            print 'Triplestore'
            out_row['source'] = 'triplestore'
            xls_info = xls_index[get_index_key(post_count)]
            xls_filepath = xls_info['xls_filepath']
            print xls_filepath
            upload = None
            out_row['senior_posts_xls'] = xls_info['senior_posts_count']
            out_row['junior_posts_xls'] = xls_info['junior_posts_count']
        else:
            # XLS comes from the uploads
            print 'Upload'
            out_row['source'] = 'upload'
            try:
                upload = uploads[(post_count['graph'], post_count['body_title'])]
            except KeyError:
                traceback.print_exc()
                import pdb; pdb.set_trace()
            if not upload['state'] == 'published':
                print 'Not published'
                import pdb; pdb.set_trace()
            xls_filepath = 'data/dgu/xls/' + upload['xls-filename']
            print xls_filepath
            original_xls_filepath = upload['xls_path']
            out_row['senior_posts_xls']=post_count['senior_posts_uploads']
            out_row['junior_posts_xls']=post_count['junior_posts_uploads']

        if args.check:
            errors, will_display = check(xls_filepath)

        out_row.update(dict(
            body_title=post_count['body_title'],
            graph=post_count['graph'],
            xls_path=xls_filepath,
            original_xls_filepath=original_xls_filepath if upload else None,
            upload_date=upload['upload_date'] if upload else None,
            publish_date=upload['action_datetime'] if upload else None,
            errors=errors if args.check else 'not checked',
            will_display=will_display if args.check else 'not checked',
            senior_posts_triplestore=post_count['senior_posts_triplestore'],
            junior_posts_triplestore=post_count['junior_posts_triplestore'],
            ))
        for j_or_s in ('senior', 'junior'):
            diff = \
                (int_if_possible(out_row.get('%s_posts_triplestore' % j_or_s)) or 0) - \
                (int_if_possible(out_row.get('%s_posts_xls' % j_or_s)) or 0)
            out_row['%s_diff' % j_or_s] = diff if diff > 0 else None
        out_rows.append(out_row)

    # save
    if args.graph or args.body:
        print 'Not writing output CSV as you specified only part of the data'
        sys.exit(0)
    headers = [
        'body_title', 'graph',
        'xls_path', 'original_xls_filepath',
        'source',
        'upload_date', 'publish_date',
        'errors', 'will_display',
        'senior_posts_triplestore', 'senior_posts_xls', 'senior_diff',
        'junior_posts_triplestore', 'junior_posts_xls', 'junior_diff',
        ]
    out_filename = 'tso_combined.csv'
    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = unicodecsv.DictWriter(csv_write_file,
                                           fieldnames=headers,
                                           encoding='utf-8')
        csv_writer.writeheader()
        for row in out_rows:
            csv_writer.writerow(row)
    print 'Written', out_filename


def check(xls_filename):
    try:
        senior, junior, errors, will_display = \
            load_xls_and_get_errors(xls_filename)
    except Exception:
        print 'XLS VALIDATION EXCEPTION', xls_filename
        traceback.print_exc()
        import pdb; pdb.set_trace()
    print '%s errors' % len(errors)
    if not will_display:
        print 'WILL NOT DISPLAY'
    return '; '.join(errors), will_display


def can_we_use_the_upload_spreadsheet(body_title, graph):
    '''Uses hand-tailored logic.'''
    # Early uploads are a mess
    if graph in ('2011-03-31', '2011-09-30'):
        return False
    # Particular uploads don't seem to represent what's in the triplestore
    if (graph, body_title) in (
        ('2014-03-31', 'National Army Museum'),
        ('2012-09-30', 'Human Tissue Authority'),
        ('2014-03-31', 'United Kingdom Hydrographic Office'),
        ('2015-03-31', 'United Kingdom Hydrographic Office'),
        ('2012-03-31', 'Audit Commission'),
        ('2012-03-31', 'Asset Protection Agency'),
        
            ):
        return False
    # MoD uploads would need combining and none of the years of uploads seem as
    # complete as the triplestore
    if body_title == 'Ministry of Defence' and graph < '2016':
        return False
    return True


def date_to_day_first(date_year_first):
    return '/'.join(date_year_first.split('-')[::-1])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true',
                        help='Check the XLS validates')
    parser.add_argument('--body')
    parser.add_argument('--graph')
    args = parser.parse_args()
    combine()
