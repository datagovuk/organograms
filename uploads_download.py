'''Makes corrections to uploads_report_raw.csv that have been manually
determined.'''

import unicodecsv
import argparse
import os

import requests_cache
import requests

requests_cached = requests_cache.CachedSession('.scrape_cache')  # never expires


DOWNLOAD_URL = 'http://organogram.data.gov.uk{path}'


def main(xls_folder, csv_folder):
    in_filename = 'uploads_report.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
        for row in csv_reader:

            download(row['xls_path'], xls_folder, row['xls-filename'])
            download(row['csv_junior_path'], csv_folder,
                     row['junior-csv-filename'])
            download(row['csv_senior_path'], csv_folder,
                     row['senior-csv-filename'])

    print 'Done'


def download(url_path, folder, filename):
    # this long dash gets encoded weirdly by TSO system - do it manually
    url_path = url_path.replace(u'\u2013', '%c3%a2%e2%82%ac%e2%80%9c')
    try:
        url = DOWNLOAD_URL.format(path=url_path)
    except:
        import pdb; pdb.set_trace()
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
