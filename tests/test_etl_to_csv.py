#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path
from nose.tools import assert_equal, assert_raises
import string

import pandas as pd

import etl_to_csv
from etl_to_csv import (
    main, load_xls_and_get_errors, in_sheet_validation_senior_columns,
    )

assert_equal.im_class.maxDiff = None

TEST_XLS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                               '../data/test-xls'))

class TestMain():
    def test_sample_senior_valid(self):
        lines = run_etl_on_file_and_return_csv_lines(
            TEST_XLS_DIR + '/sample-valid.xls', date='2016-09-30',
            senior_or_junior='senior')
        assert_equal(u'"Post Unique Reference","Name","Grade (or equivalent)","Job Title","Job/Team Function","Parent Department","Organisation","Unit","Contact Phone","Contact E-mail","Reports to Senior Post","Salary Cost of Reports (\xa3)","FTE","Actual Pay Floor (\xa3)","Actual Pay Ceiling (\xa3)","","Professional/Occupational Group","Notes","Valid?"', lines[0])
        assert_equal(u'"CEO","Bob Smith","SCS2","Chief Executive","Chief executive","Department for Culture, Media and Sport","Culture Agency","Culture Agency Unit","0300 123 1234","bob.smith@dau.org.uk","XX","1000345","1.00","120000","124999","","","","1"', lines[1])

    def test_sample_junior_valid(self):
        lines = run_etl_on_file_and_return_csv_lines(
            TEST_XLS_DIR + '/sample-valid.xls', date='2016-09-30',
            senior_or_junior='junior')
        assert_equal(u'"Parent Department","Organisation","Unit","Reporting Senior Post","Grade","Payscale Minimum (\xa3)","Payscale Maximum (\xa3)","Generic Job Title","Number of Posts in FTE","Professional/Occupational Group"', lines[0])
        assert_equal(u'"Department for Culture, Media and Sport","Culture Agency","Culture Agency Unit","CEO","Band A","13564","17594","CAU Assistant","1.00","Operational Delivery"', lines[1])

    def test_sample_senior_invalid(self):
        assert_raises(
            EtlError, run_etl_on_file_and_return_csv_lines,
            TEST_XLS_DIR + '/sample-invalid-senior.xls', date='2016-09-30')

    def test_sample_junior_invalid(self):
        assert_raises(
            EtlError, run_etl_on_file_and_return_csv_lines,
            TEST_XLS_DIR + '/sample-invalid-junior.xls', date='2016-09-30')


class TestErrorMessages():
    def test_sample_senior_invalid(self):
        senior, junior, errors, will_display = load_xls_and_get_errors(
            TEST_XLS_DIR + '/sample-invalid-senior.xls')
        assert_equal(['Sheet "(final data) senior-staff" has 1 invalid row. The problem is on row 4, as indicated by the red colour in cell S4.'], errors)

    def test_sample_junior_invalid(self):
        senior, junior, errors, will_display = load_xls_and_get_errors(
            TEST_XLS_DIR + '/sample-invalid-junior.xls')
        assert_equal(['Sheet "(final data) junior-staff" has 1 invalid row. The problem is on row 12, as indicated by the red colour in cell K12.'], errors)


SENIOR_COLUMN_HEADINGS = u'Post Unique Reference,Name,Grade (or equivalent),Job Title,Job/Team Function,Parent Department,Organisation,Unit,Contact Phone,Contact E-mail,Reports to Senior Post,Salary Cost of Reports (£),FTE,Actual Pay Floor (£),Actual Pay Ceiling (£),Total Pay (£),Professional/Occupational Group,Notes,Valid?'.split(',')

def senior_row(updates):
    row = [
        'CEO', 'Bob Smith', 'SCS2', 'Chief Executive ',
        'Chief executive', 'Department for Culture Media and Sport',
        'Culture Agency', 'Culture Agency Unit', '0300 123 1234',
        'bob.smith@dau.org.uk', 'XX', '1000345', '1.00', '120000',
        '124999', 'N/A', None, None, None]
    for col, value in updates:
        col_index = string.ascii_uppercase.index(col.upper())
        row[col_index] = value
    return row


