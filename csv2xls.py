#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Takes an organogram junior csv and senior csv and converts to an organogram
xls.
'''
import unicodecsv
import xlwt
import argparse

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

def csv2xls(senior_or_junior_csv_filepaths):
    for senior_or_junior_filepath in senior_or_junior_csv_filepaths:
        assert 'senior' in senior_or_junior_filepath or \
            'junior' in senior_or_junior_filepath, \
            'filepath needs junior/senior in it'
        csv_filepaths = dict(
            senior=senior_or_junior_filepath.replace('junior', 'senior'),
            junior=senior_or_junior_filepath.replace('senior', 'junior'))
        xls_filepath = senior_or_junior_filepath.replace('junior', 'organogram').replace('senior', 'organogram').replace('csv', 'xls')

        workbook = xlwt.Workbook()
        for level, csv_filepath in csv_filepaths.items():
            # Read CSV
            with open(csv_filepath, 'rb') as csv_read_file:
                csv_reader = unicodecsv.reader(csv_read_file)
                csv_headers = csv_reader.next()
                # Append None to each row, as a placeholder for 'Total Pay'/'Valid'
                csv_rows = [row + [None, None] for row in csv_reader]

            # Adjust CSV
            if level == 'senior':
                csv_headers[csv_headers.index('Grade')] = 'Grade (or equivalent)'
            csv_headers.append(u'Total Pay (£)')
            if level == 'junior':
                csv_headers.append('Valid?')
            # column mapping - for each of the XLS columns it gives the CSV column
            cols_map = [csv_headers.index(xls_col)
                        for xls_col in XLS_COL_HEADERS[level]]
            out_rows = [XLS_COL_HEADERS[level]]
            for row in sorted(csv_rows, key=lambda r: int_if_possible(r[0])):
                out_row = [row[csv_col_index] for csv_col_index in cols_map]
                out_rows.append(out_row)

            sheet = workbook.add_sheet('(final data) %s-staff' % level)
            for r, row in enumerate(out_rows):
                for c, value in enumerate(row):
                    sheet.write(r, c, value)
        workbook.save(xls_filepath)
        print 'Written %s' % xls_filepath

    if len(senior_or_junior_csv_filepaths) == 1:
        # for when called by tso_combined.py
        return xls_filepath


def int_if_possible(num_str):
    try:
        return int(num_str)
    except ValueError:
        return num_str


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('csvs', nargs='+',
            help='filepaths of junior or senior CSVs (the pairs will be found automatically)')
    args = parser.parse_args()
    csv2xls(args.csvs)
