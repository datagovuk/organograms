'''Scrapes organogram data

TODO:
* only scrape published data
* write an index of the scraped data to aid testing comparison of the old and generated data
'''

import sys
import os
import re

from lxml import html
import requests_cache
import requests

requests_cached = requests_cache.CachedSession('.scrape_cache')  # never expires

INDEX_URL = 'http://organogram.data.gov.uk/?email={email}&filename=&date={date}&action=Download'
DOWNLOAD_URL = 'http://organogram.data.gov.uk{path}'

dates = (
    '30/09/2011',
    '31/03/2012',
    '30/09/2012',
    '31/03/2013',
    '30/09/2013',
    '31/03/2014',
    '30/09/2014',
    '31/03/2015',
    '30/09/2015',
    #'31/03/2016',
    #'30/09/2016',
    )


def main(xls_folder, csv_folder):
    username = os.environ['SCRAPE_USERNAME']
    password = os.environ['SCRAPE_PASSWORD']
    email = os.environ['SCRAPE_EMAIL']
    for date in dates:
        url = INDEX_URL.format(email=email.replace('@', '%40'),
                               date=date.replace('/', '%2F'))
        page = requests_cached.get(url, auth=(username, password))
        tree = html.fromstring(page.content)
        org_by_xls_path = {}
        # Preview pane gives the department and XLS downloads
        for row in tree.xpath('//div[@id="preview"]//table/tr')[1:]:
            org = row.xpath('td[@class="dept"]/text()')[0]
            xls_path = row.xpath('td[@class="filename"]/a/@href')[0]
            org_by_xls_path[xls_path] = org
        # Download pane gives the CSV downloads
        for row in tree.xpath('//div[@id="download"]//table/tr')[1:]:
            filenames = row.xpath('td[@class="filename"]/a/@href')
            xls_path, csv_junior_path, csv_senior_path = filenames
            org = org_by_xls_path[xls_path]

            filename_base = '{org}-{date}'.format(
                org=munge_org(org),
                date=date.replace('/', '-'))
            download(xls_path, xls_folder, filename_base + '.xls')
            download(csv_junior_path, csv_folder,
                     filename_base + '-junior.csv')
            download(csv_senior_path, csv_folder,
                     filename_base + '-senior.csv')


def munge_org(name):
    '''Return the org name, suitable for a filename'''
    name = name.lower()
    # separators become underscores
    name = re.sub('[ .:/&]', '_', name)
    # take out not-allowed characters
    name = re.sub('[^a-z0-9-_]', '', name)
    # remove doubles
    name = re.sub('-+', '-', name)
    name = re.sub('_+', '_', name)
    return name


def download(url_path, folder, filename):
    url = DOWNLOAD_URL.format(path=url_path)
    filepath = os.path.join(folder, filename)
    print 'Requesting: {url} {filename}'.format(url=url, filename=filename)
    response = requests.get(url)
    with open(filepath, 'wb') as f:
        f.write(response.content)


def usage():
    print 'Usage: python %s data/xls data/csv' % sys.argv[0]
    sys.exit(1)


if __name__ == '__main__':
    args = sys.argv[1:]
    if len(args) != 2:
        print 'Error: Wrong number of args'
        usage()
    xls_folder, csv_folder = args
    for folder in (xls_folder, csv_folder):
        if not os.path.isdir(folder):
            print "Error: Not a directory: %s" % folder
            usage()
    main(xls_folder, csv_folder)
