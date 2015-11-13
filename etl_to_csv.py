#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Quick script to pull apart official Organograms XLS files,
# clean them up, verify the structure of the data, and output
# a pair of CSVs: Junior and Senior staff lists.
#
# The script is structured so that errors are appended to a list
# rather than going straight to stderr. The script can therefore
# be reused to fulfil an API endpoint (for example).
#
# Command-line use: etl_to_csv.py infile1.xls infile2.xls ... output_folder/
#
import pandas
import numpy
import sys
import os.path
import json
from xlrd import XLRDError


class ValidationFatalError(Exception):
    pass


def load_excel_store_errors(filename, sheet_name, errors, input_columns, rename_columns, integer_columns, string_columns):
    """Carefully load an Excel file, taking care to log errors and produce clean output.
    You'll always receive a dataframe with the expected columns, though it might contain 0 rows if
    there are errors. Strings will be stored in the 'errors' array."""
    # Output columns can be different. Update according to the rename_columns hash:
    output_columns = [ rename_columns.get(x,x) for x in input_columns ]
    try:
        df = pandas.read_excel(filename,
                               sheet_name,
                               convert_float=True,
                               parse_cols=len(input_columns)-1)
    except XLRDError, e:
        errors.append( str(e) )
        return pandas.DataFrame(columns=output_columns)
    # Verify number of columns
    if len(df.columns)!=len(input_columns):
        errors.append("Sheet %s contains %d columns. I expect at least %d columns."%(sheet_name,len(df.columns),len(input_columns)))
        return pandas.DataFrame(columns=output_columns)
    # Softly correct column names
    for i in range(len(df.columns)):
        if df.columns[i]!=input_columns[i]:
            from string import uppercase
            errors.append("Sheet %s column %s: Title='%s' Expected='%s'" % (sheet_name,uppercase[i],df.columns[i],input_columns[i]))
    df.columns = output_columns
    # Filter null rows
    column0 = df[ df.columns[0] ]
    df = df[ column0.notnull() ]
    # Softly cast to integer
    def cast_to_int(column_name):
        def _inner(x):
            if pandas.isnull(x): return 0
            try:
                return int(x)
            except ValueError:
                errors.append('Expected numeric values in column "%s", but got text="%s".'%(column_name,x))
                return 0
        return _inner
    for column_name in integer_columns:
        df[column_name] = df[column_name].map( cast_to_int(column_name) ).astype(int)
    for column_name in string_columns:
        if str(df[column_name].dtype).startswith('float'):
            # an int seems to get detected as float, so convert back to int first
            # or else you get a string like "1.0" instead of "1"
            # e.g. appointments_commission-30-09-2011.xls
            df[column_name] = df[column_name].astype(int)
        df[column_name] = df[column_name].astype(str)
    return df


def load_senior(excel_filename,errors):
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
      u'Total Pay (£)' : u'',
      u'Grade (or equivalent)' : u'Grade',
    }
    integer_columns = [
      u'Actual Pay Floor (£)',
      u'Actual Pay Ceiling (£)',
      u'',
    ]
    string_columns = [
      u'Post Unique Reference',
      u'Reports to Senior Post',
    ]
    df = load_excel_store_errors(excel_filename, '(final data) senior-staff', errors, input_columns, rename_columns, integer_columns, string_columns)
    if df.dtypes['Post Unique Reference']==numpy.float64:
        df['Post Unique Reference'] = df['Post Unique Reference'].astype('int')
    return df


def load_junior(excel_filename,errors):
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
      u'Professional/Occupational Group']
    integer_columns = [
      u'Payscale Minimum (£)',
      u'Payscale Maximum (£)'
    ]
    string_columns = [
      u'Reporting Senior Post',
    ]
    df = load_excel_store_errors(excel_filename, '(final data) junior-staff', errors, input_columns, {}, integer_columns, string_columns)
    if df.dtypes['Reporting Senior Post']==numpy.float64:
        df['Reporting Senior Post'] = df['Reporting Senior Post'].fillna(-1).astype('int')
    return df


class MaxDepthError(Exception):
    pass


