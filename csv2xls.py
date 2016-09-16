#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Takes an organogram junior csv and senior csv and converts to an organogram
xls.
'''
import unicodecsv
import xlwt
import argparse
import csv
import os
import traceback

args = None


XLS_COL_HEADERS = {
    'senior': (
        'Post Unique Reference', 'Name', 'Grade (or equivalent)', 'Job Title',
        'Job/Team Function', 'Parent Department', 'Organisation', 'Unit',
        'Contact Phone', 'Contact E-mail', 'Reports to Senior Post',
        u'Salary Cost of Reports (£)', 'FTE', u'Actual Pay Floor (£)',
        u'Actual Pay Ceiling (£)', u'Total Pay (£)',
        'Professional/Occupational Group', 'Notes', 'Valid?',
    ),
    'junior': (
        'Parent Department', 'Organisation', 'Unit', 'Reporting Senior Post',
        'Grade', u'Payscale Minimum (£)', u'Payscale Maximum (£)', 'Generic Job Title',
        'Number of Posts in FTE', 'Professional/Occupational Group', 'Valid?',
    )}
COLS_THAT_SHOULD_BE_NUMBERS = {
    'senior': (u'Salary Cost of Reports (£)', 'FTE',
               u'Actual Pay Floor (£)', u'Actual Pay Ceiling (£)'),
    'junior': (u'Payscale Minimum (£)', u'Payscale Maximum (£)',
               'Number of Posts in FTE')
    }
XLS_COLS_THAT_SHOULD_BE_NUMBERS = {
    'senior': [XLS_COL_HEADERS['senior'].index(col_name)
               for col_name in COLS_THAT_SHOULD_BE_NUMBERS['senior']],
    'junior': [XLS_COL_HEADERS['junior'].index(col_name)
               for col_name in COLS_THAT_SHOULD_BE_NUMBERS['junior']]
}


def csv2xls_multiple(senior_or_junior_csv_filepaths):
    '''Converts the CSV pairs to XLS. Records the operation by updating an
    index CSV.
    '''
    conversions = []
    for senior_or_junior_filepath in senior_or_junior_csv_filepaths:
        conversions += csv2xls(senior_or_junior_filepath)
    return conversions


def csv2xls(senior_or_junior_csv_filepath):
    '''Converts the CSV pairs to XLS. Records the operation by updating an
    index CSV.
    '''
    assert 'senior' in senior_or_junior_csv_filepath or \
        'junior' in senior_or_junior_csv_filepath, \
        'filepath needs junior/senior in it'
    csv_filepaths = dict(
        senior=senior_or_junior_csv_filepath.replace('junior', 'senior'),
        junior=senior_or_junior_csv_filepath.replace('senior', 'junior'))
    xls_filepath = filepath_for_xls_from_triplestore_from_csv_filepath(
        senior_or_junior_csv_filepath)

    workbook = xlwt.Workbook()
    row_counts = {}
    units = set()
    for level, csv_filepath in csv_filepaths.items():
        # Read CSV
        with open(csv_filepath, 'rb') as csv_read_file:
            csv_reader = unicodecsv.reader(csv_read_file)
            csv_headers = csv_reader.next()
            # Append None to each row, as a placeholder for 'Total Pay'/'Valid'
            csv_rows = [row + [None, None] for row in csv_reader]

        # Adjust CSV
        if level == 'senior':
            if 'Grade' in csv_headers:
                csv_headers[csv_headers.index('Grade')] = \
                    'Grade (or equivalent)'
        csv_headers.append(u'Total Pay (£)')
        if level == 'junior':
            csv_headers.append('Valid?')
        # column mapping - for each of the XLS columns it gives the CSV column
        cols_map = [csv_headers.index(xls_col)
                    for xls_col in XLS_COL_HEADERS[level]]
        out_rows = [XLS_COL_HEADERS[level]]
        row_count = 0
        for row in sorted(csv_rows, key=lambda r: number_if_possible(r[0])):
            out_row = [row[csv_col_index] for csv_col_index in cols_map]
            for col_index in XLS_COLS_THAT_SHOULD_BE_NUMBERS[level]:
                out_row[col_index] = number_if_possible(out_row[col_index])
            out_rows.append(out_row)
            row_count += 1

        sheet = workbook.add_sheet('(final data) %s-staff' % level)
        for r, row in enumerate(out_rows):
            for c, value in enumerate(row):
                sheet.write(r, c, value)
        row_counts[level] = row_count

        for row in csv_rows:
            units.add(row[csv_headers.index('Unit')])

    sheet = workbook.add_sheet('(reference) units')
    sheet.write(0, 0, 'Units')
    for r, unit in enumerate(units):
        sheet.write(r + 1, 0, unit)

    workbook.save(xls_filepath)
    print 'Written %s' % xls_filepath
    conversion = dict(
        senior_csv_filepath=csv_filepaths['junior'],
        junior_csv_filepath=csv_filepaths['junior'],
        xls_filepath=xls_filepath,
        senior_posts_count=row_counts['senior'],
        junior_posts_count=row_counts['junior'],
        )
    return conversion


def convert_csvs_where_uploads_unreliable():
    from compare_posts import filepath_for_csv_from_triplestore
    from tso_combined import can_we_use_the_upload_spreadsheet

    # read the index
    def get_index_key(row):
        return (row['body_title'], row['graph'])
    xls_index_filename = 'csv2xls-from-triplestore.csv'
    if os.path.exists(xls_index_filename):
        with open(xls_index_filename, 'rb') as csv_read_file:
            csv_reader = csv.DictReader(csv_read_file)
            xls_index = dict((get_index_key(row), row)
                             for row in csv_reader)
    else:
        print 'Index does not exist - creating %s' % xls_index_filename
        xls_index = dict()

    # convert the csvs to xls
    in_filename = 'triplestore_departments_tidied.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        for row in csv_reader:
            for graph in row['graphs'].split():
                # check if upload is reliable or not
                if can_we_use_the_upload_spreadsheet(
                        row['title'], graph):
                    continue
                csv_filepath = filepath_for_csv_from_triplestore(
                    row['title'], graph, 'senior')
                conversion = csv2xls(csv_filepath)
                # update the index
                conversion['body_title'] = row['title']
                conversion['graph'] = graph
                xls_index[get_index_key(conversion)] = conversion

    # save the index
    headers = [
        'body_title', 'graph',
        'senior_csv_filepath', 'junior_csv_filepath',
        'xls_filepath',
        'senior_posts_count', 'junior_posts_count',
        ]
    try:
        with open(xls_index_filename, 'wb') as csv_write_file:
            csv_writer = unicodecsv.DictWriter(csv_write_file,
                                               fieldnames=headers,
                                               encoding='utf-8')
            csv_writer.writeheader()
            for key, row in sorted(xls_index.items(),
                                   key=lambda x: x[0][1] + x[0][0]):
                csv_writer.writerow(row)
    except Exception:
        print 'Index writing exception'
        traceback.print_exc()
        import pdb; pdb.set_trace()
    print 'Written', xls_index_filename


def filepath_for_xls_from_triplestore_from_csv_filepath(
        senior_or_junior_filepath):
    return senior_or_junior_filepath \
        .replace('junior', 'organogram') \
        .replace('senior', 'organogram') \
        .replace('csv', 'xls')


def number_if_possible(num_str):
    try:
        return int(num_str)
    except ValueError:
        try:
            return float(num_str)
        except ValueError:
            return num_str


def int_if_possible(num_str):
    try:
        return int(num_str)
    except ValueError:
        return num_str


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csvs', nargs='*',
            help='filepaths of junior or senior CSVs (the pairs will be found automatically)')
    parser.add_argument('--where-uploads-unreliable', action='store_true')
    args = parser.parse_args()
    if args.where_uploads_unreliable:
        convert_csvs_where_uploads_unreliable()
    else:
        csv2xls_multiple(args.csvs)
