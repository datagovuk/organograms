'''Scrapes organogram data

TODO:
* only scrape published data
* write an index of the scraped data to aid testing comparison of the old and generated data
'''

import sys
import os
import re
import datetime
import csv

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

states_by_action = {
    'sign-off': 'uploaded',
    'publish': 'signed off',
    'published': 'published',
    }

csv_file = open('report.csv', 'wb')
csv_writer = csv.writer(csv_file, dialect='excel')
row_headings = [
   'version',
   'org_name', 'submitter_email', 'xls_path', 'upload_date', 'state',
   'action_datetime', 'xls-filename', 'junior-csv-filename', 'senior-csv-filename'
   ]
csv_writer.writerow(row_headings)
rows_written = 0
def save_to_csv(row_dict):
    row = []
    for heading in row_headings:
        cell = row_dict.get(heading, '')
        if heading in ('upload_date', 'action_datetime'):
            cell = cell.isoformat()
        row.append(cell)
    #print row
    csv_writer.writerow(row)
    global rows_written
    rows_written += 1


def main(xls_folder, csv_folder):
    username = os.environ['SCRAPE_USERNAME']
    password = os.environ['SCRAPE_PASSWORD']
    email = os.environ['SCRAPE_EMAIL']
    for date in dates:
        url = INDEX_URL.format(email=email.replace('@', '%40'),
                               date=date.replace('/', '%2F'))
        print 'Date: ', date, ' URL: ', url
        page = requests_cached.get(url, auth=(username, password))
        tree = html.fromstring(page.content)
        row_info_by_xls_path = {}
        # Preview pane gives the department and XLS downloads
        # and state
        for row in tree.xpath('//div[@id="preview"]//table/tr')[1:]:
            org = row.xpath('td[@class="dept"]/text()')[0]
            submitter_email = row.xpath('td[@class="submitter"]/a/text()')[0].strip()
            xls_path = row.xpath('td[@class="filename"]/a/@href')[0]
            upload_date = row.xpath('td[@class="modified"]/text()')[0].strip()
            upload_date = datetime.datetime.strptime(upload_date, '%d/%m/%Y')
            action_value = row.xpath('td[@class="sign-off"]//input[@name="action"]/@value')[0]
            state = states_by_action[action_value]
            row_info_by_xls_path[xls_path] = {
                'version': date,
                'org_name': org,
                'submitter_email': submitter_email,
                'xls_path': xls_path,
                'upload_date': upload_date,
                'state': state,
                }

        # Download pane gives the CSV downloads
        for row in tree.xpath('//div[@id="download"]//table/tr')[1:]:
            row_info = row_info_by_xls_path[xls_path]
            date_str = row.xpath('td[@class="modified"]/text()')[0]
            row_info['action_datetime'] = \
                datetime.datetime.strptime(date_str, '%d %b %Y %H:%M')
            filenames = row.xpath('td[@class="filename"]/a/@href')
            xls_path, csv_junior_path, csv_senior_path = filenames
            org = row_info['org_name']

            filename_base = '{org}-{date}'.format(
                org=munge_org(org),
                date=date.replace('/', '-'))

            save_to_csv(row_info)

            if state == 'published':
                row_info['xls-filename'] = filename_base + '.xls'
                row_info['junior-csv-filename'] = filename_base + '-junior.csv'
                row_info['senior-csv-filename'] = filename_base + '-senior.csv'
                download(xls_path, xls_folder, row_info['xls-filename'])
                download(csv_junior_path, csv_folder,
                        row_info['junior-csv-filename'])
                download(csv_senior_path, csv_folder,
                        row_info['senior-csv-filename'])

        # save any rows not found in the download pane
        for row in row_info:
            if 'action_datetime' not in row:
                save_to_csv(row_info)
        global rows_written
        print 'Wrote %s rows' % rows_written; rows_written = 0


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