def verify_graph(senior, junior, errors):
    # ignore eliminated posts (i.e. don't exist any more)
    senior_ = senior[senior['Name'] != "Eliminated"]

    # merge posts which are job shares
    # "post is duplicate save from name, pay columns, contact phone/email and
    #  notes"
    cols = set(senior_.columns.values) - set((
        'Name', u'Actual Pay Ceiling (£)', u'Actual Pay Floor (£)',
        'Total Pay', 'Contact Phone', 'Contact E-mail', 'Notes',
        'FTE'))
    senior_ = senior_.drop_duplicates(keep='first', subset=cols)

    # ensure one person is marked as top (XX)
    top_persons = senior_[senior_['Reports to Senior Post'].isin(('XX', 'xx'))]
    if len(top_persons) != 1:
        errors.append('There should be 1 senior post with "Reports to Senior '
                      'Post" value of "XX" but instead found: %s'
                      % len(top_persons))
        raise ValidationFatalError(errors[-1])
    top_person_ref = top_persons['Post Unique Reference'][top_persons['Post Unique Reference'].index[0]]

    # do all seniors report to a correct senior ref? (aside from top person)
    senior_post_refs = set(senior_['Post Unique Reference'])
    senior_report_to_refs = set(senior_['Reports to Senior Post'])
    bad_senior_refs = senior_report_to_refs - senior_post_refs - set(['XX', 'xx'])
    for ref in bad_senior_refs:
        errors.append('Senior post reporting to unknown senior post "%s"'
                      % ref)

    # check there are no orphans in this tree
    reports_to = {}
    for index, post in senior_.iterrows():
        ref = post['Post Unique Reference']
        if ref in reports_to:
            errors.append('Senior post "Post Unique Reference" is not unique: '
                          '%s "%s"' % (index, ref))
        reports_to[ref] = post['Reports to Senior Post']
    top_level_boss_by_ref = {}
    def get_top_level_boss_recursive(ref, depth=0):
        if ref == top_person_ref:
            return ref
        if depth > 100:
            raise MaxDepthError()
        if ref in top_level_boss_by_ref:
            return top_level_boss_by_ref[ref]
        try:
            boss_ref = reports_to[ref]
        except KeyError, e:
            print e
            import pdb; pdb.set_trace()
        top_level_boss_by_ref[ref] = get_top_level_boss_recursive(boss_ref,
                                                                  depth + 1)
        return top_level_boss_by_ref[ref]
    for index, post in senior_.iterrows():
        ref = post['Post Unique Reference']
        try:
            top_level_boss = get_top_level_boss_recursive(ref)
        except MaxDepthError:
            errors.append('Could not follow the reporting structure from '
                          'Senior post %s "%s" up to the top in 100 steps - '
                          'is there a loop?' % (index, ref))
        if top_level_boss != top_person_ref:
            errors.append('Reporting from Senior post %s "%s" up to the top '
                          'results in "%s" rather than "XX"' %
                          (index, ref, top_level_boss))

    # do all juniors report to a correct senior ref?
    junior_report_to_refs = set(junior['Reporting Senior Post'])
    bad_junior_refs = junior_report_to_refs - senior_post_refs
    for ref in bad_junior_refs:
        errors.append('Junior post reporting to unknown senior post "%s"'
                      % ref)


def main(input_files, output_folder):
    index = []
    for filename in input_files:
        print "-"*40
        print "Loading", filename
        errors = []
        senior = load_senior(filename, errors)
        junior = load_junior(filename, errors)
        try:
            verify_graph(senior, junior, errors)
        except ValidationFatalError, e:
            print "FATAL ERROR:", e
            return
        for error in list(set(errors)):
            print "ERROR:", error
        # Calculate Organogram name
        _org = senior['Organisation']
        _org = _org[_org.notnull()].unique()
        name = " & ".join(_org)
        if name == u'Ministry of Defence':
            _unit = senior['Unit']
            _unit = _unit[_unit.notnull()].unique()
            name += " - " + (" & ".join(_unit))
        # Write output files
        basename, extension = os.path.splitext(os.path.basename(filename))
        senior_filename = os.path.join(output_folder, basename+'-senior.csv')
        junior_filename = os.path.join(output_folder, basename+'-junior.csv')
        print "Writing", senior_filename
        senior.to_csv(senior_filename,encoding="utf-8")
        print "Writing", junior_filename
        junior.to_csv(junior_filename,encoding="utf-8")
        # Update index
        index.append({'name': name, 'value': basename})
    index = sorted(index, key=lambda x: x['name'])
    index_filename = os.path.join(output_folder, 'index.json')
    print "="*40
    print "Writing index file:", index_filename
    with open(index_filename, 'w') as f:
        json.dump(index, f)
    print "Done."

def usage():
    print "Usage: %s input_1.xls input_2.xls ... output_folder/" % sys.argv[0]
    sys.exit()

if __name__ == '__main__':
    if len(sys.argv) < 3:
        usage()
    input_files = sys.argv[1:-1]
    output_folder = sys.argv[-1]
    if not os.path.isdir(output_folder):
        print "Error: Not a directory: %s" % output_folder
        usage()
    for f in input_files:
        if not os.path.exists(f):
            print "Error: File not found: %s" % f
            usage()
    main(input_files, output_folder)
