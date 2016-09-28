#!/usr/bin/env python
# -*- coding: utf-8 -*-
from StringIO import StringIO
import unicodecsv

from nose.tools import assert_equal
import mock

import compare_posts
from compare_posts import get_triplestore_posts, save_posts_csv


assert_equal.im_class.maxDiff = None
CSV_FILEPATH = '/tmp/organogram_test'
compare_posts.filepath_for_csv_from_triplestore = \
    mock.MagicMock(return_value=CSV_FILEPATH)
ACAS_URI = 'http://reference.data.gov.uk/id/public-body/advisory-conciliation-and-arbitration-service'
ACAS_TITLE = 'Advisory, Conciliation and Arbitration Service'

class TestTriplestorePostsToCsv(object):
    def test_header_senior(self):
        out = convert_to_csv(ACAS_URI, ACAS_TITLE, '2012-09-30', 'senior')
        # * quote every value - data/dgu/tso-csv/advisory_conciliation_and_arbitration_service-30-09-2012-senior.csv
        # * "URI" added on the end because it is handy
        assert_equal(u'"Post Unique Reference","Name","Grade (or equivalent)","Job Title","Job/Team Function","Parent Department","Organisation","Unit","Contact Phone","Contact E-mail","Reports to Senior Post","Salary Cost of Reports (£)","FTE","Actual Pay Floor (£)","Actual Pay Ceiling (£)","","Professional/Occupational Group","Notes","Valid?","URI"', out[0])

    def test_header_junior(self):
        out = convert_to_csv(ACAS_URI, ACAS_TITLE, '2012-09-30', 'junior')
        assert_equal(u'"Parent Department","Organisation","Unit","Reporting Senior Post","Grade","Payscale Minimum (£)","Payscale Maximum (£)","Generic Job Title","Number of Posts in FTE","Professional/Occupational Group"', out[0])

    def test_rows_format_senior(self):
        rows = convert_to_csv(ACAS_URI, ACAS_TITLE, '2012-09-30', 'senior')
        row = get_senior_row(rows, post_ref='5')
        assert row.startswith('"5","N/D","SCS1","Chief Operating Officer","Provide good customer service, Collective conciliation, Helpline"'), row

    def test_values_senior(self):
        rows = convert_to_csv(ACAS_URI, ACAS_TITLE, '2012-09-30', 'senior',
                              include_salary_cost_of_reports=True)
        row = csv_string_as_dicts(rows, post_ref='5')
        # from data/dgu/tso-csv/advisory_conciliation_and_arbitration_service-30-09-2012-senior.csv
        tso_row = unicode_dict(dict(zip(TSO_HEADER, ("5","N/D","SCS1","Chief Operating Officer","Provide good customer service, Collective conciliation, Helpline","Department for Business Innovation and Skills","Advisory, Conciliation and Arbitration Service","Delivery","N/D","pay_enquiries@acas.org.uk","1","191944227","1.00","N/A","","","Operational Delivery","","1"))))

        expected_row = tso_row
        expected_row[u'Parent Department'] = u'parent dept'
        expected_row[u'Actual Pay Floor (£)'] = u'N/D'  # triplestore returns blank but is SCS1 so it should be N/D rather than N/A
        expected_row[u'Actual Pay Ceiling (£)'] = u'N/D'
        expected_row[u'FTE'] = u'1'  # without the decimal places is absolutely fine
        expected_row[u'URI'] = u'http://reference.data.gov.uk/id/public-body/advisory-conciliation-and-arbitration-service/post/5'
        expected_row[u'Valid?'] = u''
        assert_equal(expected_row, row)



def convert_to_csv(body_uri, body_title, graph, senior_or_junior,
                   include_salary_cost_of_reports=False):
    compare_posts.args = MockArgs()
    if senior_or_junior == 'junior':
        compare_posts.args.junior = True
    compare_posts.args.include_salary_cost_of_reports = \
        include_salary_cost_of_reports
    senior_posts, junior_posts, num_eliminated_posts = \
        get_triplestore_posts(body_uri, graph, print_urls=True)
    posts = senior_posts if senior_or_junior == 'senior' else junior_posts
    print '%s posts %s %s ' % (len(posts), body_uri.split('/')[0], graph)
    return get_posts_csv(body_title, graph, senior_or_junior, posts)

def get_posts_csv(body_title, graph, senior_or_junior, posts):
    save_posts_csv(body_title, graph, senior_or_junior, posts, 'parent dept')
    with open(CSV_FILEPATH, 'rb') as f:
        return f.read().strip().decode('utf8').split('\r\n')

def get_senior_row(rows, post_ref):
    post_ref_str = '"%s"' % post_ref
    for row in rows:
        if row.startswith(post_ref_str):
            return row
    raise ValueError('Couldn\'t find row with post_ref: %r' % post_ref)

def csv_string_as_dicts(csv_string, post_ref=None):
    csv_reader = unicodecsv.DictReader(StringIO('\n'.join(csv_string).encode('utf8')))
    items = [item for item in csv_reader]
    if post_ref:
        for item in items:
            if item['Post Unique Reference'] == post_ref:
                return item
        raise ValueError('Couldn\'t find row with post_ref: %r' % post_ref)

class MockArgs(object):
    junior = False
    include_salary_cost_of_reports = False

TSO_HEADER = ("Post Unique Reference","Name","Grade (or equivalent)","Job Title","Job/Team Function","Parent Department","Organisation","Unit","Contact Phone","Contact E-mail","Reports to Senior Post",u"Salary Cost of Reports (£)","FTE",u"Actual Pay Floor (£)",u"Actual Pay Ceiling (£)","","Professional/Occupational Group","Notes","Valid?")

def unicode_dict(dict_):
    new_dict = {}
    for k, v in dict_.items():
        if isinstance(k, str):
            k = unicode(k)
        if isinstance(v, str):
            v = unicode(v)
        new_dict[k] = v
    return new_dict
