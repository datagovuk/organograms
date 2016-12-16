'''Run these tests with:

python -m unittest test_reference
or
python -m unittest test_reference.TestClass.test_method

'''
import unittest

import requests
import requests_cache
requests_cache.install_cache(backend='memory')  # cached only for this run

def assert_equal(a, b):
    assert a == b, '%r != %r' % (a, b)

def assert_not_equal(a, b):
    assert a != b, '%r == %r' % (a, b)

urls_that_should_resolve = '''
http://reference.data.gov.uk/2011-03-31/doc/public-body/environment-agency
'''.split()

def for_each_url(url_list, function, *kargs, **kwargs):
    if isinstance(url_list, basestring):
        url_list = url_list.split()
    for url in url_list:
        function(url.strip(), *kargs, **kwargs)

def url_resolves(url):
    response = requests.get(url)
    if response.status_code != 200:
        assert 0, 'Doesnt resolve: %s' % url

def url_redirects(url):
    response = requests.get(url)
    assert_not_equal(url, response.url)

def url_doesnt_redirect(url, except_to_archive=False):
    response = requests.get(url)
    if url != response.url and except_to_archive:
        if response.url.startswith('http://webarchive.nationalarchives.gov.uk'):
            return

    assert_equal(url, response.url)

def url_redirect_is(url, redirects_to):
    response = requests.get(url)
    response_url = response.url
    # but allow archived version
    if 'http://webarchive.nationalarchives.gov.uk/+/' in response_url:
        response_url = response_url.replace('http://webarchive.nationalarchives.gov.uk/+/', '')
    assert_equal(response_url, redirects_to)


class TestDepartments(unittest.TestCase):

    def test_dept(self):
        urls = '''
            http://reference.data.gov.uk/id/department/co
            http://reference.data.gov.uk/2011-09-30/doc/department/co
            http://reference.data.gov.uk/2011-09-30/doc/department/co.ttl
            http://reference.data.gov.uk/2011-09-30/doc/department/co.json
            '''.split()
        for_each_url(urls, url_resolves)
        url_redirects('http://reference.data.gov.uk/id/department/co')
        url_redirect_is('http://reference.data.gov.uk/id/department/co',
            'http://reference.data.gov.uk/2011-09-30/doc/department/co')
        url_doesnt_redirect('http://reference.data.gov.uk/2011-09-30/doc/department/co', except_to_archive=True)
        url_doesnt_redirect('http://reference.data.gov.uk/2011-09-30/doc/department/co.ttl', except_to_archive=True)

    def test_publicbody(self):
        url = 'http://reference.data.gov.uk/id/public-body/big-lottery-fund'
        url_resolves(url)
        url_redirect_is(
            url,
            'http://reference.data.gov.uk/2011-09-30/doc/public-body/big-lottery-fund')

    def test_unit(self):
        url = 'http://reference.data.gov.uk/id/department/co/unit/boundary-commission-for-england'
        url_resolves(url)
        url_redirect_is(
            url,
            'http://reference.data.gov.uk/2011-09-30/doc/department/co/unit/boundary-commission-for-england')

class TestOgl(unittest.TestCase):

    def test_redirect(self):
        response = requests.get('http://reference.data.gov.uk/id/open-government-licence')
        assert response.url in (
            'http://www.nationalarchives.gov.uk/doc/open-government-licence/version/2/'
            'http://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/'
            )

