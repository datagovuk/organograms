'''Scrapes TSO organogram upload page to get info about what's published and
can download the XLS and CSV files.
'''
import argparse
import os
import re
import datetime
import unicodecsv

from lxml import html
import requests_cache
import requests

requests_cached = requests_cache.CachedSession('.scrape_cache')  # never expires

INDEX_URL = 'http://organogram.data.gov.uk/?email={email}&filename=&date={date}&action=Download'

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
    '31/03/2016',
    #'30/09/2016',
    )

VERSIONS = [
    '2011-03-31',
    '2011-09-30',
    '2012-03-31',
    '2012-09-30',
    '2013-03-31',
    '2013-09-30',
    '2014-03-31',
    '2014-09-30',
    '2015-03-31',
    '2015-09-30',
    '2016-03-31',
    ]

states_by_action = {
    'sign-off': 'uploaded',
    'publish': 'signed off',
    'published': 'published',
    }

args = None


class ReportCsv(object):
    def __init__(self):
        self.out_filename = 'uploads_report_raw.csv' if not \
            args.include_private_info else 'uploads_report_raw_with_private.csv'

        self.csv_file = open(self.out_filename, 'wb')
        self.csv_writer = unicodecsv.writer(self.csv_file, dialect='excel',
                                            encoding='utf8')
        self.row_headings = [
            'version',
            'org_name', 'xls_path', 'upload_date', 'state',
            'action_datetime', 'csv_junior_path', 'csv_senior_path',
            #'junior-csv-filename', 'senior-csv-filename',
            ]
        if args.include_private_info:
            self.row_headings = ['submitter_email'] + self.row_headings
        self.csv_writer.writerow(self.row_headings)
        self.rows_written = 0

        self._written_identities = dict()

    def _identity(self, row_dict):
        return (row_dict['version'],
                row_dict['org_name'])

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

        # duplicates check
        if row_dict['state'] == 'published':
            identity = self._identity(row_dict)
            if identity in self._written_identities:
                if row_dict['org_name'] == 'Ministry of Defence':
                    # we have dealt with MOD
                    pass
                else:
                    print 'WARNING: duplicate row: %r - %r same as %r' % (repr(identity).encode('latin7', 'replace'), row_dict['xls_path'], self._written_identities[identity]['xls_path'])
            else:
                self._written_identities[identity] = row_dict


def main():
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
            row_info['csv_junior_path'] = csv_junior_path
            row_info['csv_senior_path'] = csv_senior_path
            assert 'action_datetime' not in row_info, \
                'XLS appears twice in download: ' + xls_path
            date_str = row.xpath('td[@class="modified"]/text()')[0]
            row_info['action_datetime'] = \
                datetime.datetime.strptime(date_str, '%d %b %Y %H:%M')

            report.save_to_csv(row_info)

        # check all rows in the preview pane have been found in the download
        # pane
        for row_info in row_info_by_xls_path.values():
            if 'action_datetime' not in row_info:
                assert 0, row_info

        print 'Wrote %s rows' % report.rows_written
        report.rows_written = 0
        print 'Written %s' % report.out_filename

def munge_org(name, separation_char='-'):
    '''Return the org name, suitable for a filename'''
    name = name.lower()
    # separators become dash/underscore
    name = re.sub('[ .:/&]', separation_char, name)
    # take out not-allowed characters
    name = re.sub('[^a-z0-9-_]', '', name)
    # remove doubles
    name = re.sub('-+', '-', name)
    name = re.sub('_+', '_', name)
    return name

def munge_xls_path(name):
    '''Make the XLS path bits suitable to be part of the saved filename,
    getting rid of the /data/ and /<date>/ bits as they are in the path.
    /data/acas/2011-09-30/ACAS-SEPT-2011-TRANSPERANCYa.xls
    ->
    acas__ACAS-SEPT-2011-TRANSPERANCYa
    '''
    parts = name.split('/')
    assert len(parts) == 5, name
    name = '%s__%s' % (parts[2], parts[4])
    name = '.'.join(name.split('.')[:-1])
    # separators become underscores
    name = re.sub('[ .:/&]', '-', name)
    # take out not-allowed characters
    name = re.sub('[^A-Za-z0-9-_]', '', name)
    # remove doubles
    name = re.sub('-+', '-', name)
    name = re.sub('_+', '_', name)
    return name


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--download', action='store_true')
    parser.add_argument('--include-private-info', action='store_true')
    args = parser.parse_args()
    main()