class TestInSheetValidationSeniorColumns():
    # These tests should match the behaviour of the Excel sheet. Note any
    # improvements that could be made to the validation here, and look to add
    # tighter validation in the etl, but separate to the 'in-sheet' section.

    def test_valid(self):
        errors = in_sheet_validate_senior_row([])
        assert_equal(errors, [])

    def test_a_symbol(self):
        # better to have a whitelist
        errors = in_sheet_validate_senior_row_diff([('A', 'RP$FD')])
        assert_equal(errors, ['You cannot have punctuation/symbols in the "Post Unique Reference" column. See sheet "sheet" cell A4'])

    def test_a_xx(self):
        errors = in_sheet_validate_senior_row_diff([('A', 'AXXB')])
        assert_equal(errors, ['You cannot have "XX" in the "Post Unique Reference" column. See sheet "sheet" cell A4'])

    def test_a_space(self):
        errors = in_sheet_validate_senior_row_diff([('A', 'A B')])
        assert_equal(errors, ['You cannot have spaces in the "Post Unique Reference" column. See sheet "sheet" cell A4'])

    def test_a_blank(self):
        # blank value shouldn't be allowed but it is!
        errors = in_sheet_validate_senior_row_diff([('A', None)])
        assert_equal(errors, [])

    def test_a_blank_row(self):
        errors = in_sheet_validate_senior_row([None] * 19)
        assert_equal(errors, [])

    def test_b_not_in_post_b_is_a_string(self):
        errors = in_sheet_validate_senior_row_diff([('A', '0'), ('B', 'Bob')])
        assert_equal(errors, ['Because the "Post Unique Reference" is "0" (individual is paid but not in post) the name must be "N/D". See sheet "sheet" cell B4'])

    def test_b_not_in_post_b_is_blank(self):
        errors = in_sheet_validate_senior_row_diff([('A', '0'), ('B', '')])
        assert_equal(errors, ['Because the "Post Unique Reference" is "0" (individual is paid but not in post) the name must be "N/D". See sheet "sheet" cell B4'])

    def test_b_not_in_post_correct(self):
        errors = in_sheet_validate_senior_row_diff([('A', '0'), ('B', 'N/D')])
        assert_equal(errors, [])

    def test_b_is_n_a_and_pay_is_n_a(self):
        errors = in_sheet_validate_senior_row_diff([('B', 'N/A'), ('P', 'N/A')])
        assert_equal(errors, [u'The "Name" cannot be "N/A" (unless "Total Pay (\xa3)" is 0). See sheet "sheet" cell B4'])

    def test_b_is_n_a_and_pay_is_a_string(self):
        errors = in_sheet_validate_senior_row_diff([('B', 'N/A'), ('P', 'fff')])
        assert_equal(errors, [u'The "Name" cannot be "N/A" (unless "Total Pay (\xa3)" is 0). See sheet "sheet" cell B4'])

    def test_b_is_n_a_and_pay_is_1(self):
        errors = in_sheet_validate_senior_row_diff([('B', 'N/A'), ('P', 1)])
        assert_equal(errors, [u'The "Name" cannot be "N/A" (unless "Total Pay (\xa3)" is 0). See sheet "sheet" cell B4'])

    def test_b_is_n_a_and_pay_is_0(self):
        errors = in_sheet_validate_senior_row_diff([('B', 'N/A'), ('P', 0)])
        assert_equal(errors, [])

    def test_b_is_n_d_and_pay_is_n_a(self):
        errors = in_sheet_validate_senior_row_diff([('B', 'N/D'), ('P', 'N/A')])
        assert_equal(errors, [])

    def test_b_is_n_d_and_pay_is_a_string(self):
        errors = in_sheet_validate_senior_row_diff([('B', 'N/D'), ('P', 'fff')])
        assert_equal(errors, [u'The "Name" must be disclosed (cannot be "N/A" or "N/D") unless the "Total Pay (\xa3)" is 0. See sheet "sheet" cell B4'])

    def test_b_is_n_d_and_pay_is_1(self):
        errors = in_sheet_validate_senior_row_diff([('B', 'N/D'), ('P', 1)])
        assert_equal(errors, [u'The "Name" must be disclosed (cannot be "N/A" or "N/D") unless the "Total Pay (\xa3)" is 0. See sheet "sheet" cell B4'])

    def test_b_is_n_d_and_pay_is_0(self):
        errors = in_sheet_validate_senior_row_diff([('B', 'N/D'), ('P', 0)])
        assert_equal(errors, [])

    def test_b_is_blank_and_pay_is_1(self):
        errors = in_sheet_validate_senior_row_diff([('B', ''), ('P', 0)])
        assert_equal(errors, [u'The "Name" cannot be blank. See sheet "sheet" cell B4'])

    def test_b_is_blank_and_pay_is_0(self):
        errors = in_sheet_validate_senior_row_diff([('B', ''), ('P', 0)])
        assert_equal(errors, [u'The "Name" cannot be blank. See sheet "sheet" cell B4'])

    def test_b_is_blank_and_pay_is_a_string(self):
        errors = in_sheet_validate_senior_row_diff([('B', ''), ('P', 0)])
        assert_equal(errors, [u'The "Name" cannot be blank. See sheet "sheet" cell B4'])

    def test_b_is_blank_and_pay_is_n_a(self):
        errors = in_sheet_validate_senior_row_diff([('B', ''), ('P', 0)])
        assert_equal(errors, [u'The "Name" cannot be blank. See sheet "sheet" cell B4'])


def in_sheet_validate_senior_row_diff(row_updates):
    row = senior_row(row_updates)
    return in_sheet_validate_senior_row(row)

def in_sheet_validate_senior_row(row):
    df = pd.DataFrame([[''] * 19] + [[''] * 19] + [row],
                      columns=SENIOR_COLUMN_HEADINGS)
    errors = []
    in_sheet_validation_senior_columns(df.loc[2], df, errors, 'sheet')
    return errors

class MockArgs(object):
    date = None
    date_from_filename = False


def run_etl_on_file(input_xls_filepath, date='2011-03-31'):
    etl_to_csv.args = MockArgs()
    etl_to_csv.args.date = date
    ret = main(input_xls_filepath, '/tmp/')
    if ret is None:
        raise EtlError()
    senior_filepath, junior_filepath, senior, junior = ret
    return senior_filepath, junior_filepath, senior, junior


def run_etl_on_file_and_return_csv_lines(input_xls_filepath, date='2011-03-31',
                                         senior_or_junior='both'):
    senior_filepath, junior_filepath, senior, junior = \
        run_etl_on_file(input_xls_filepath, date=date)
    if senior_or_junior == 'senior':
        return csv_read(senior_filepath)
    elif senior_or_junior == 'junior':
        return csv_read(junior_filepath)
    elif senior_or_junior == 'both':
        return csv_read(senior_filepath), csv_read(junior_filepath)

def csv_read(filepath):
    with open(filepath, 'rb') as f:
        return f.read().strip().decode('utf8').split('\n')

class EtlError(Exception):
    pass
