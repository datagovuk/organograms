'''Scrapes TSO organogram upload page to get info about what's published and
can download the XLS and CSV files.
'''
import argparse
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

args = None


class ReportCsv(object):
    def __init__(self):
        self.out_filename = 'uploads_report.csv' if not \
            args.include_private_info else 'uploads_report_with_private.csv'

        self.csv_file = open(self.out_filename, 'wb')
        self.csv_writer = csv.writer(self.csv_file, dialect='excel')
        self.row_headings = [
            'version',
            'org_name', 'xls_path', 'upload_date', 'state',
            'action_datetime', 'xls-filename',
            'junior-csv-filename', 'senior-csv-filename'
            ]
        if args.include_private_info:
            self.row_headings = ['submitter_email'] + self.row_headings
        self.csv_writer.writerow(self.row_headings)
        self.rows_written = 0

    def save_to_csv(self, row_dict):
        row = []
        for heading in self.row_headings:
            cell = row_dict.get(heading, '')
            if heading in ('upload_date', 'action_datetime') and cell:
                cell = cell.isoformat()
            row.append(cell)
        #print row
        self.csv_writer.writerow(row)
        self.rows_written += 1


def main(xls_folder, csv_folder):
    username = os.environ['SCRAPE_USERNAME']
    password = os.environ['SCRAPE_PASSWORD']
    email = os.environ['SCRAPE_EMAIL']
    report = ReportCsv()
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
            if args.include_private_info:
                try:
                    submitter_email = row.xpath('td[@class="submitter"]/a/text()')[0].strip()
                except IndexError:
                    # 30/09/2013 JNCC submitter is not an email address
                    submitter_email = row.xpath('td[@class="submitter"]/a/text()')
            xls_path = row.xpath('td[@class="filename"]/a/@href')[0]
            upload_date = row.xpath('td[@class="modified"]/text()')[0].strip()
            upload_date = datetime.datetime.strptime(upload_date, '%d/%m/%Y')
            action_value = row.xpath('td[@class="sign-off"]//input[@name="action"]/@value')[0]
            state = states_by_action[action_value]

            # correct the 2011 states according to what is found in the
            # triplestore - they should all say they are published
            if date == '30/09/2011' and \
                    xls_path not in (
                        '/data/geo/2011-09-30/Copy-of-Final_20110930_08.11.xls',
                        '/data/bl/2011-09-30/British-Library-Staff-and-Salary-Data---November-2011.xls',
                        '/data/hmrc/2011-09-30/300911-HMRC-Organogram-final.xls',
                        ):

                state = 'published'
            # correct some states that appear to be published in the
            # triplestore, but not on the uploads page (maybe they were changed
            # back on the uploads page but the triplestore didn't update?)
            if xls_path in (
                '/data/education/2012-03-31/310312-DfE-Organogram-ver2.xls',
                '/data/nhs/2013-09-30/300913-NHSEngland-Organogram-ver4.xls',
                '/data/cqc/2014-03-31/template.xls',
                '/data/ofsted/2014-03-31/Government-staff-and-salary-data-blank-June-2014.xls',
                '/data/justice/2015-09-30/September-SCS-Structure-and-Pay-Disclosure-Publicationxls.xls',
                '/data/cabinet-office/2014-03-31/Upload---270614-FINAL.xls',
                ):
                state = 'published'

            row_info_by_xls_path[xls_path] = {
                'version': date,
                'org_name': org,
                'submitter_email': submitter_email if args.include_private_info else None,
                'xls_path': xls_path,
                'upload_date': upload_date,
                'state': state,
                }

        # Download pane gives the CSV downloads
        for row in tree.xpath('//div[@id="download"]//table/tr'):
            filenames = row.xpath('td[@class="filename"]/a/@href')
            xls_path, csv_junior_path, csv_senior_path = filenames
            row_info = row_info_by_xls_path[xls_path]
            assert 'action_datetime' not in row_info, \
                'XLS appears twice in download: ' + xls_path
            date_str = row.xpath('td[@class="modified"]/text()')[0]
            row_info['action_datetime'] = \
                datetime.datetime.strptime(date_str, '%d %b %Y %H:%M')

            # Corrections for duplicates etc
            if xls_path == '/data/forestry/2012-03-31/300912-FC-ORGANOGRAM.xls' and date == '31/03/2012':
                # wrong date, and is duplicate
                continue
            if xls_path == '/data/dfid/2013-03-31/organoggram-staff-salary-transparency-Sept-2012.xls' and date == '31/03/2013':
                # wrong date
                row_info['version'] = '30/09/2012'
            if xls_path == '/data/hfea/2013-03-31/2013-09-30-Disclosure-Information--Seni~taff-Payscales-as-at-30-September-2013-for-Cabinet-~-Final.xls' and date == '31/03/2013':
                # wrong date
                row_info['version'] = '30/09/2013'
            if xls_path == '/data/cefas/2014-09-30/300914_cefas_organogram.xls':
                # another version comes a week later, so ignore this one
                continue
            if xls_path == '/data/bl/2015-09-30/British-Library-Staff-and-Salary-Data---September-2015.xls':
                # another version comes a day later, so ignore this one
                continue
            if xls_path == '/data/cabinet-office/2011-09-30/Independent-Office-staff-and-salary-data-FINAL-TEMPLATE.xls':
                row_info['org_name'] = 'Independent Offices'
            if xls_path == '/data/cabinet-office/2011-09-30/BCE-staff-and-salary-data-FINAL-TEMPLATE-v2.xls':
                row_info['org_name'] = 'Boundary Commission for England'
            if xls_path == '/data/chre/2011-09-30/111128-staff-organogram-spreadsheet.xls':
                # another version comes a few minutes later, so ignore this one
                continue
            if xls_path == '/data/dstl/2015-03-31/20150930-Final_ORGANOGRAM.xls':
                row_info['version'] = '30/09/2015'

            filename_base = '{org}-{date}'.format(
                org=munge_org(row_info['org_name']),
                date=row_info['version'].replace('/', '-'))

            if row_info['state'] == 'published':
                row_info['xls-filename'] = filename_base + '.xls'
                row_info['junior-csv-filename'] = filename_base + '-junior.csv'
                row_info['senior-csv-filename'] = filename_base + '-senior.csv'
                if args.download:
                    download(xls_path, xls_folder, row_info['xls-filename'])
                    download(csv_junior_path, csv_folder,
                             row_info['junior-csv-filename'])
                    download(csv_senior_path, csv_folder,
                             row_info['senior-csv-filename'])



            report.save_to_csv(row_info)

        # check all rows in the preview pane have been found in the download
        # pane
        for row_info in row_info_by_xls_path.values():
            if 'action_datetime' not in row_info:
                assert 0, row_info

        print 'Wrote %s rows' % report.rows_written
        report.rows_written = 0
        print 'Written %s' % report.out_filename

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
    if os.path.exists(filepath):
        print 'Skipping downloading existing file %s %s' % (url, filepath)
        return
    print 'Requesting: {url} {filename}'.format(url=url, filename=filename)
    response = requests.get(url)
    if not response.ok:
        print 'ERROR downloading %s' % url
        print response, response.reason
        if filename.endswith('.xls'):
            # actually we're only really concerned with xls files, not csv
            import pdb; pdb.set_trace()
        return
    with open(filepath, 'wb') as f:
        f.write(response.content)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('xls_folder')
    parser.add_argument('csv_folder')
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--include-private-info', action='store_true')
    args = parser.parse_args()
    xls_folder = args.xls_folder
    csv_folder = args.csv_folder
    for folder in (xls_folder, csv_folder):
        if not os.path.isdir(folder):
            raise argparse.ArgumentTypeError(
                'Error: Not an existing directory: %s' % folder)
    main(xls_folder, csv_folder)
