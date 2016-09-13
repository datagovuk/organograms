#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os.path
from nose.tools import assert_equal, assert_raises

import etl_to_csv
from etl_to_csv import main, load_xls_and_get_errors

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