class TestIntervals(unittest.TestCase):

    def test_vocabulary(self):
        url = 'http://reference.data.gov.uk/def/intervals'
        url_resolves(url)
        url_doesnt_redirect(url)

    def test_vocabulary_formats(self):
        urls = '''
            http://reference.data.gov.uk/def/intervals.ttl
            http://reference.data.gov.uk/def/intervals.n3
            http://reference.data.gov.uk/def/intervals.rdf
        '''
        for_each_url(urls, url_resolves)
        for_each_url(urls, url_doesnt_redirect)

    def test_def_linked_from_vocabulary(self):
        urls = '''
            http://reference.data.gov.uk/def/intervals/IntervalList
            http://reference.data.gov.uk/def/intervals/one-second
            http://reference.data.gov.uk/def/intervals/Quarter
            '''
        for_each_url(urls, url_resolves)
        for_each_url(urls, url_redirects)
        url_redirect_is(
            'http://reference.data.gov.uk/def/intervals/IntervalList',
            'http://reference.data.gov.uk/def/intervals')
        url_redirect_is(
            'http://reference.data.gov.uk/def/intervals/CalendarYear.ttl',
            'http://reference.data.gov.uk/def/intervals.ttl')

    def test_other_defs(self):
        urls = '''
            http://reference.data.gov.uk/id/government-year
            http://reference.data.gov.uk/id/government-half
            http://reference.data.gov.uk/id/government-quarter
            http://reference.data.gov.uk/id/government-week
            http://reference.data.gov.uk/id/government-year/2010-2011
            http://reference.data.gov.uk/id/government-half/2010-2011/H1
            http://reference.data.gov.uk/id/government-quarter/2006-2007/Q1
            http://reference.data.gov.uk/id/government-week/2006-2007/W01
            http://reference.data.gov.uk/id/quarter/2006-Q1
            http://reference.data.gov.uk/id/gregorian-instant/2006-01-01T00:00:00
            http://reference.data.gov.uk/id/gregorian-interval/2006-01-01T00:00:00/P3M
            http://reference.data.gov.uk/id/month/2006-02
            http://reference.data.gov.uk/id/year/2006
            http://reference.data.gov.uk/id/half/2006-H1
            http://reference.data.gov.uk/id/day/2016-01-01
            http://reference.data.gov.uk/id/hour/2016-01-01T10
            http://reference.data.gov.uk/id/minute/2016-01-01T10:15
            http://reference.data.gov.uk/id/second/2016-01-01T10:15:59
            http://reference.data.gov.uk/id/week/2016-W51
            http://reference.data.gov.uk/id/gregorian-year/2016
            http://reference.data.gov.uk/id/gregorian-half/2016-H1
            http://reference.data.gov.uk/id/gregorian-day/2016-01-01
            http://reference.data.gov.uk/id/gregorian-hour/2016-01-01T10
            http://reference.data.gov.uk/id/gregorian-minute/2016-01-01T10:15
            http://reference.data.gov.uk/id/gregorian-second/2016-01-01T10:15:59
            http://reference.data.gov.uk/id/gregorian-week/2016-W51
            http://reference.data.gov.uk/doc/gregorian-interval.nt

            http://reference.data.gov.uk/doc/quarter/2006-Q1
            http://reference.data.gov.uk/doc/quarter/2006-Q1.rdf
            http://reference.data.gov.uk/doc/quarter/2006-Q1.ttl
            http://reference.data.gov.uk/doc/quarter/2006-Q1.n3
            http://reference.data.gov.uk/doc/quarter/2006-Q1.nt
            http://reference.data.gov.uk/doc/quarter/2006-Q1.json

            http://reference.data.gov.uk/doc/government-year
            http://reference.data.gov.uk/doc/government-half
            http://reference.data.gov.uk/doc/government-quarter
            http://reference.data.gov.uk/doc/government-week
            http://reference.data.gov.uk/doc/government-year/2010-2011
            http://reference.data.gov.uk/doc/government-half/2010-2011/H1
            http://reference.data.gov.uk/doc/government-quarter/2006-2007/Q1
            http://reference.data.gov.uk/doc/government-week/2006-2007/W01
            http://reference.data.gov.uk/doc/quarter/2006-Q1
            http://reference.data.gov.uk/doc/gregorian-instant/2006-01-01T00:00:00
            http://reference.data.gov.uk/doc/gregorian-interval/2006-01-01T00:00:00/P3M
            http://reference.data.gov.uk/doc/month/2006-02
            http://reference.data.gov.uk/doc/year/2006
            http://reference.data.gov.uk/doc/half/2006-H1
            http://reference.data.gov.uk/doc/day/2016-01-01
            http://reference.data.gov.uk/doc/hour/2016-01-01T10
            http://reference.data.gov.uk/doc/minute/2016-01-01T10:15
            http://reference.data.gov.uk/doc/second/2016-01-01T10:15:59
            http://reference.data.gov.uk/doc/week/2016-W51
            http://reference.data.gov.uk/doc/gregorian-year/2016
            http://reference.data.gov.uk/doc/gregorian-half/2016-H1
            http://reference.data.gov.uk/doc/gregorian-day/2016-01-01
            http://reference.data.gov.uk/doc/gregorian-hour/2016-01-01T10
            http://reference.data.gov.uk/doc/gregorian-minute/2016-01-01T10:15
            http://reference.data.gov.uk/doc/gregorian-second/2016-01-01T10:15:59
            http://reference.data.gov.uk/doc/gregorian-week/2016-W51
            '''
        for_each_url(urls, url_resolves)
        url_redirect_is(
            'http://reference.data.gov.uk/id/government-year/2010-2011',
            'http://reference.data.gov.uk/doc/government-year/2010-2011')
        urls_dont_redirect = '''
            http://reference.data.gov.uk/doc/gregorian-interval.nt
            http://reference.data.gov.uk/doc/quarter/2006-Q1
            http://reference.data.gov.uk/doc/quarter/2006-Q1.rdf
            http://reference.data.gov.uk/doc/quarter/2006-Q1.ttl
            http://reference.data.gov.uk/doc/quarter/2006-Q1.n3
            http://reference.data.gov.uk/doc/quarter/2006-Q1.nt
            http://reference.data.gov.uk/doc/quarter/2006-Q1.json
            '''
        for_each_url(urls_dont_redirect, url_doesnt_redirect)
        url_redirect_is(
            'http://reference.data.gov.uk/id/government-year',
            'http://reference.data.gov.uk/doc/government-year',
            )
        url_redirect_is(
            'http://reference.data.gov.uk/id/government-half',
            'http://reference.data.gov.uk/doc/government-half',
            )
        url_redirect_is(
            'http://reference.data.gov.uk/id/government-quarter',
            'http://reference.data.gov.uk/doc/government-quarter',
            )
        url_redirect_is(
            'http://reference.data.gov.uk/id/government-week',
            'http://reference.data.gov.uk/doc/government-week',
            )

class TestGovernmentOntology(unittest.TestCase):

    def test_vocabulary(self):
        url = 'http://reference.data.gov.uk/def/central-government'
        url_resolves(url)
        url_doesnt_redirect(url)

    def test_vocabulary(self):
        url = 'http://reference.data.gov.uk/def/central-government.ttl'
        url_resolves(url)
        url_doesnt_redirect(url)