#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
Converts Organograms XLS files into a pair of CSVs: junior and senior posts.
Does verification of the structure and values.
'''

# The script is structured so that errors are appended to a list
# rather than going straight to stderr. The script can therefore
# be reused to fulfil an API endpoint (for example).

# pip install pandas==0.17.0
import pandas
import numpy
import sys
import os.path
import json
from xlrd import XLRDError
import csv
import re
import argparse
import string


args = None

class ValidationFatalError(Exception):
    pass


def load_excel_store_errors(filename, sheet_name, errors, validation_errors, input_columns, rename_columns, blank_columns, integer_columns, string_columns, n_a_for_blanks_columns):
    """Carefully load an Excel file, taking care to log errors and produce clean output.
    You'll always receive a dataframe with the expected columns, though it might contain 0 rows if
    there are errors. Strings will be stored in the 'errors' array.
    If 'validation_errors' are inserted, it means some values are discarded, but you would not be prevented from displaying the rest of the data.
    """
    # Output columns can be different. Update according to the rename_columns dict:
    output_columns = [rename_columns.get(x,x) for x in input_columns]
    try:
        # need to convert strings at this stage or leading zeros get lost
        string_converters = dict((col, str) for col in string_columns)
        df = pandas.read_excel(filename,
                               sheet_name,
                               convert_float=True,
                               parse_cols=len(input_columns)-1,
                               converters=string_converters)
    except XLRDError, e:
        errors.append( str(e) )
        return pandas.DataFrame(columns=output_columns)
    # Verify number of columns
    if len(df.columns)!=len(input_columns):
        errors.append("Sheet '%s' contains %d columns. I expect at least %d columns."%(sheet_name,len(df.columns),len(input_columns)))
        return pandas.DataFrame(columns=output_columns)
    # Blank out columns
    for column_name in blank_columns:
        col_index = df.columns.tolist().index(column_name)
        df.drop(df.columns[col_index], axis=1, inplace=True)
        df.insert(col_index, column_name, '')
    # Softly correct column names
    for i in range(len(df.columns)):
        # Check column names are as expected. Also allow them to be the renamed
        # version, since old XLS templates had "Grade" instead of "Grade (or
        # equivalent)" for senior sheet. (And the CSVs follow the same pattern
        # - during 2011 they had "Grade" and subsequently they were "Grade (or
        # equivalent)")
        if df.columns[i] != input_columns[i] and \
                output_columns[i] != input_columns[i]:
            from string import uppercase
            errors.append("Wrong column title. "
                          "Sheet '%s' column %s: Title='%s' Expected='%s'" %
                          (sheet_name, uppercase[i], df.columns[i],
                           input_columns[i]))
    df.columns = output_columns
    # Filter null rows
    # (defined as having the first two columns both blank. junior roles
    # generated from triplestore don't have a parent organization set.)
    df = df.dropna(subset=df.columns[0:2], how='all')
    # Softly cast to integer (or N/A or N/D)
    def validate_int_or_na(column_name):
        def _inner(x):
            if pandas.isnull(x):
                # i.e. float.NaN. Cell contained e.g. 'N/A'
                return 'N/A'
            try:
                return str(int(round(x)))
            except (TypeError, ValueError):
                try:
                    # e.g. u'0'
                    return str(int(x))
                except (TypeError, ValueError):
                    # look for N/A and N/D plus all sorts of variations
                    text = re.sub('[^A-Z]', '', x.upper())
                    if text == 'NA':
                        return 'N/A'
                    if text == 'ND':
                        return 'N/D'
                    validation_errors.append('Expected numeric values in column "%s" (or N/A or N/D), but got text="%s".' % (column_name, x))
                    return 0
        return _inner
    # int type cannot store NaN, so use object type
    for column_name in integer_columns:
        df[column_name] = df[column_name].astype(object).map(validate_int_or_na(column_name))
    # Format any numbers in string columns
    for column_name in string_columns:
        if str(df[column_name].dtype).startswith('float'):
            # an int seems to get detected as float, so convert back to int first
            # or else you get a string like "1.0" instead of "1"
            # e.g. appointments_commission-30-09-2011.xls
            df[column_name] = df[column_name].astype(int)
        df[column_name] = df[column_name].astype(str)
    # Strip strings of spaces
    for column_name in df.columns:
        # columns with strings have detected 'object' type
        if df[column_name].dtype == 'O':
            df[column_name] = df[column_name].str.strip()
    # Blank cells might need to be changed to 'N/A'
    for column_name in n_a_for_blanks_columns:
        df[column_name] = df[column_name].fillna('N/A')
    return df


def load_senior(excel_filename, errors, validation_errors):
    input_columns = [
      u'Post Unique Reference',
      u'Name',
      u'Grade (or equivalent)',
      u'Job Title',
      u'Job/Team Function',
      u'Parent Department',
      u'Organisation',
      u'Unit',
      u'Contact Phone',
      u'Contact E-mail',
      u'Reports to Senior Post',
      u'Salary Cost of Reports (£)',
      u'FTE',
      u'Actual Pay Floor (£)',
      u'Actual Pay Ceiling (£)',
      u'Total Pay (£)',
      u'Professional/Occupational Group',
      u'Notes',
      u'Valid?']
    rename_columns = {
      u'Total Pay (£)': u'',
      u'Grade': u'Grade (or equivalent)',
    }
    blank_columns = {
      u'Total Pay (£)' : u'',
    }
    integer_columns = [
      u'Actual Pay Floor (£)',
      u'Actual Pay Ceiling (£)',
      u'Salary Cost of Reports (£)',
    ]
    string_columns = [
      u'Post Unique Reference',
      u'Reports to Senior Post',
    ]
    n_a_for_blanks_columns = [
      u'Contact Phone',
    ]
    sheet_name = '(final data) senior-staff'
    df = load_excel_store_errors(excel_filename, sheet_name, errors, validation_errors, input_columns, rename_columns, blank_columns, integer_columns, string_columns, n_a_for_blanks_columns)
    if df.dtypes['Post Unique Reference']==numpy.float64:
        df['Post Unique Reference'] = df['Post Unique Reference'].astype('int')
    in_sheet_validation(df, validation_errors, sheet_name, 'senior')
    return df


def load_junior(excel_filename, errors, validation_errors):
    input_columns = [
      u'Parent Department',
      u'Organisation',
      u'Unit',
      u'Reporting Senior Post',
      u'Grade',
      u'Payscale Minimum (£)',
      u'Payscale Maximum (£)',
      u'Generic Job Title',
      u'Number of Posts in FTE',
      u'Professional/Occupational Group',
      u'Valid?']
    integer_columns = [
      u'Payscale Minimum (£)',
      u'Payscale Maximum (£)'
    ]
    string_columns = [
      u'Reporting Senior Post',
    ]
    n_a_for_blanks_columns = []
    sheet_name = '(final data) junior-staff'
    df = load_excel_store_errors(excel_filename, sheet_name, errors, validation_errors, input_columns, {}, [], integer_columns, string_columns, n_a_for_blanks_columns)
    if df.dtypes['Reporting Senior Post']==numpy.float64:
        df['Reporting Senior Post'] = df['Reporting Senior Post'].fillna(-1).astype('int')
    in_sheet_validation(df, validation_errors, sheet_name, 'junior')
    # 'Valid?'' column doesn't get written in the junior sheet
    df.drop('Valid?', axis=1, inplace=True)
    return df


class MaxDepthError(Exception):
    pass


class PostReportsToUnknownPostError(Exception):
    pass


class PostReportLoopError(Exception):
    pass


def verify_graph(senior, junior, errors):
    '''Does checks on the senior and junior posts. Writes errors to supplied
    empty list. Returns None.

    May raise ValidationFatalError if it is so bad that the organogram cannot
    be displayed (e.g. no "top post").
    '''
    # ignore eliminated posts (i.e. don't exist any more)
    senior_ = senior[senior['Name'].astype(unicode) != "Eliminated"]

    # merge posts which are job shares
    # "post is duplicate save from name, pay columns, contact phone/email and
    #  notes"
    cols = set(senior_.columns.values) - set((
        'Name', u'Actual Pay Ceiling (£)', u'Actual Pay Floor (£)',
        'Total Pay', 'Contact Phone', 'Contact E-mail', 'Notes',
        'FTE'))
    senior_ = senior_.drop_duplicates(keep='first', subset=cols)

    # ensure at least one person is marked as top (XX)
    top_persons = senior_[senior_['Reports to Senior Post'].isin(('XX', 'xx'))]
    if len(top_persons) < 1:
        errors.append('Could not find a senior post with "Reports to Senior '
                      'Post" value of "XX" (i.e. the top role)')
        raise ValidationFatalError(errors[-1])
    top_person_refs = top_persons['Post Unique Reference'].values

    # do all seniors report to a correct senior ref? (aside from top person)
    senior_post_refs = set(senior_['Post Unique Reference'])
    senior_report_to_refs = set(senior_['Reports to Senior Post'])
    bad_senior_refs = senior_report_to_refs - senior_post_refs - \
        set(['XX', 'xx'])
    for ref in bad_senior_refs:
        errors.append('Senior post reporting to unknown senior post "%s"'
                      % ref)

    # check there are no orphans in this tree
    reports_to = {}
    for index, post in senior_.iterrows():
        ref = post['Post Unique Reference']
        if ref in reports_to:
            errors.append('Senior post "Post Unique Reference" is not unique. The only occasion where two rows can have the same reference is for a job share, and in this case the rows must be identical save from name, pay columns, contact phone/email, notes and FTE. '
                          'index:%s ref:"%s"' % (index, ref))
        reports_to[ref] = post['Reports to Senior Post']
        if ref == reports_to[ref]:
            errors.append('Senior post reports to him/herself. '
                          'index:%s ref:"%s"' % (index, ref))
    top_level_boss_by_ref = {}

    def get_top_level_boss_recursive(ref, posts_recursed=None):
        if posts_recursed is None:
            posts_recursed = []
        posts_recursed.append(ref)
        if ref in top_person_refs:
            return ref
        if ref in posts_recursed[:-1]:
            raise PostReportLoopError(' '.join(posts_recursed))
        if len(posts_recursed) > 100:
            raise MaxDepthError(' '.join(posts_recursed))
        if ref in top_level_boss_by_ref:
            return top_level_boss_by_ref[ref]
        try:
            boss_ref = reports_to[ref]
        except KeyError:
            known_refs = list(set(reports_to.keys()))
            # convert known_refs to int if poss, so it sorts better
            for i, ref_ in enumerate(known_refs):
                try:
                    known_refs[i] = int(ref_)
                except:
                    pass
            raise PostReportsToUnknownPostError(
                'Post reports to unknown post ref:"%s". '
                'Known post refs:"%s"' %
                (ref, sorted(known_refs)))
        try:
            top_level_boss_by_ref[ref] = get_top_level_boss_recursive(
                boss_ref, posts_recursed)
        except PostReportsToUnknownPostError, e:
            raise PostReportsToUnknownPostError('Error with senior post "%s": %s' % (ref, e))

        return top_level_boss_by_ref[ref]
    for index, post in senior_.iterrows():
        ref = post['Post Unique Reference']
        try:
            top_level_boss = get_top_level_boss_recursive(ref)
        except MaxDepthError, posts_recursed:
            errors.append('Could not follow the reporting structure from '
                          'Senior post %s "%s" up to the top in 100 steps - '
                          'is there a loop? Posts: %s'
                          % (index, ref, posts_recursed))
        except PostReportsToUnknownPostError, e:
            errors.append(str(e))
        except PostReportLoopError, posts_recursed:
            errors.append('Reporting structure from Senior post %s "%s" '
                          'ended up in a loop: %s'
                          % (index, ref, posts_recursed))
        else:
            if top_level_boss not in top_person_refs:
                errors.append('Reporting from Senior post %s "%s" up to the '
                              'top results in "%s" rather than "XX"' %
                              (index, ref, top_level_boss))

    # do all juniors report to a correct senior ref?
    junior_report_to_refs = set(junior['Reporting Senior Post'])
    bad_junior_refs = junior_report_to_refs - senior_post_refs
    for ref in bad_junior_refs:
        errors.append('Junior post reporting to unknown senior post "%s"'
                      % ref)

def row_name(row_index):
    '''
    0 returns '2' (first value, after the header row)
    '''
    return row_index + 2

def column_name(column_index):
    '''
    0 returns 'A' (left-most column)
    '''
    return string.ascii_uppercase[column_index]

def cell_name(row_index, column_index):
    '''
    (0, 0) returns 'A2' (top-left value, after the header row)
    (12, 2) returns 'B14'
    '''
    return '%s%d' % (column_name(column_index), row_name(row_index))

def in_sheet_validation(df, validation_errors, sheet_name, junior_or_senior):
    # Row validation indication
    validation_column = df.columns.get_loc('Valid?') # equivalent to S
    rows_marked_invalid = df[df['Valid?'] == 0]
    if len(rows_marked_invalid):
        row = rows_marked_invalid.head(1)
        row_index = row.index[0]
        err = 'Sheet "%s" has %d invalid row%s. The %sproblem is on row %d, as indicated by the red colour in cell %s.' % (sheet_name, len(rows_marked_invalid), 's' if len(rows_marked_invalid) > 1 else '', 'first ' if len(rows_marked_invalid) > 1 else '', row_name(row_index), cell_name(row_index, validation_column))
        validation_errors.append(err)

def get_date_from_filename(filename):
    match = re.search(r'(\d{4}-\d{2}-\d{2})', filename) or \
        re.search(r'(\d{2}-\d{2}-\d{4})', filename)
    assert match, 'Cannot find date in filename: %s' % filename
    return match.groups()[0]


def get_verify_level(graph):
    # parse graph date
    graph_match = re.match(
        r'^(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2})$',
        graph) or \
        re.match(
        r'^(?P<day>\d{2})-(?P<month>\d{2})-(?P<year>\d{4})$',
        graph)
    assert graph_match, \
        'Could not parse graph YYYY-MM-DD / DD-MM-YYYY: %r' % graph
    graph = graph_match.groupdict()
    graph['year'] = int(graph['year'])
    graph['month'] = int(graph['month'])

    # verify level based on the date
    if graph['year'] == 2011:
        # Be very lenient - overlook all errors for these early 2011 ones
        # because the data clearly wasn't validated at this time:
        # * some posts are orphaned
        # * some posts report to posts which don't exist
        # * some post reporting loops (including roles reporting to himself)
        # * some job-shares are people of different grades so you get errors
        #   about duplicate post refs.
        return 'load'
    elif graph['year'] <= 2015 or \
            (graph['year'] == 2016 and graph['month'] == 3):
        # Be quite lenient. During 2012 - 2016/03 TSO did only basic validation
        # and we see errors:
        # * 'Senior post "Post Unique Reference" is not unique'
        # * u'Expected numeric values in column "Actual Pay '
        # * 'Senior post reports to him/herself.'
        # * 'Senior post reporting to unknown senior post'
        # * 'Junior post reporting to unknown senior post'
        # * 'ended up in a loop'
        # * 'Post reports to unknown post'
        return 'load and display'
    else:
        # Drupal-based workflow actually displays the problems to the user, so
        # we can enforce all errors
        return 'load, display and be valid'


def load_xls_and_get_errors(xls_filename):
    '''
    Used by tso_combined.py
    Returns: (senior, junior, errors, will_display)
    '''
    errors = []
    validation_errors = []
    senior = load_senior(xls_filename, errors, validation_errors)
    junior = load_junior(xls_filename, errors, validation_errors)

    if errors:
        return None, None, errors + validation_errors, False

    errors = validation_errors
    try:
        verify_graph(senior, junior, errors)
    except ValidationFatalError, e:
        # display error - organogram is not displayable
        return None, None, [unicode(e)], False

    # If we get this far then it will display, although there might be problems
    # with some posts
    errors = dedupe_list(errors)
    return senior, junior, errors, True


def print_error(error_msg):
    print 'ERROR:', error_msg.encode('utf8')  # encoding for Drupal exec()


def load_xls_and_print_errors(xls_filename, verify_level):
    '''
    Loads the XLS, verifies it to an appropriate level and returns the data.

    If errors are not acceptable, it prints them and returns None
    '''
    load_errors = []
    validation_errors = []
    senior = load_senior(xls_filename, load_errors, validation_errors)
    junior = load_junior(xls_filename, load_errors, validation_errors)

    if load_errors:
        print 'Critical error(s):'
        for error in load_errors:
            print_error(error)
        # errors mean no rows can be got from the file, so can't do anything
        return
    if validation_errors and verify_level == 'load, display and be valid':
        print 'Validation error(s) during load:'
        for error in validation_errors:
            print_error(error)
        return

    if verify_level != 'load':
        validate_errors = []
        try:
            verify_graph(senior, junior, validate_errors)
        except ValidationFatalError, e:
            # display error - organogram is not displayable
            print_error(unicode(e))
            return

        if verify_level == 'load, display and be valid' and validate_errors:
            for error in dedupe_list(validate_errors):
                print_error(error)
            return

    return senior, junior


def dedupe_list(things):
    seen = set()
    seen_add = seen.add
    return [x for x in things if not (x in seen or seen_add(x))]


def main(input_xls_filepath, output_folder):
    print "Loading", input_xls_filepath

    if args.date:
        verify_level = get_verify_level(args.date)
    elif args.date_from_filename:
        date_ = get_date_from_filename(input_xls_filepath)
        verify_level = get_verify_level(date_)
    else:
        verify_level = 'load, display and be valid'
    data = load_xls_and_print_errors(input_xls_filepath, verify_level)
    if data is None:
        # fatal error has been printed
        return
    senior, junior = data

    # Calculate Organogram name
    _org = senior['Organisation']
    _org = _org[_org.notnull()].unique()
    name = " & ".join(_org)
    if name == u'Ministry of Defence':
        _unit = senior['Unit']
        _unit = _unit[_unit.notnull()].unique()
        name += " - " + (" & ".join(_unit))
    # Write output files
    basename, extension = os.path.splitext(os.path.basename(input_xls_filepath))
    senior_filename = os.path.join(output_folder, basename + '-senior.csv')
    junior_filename = os.path.join(output_folder, basename + '-junior.csv')
    print "Writing", senior_filename
    csv_options = dict(encoding="utf-8",
                       quoting=csv.QUOTE_ALL,
                       float_format='%.2f',
                       index=False)
    senior.to_csv(senior_filename, **csv_options)
    print "Writing", junior_filename
    junior.to_csv(junior_filename, **csv_options)
    # Write index file - used by Drupal
    index = [{'name': name, 'value': basename}]  # a list because of legacy
    index = sorted(index, key=lambda x: x['name'])
    index_filename = os.path.join(output_folder, 'index.json')
    print "Writing index file:", index_filename
    with open(index_filename, 'w') as f:
        json.dump(index, f)
    print "Done."
    # return values are only for the tests
    return senior_filename, junior_filename, senior, junior


def usage():
    print "Usage: %s input_1.xls input_2.xls ... output_folder/" % sys.argv[0]
    sys.exit()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--date',
                        help='The strength of verify level picked according '
                             'to the date of the data (YYYY-MM-DD)')
    parser.add_argument('--date-from-filename',
                        action='store_true',
                        help='The strength of verify level picked according '
                             'to the date of the data, extracted from the '
                             'filename (for manual tests only!)')
    parser.add_argument('input_xls_filepath')
    parser.add_argument('output_folder')
    args = parser.parse_args()
    if not os.path.isdir(args.output_folder):
        parser.error("Error: Not a directory: %s" % args.output_folder)
    if not os.path.exists(args.input_xls_filepath):
        parser.error("Error: File not found: %s" % args.input_xls_filepath)
    main(args.input_xls_filepath, args.output_folder)
