'''Makes corrections to uploads_report_raw.csv that have been manually
determined. Also determines the filenames to download the XLS and CSV as.'''

import unicodecsv

from uploads_scrape import munge_org, munge_xls_path


should_not_be_published = (
    '/data/bl/2011-09-30/British-Library-Staff-and-Salary-Data---November-2011.xls',
    '/data/hmrc/2011-09-30/300911-HMRC-Organogram-final.xls',

    )
should_be_published = (
    '/data/education/2012-03-31/310312-DfE-Organogram-ver2.xls',
    '/data/nhs/2013-09-30/300913-NHSEngland-Organogram-ver4.xls',
    '/data/cqc/2014-03-31/template.xls',
    '/data/ofsted/2014-03-31/Government-staff-and-salary-data-blank-June-2014.xls',
    '/data/justice/2015-09-30/September-SCS-Structure-and-Pay-Disclosure-Publicationxls.xls',
    '/data/cabinet-office/2014-03-31/Upload---270614-FINAL.xls',
    )
ignore_duplicates = (
    '/data/forestry/2012-03-31/300912-FC-ORGANOGRAM.xls', # wrong date, and is duplicate
    '/data/dfid/2013-03-31/organoggram-staff-salary-transparency-Sept-2012.xls', # wrong date
    '/data/hfea/2013-03-31/2013-09-30-Disclosure-Information--Seni~taff-Payscales-as-at-30-September-2013-for-Cabinet-~-Final.xls', # wrong date
    '/data/cefas/2014-09-30/300914_cefas_organogram.xls', # another version comes a week later, so ignore this one
    '/data/bl/2015-09-30/British-Library-Staff-and-Salary-Data---September-2015.xls',
 # another version comes a day later, so ignore this one
    '/data/chre/2011-09-30/111128-staff-organogram-spreadsheet.xls', # another version comes a few minutes later, so ignore this one
    '/data/dft/2015-09-30/300915-MCA-Organogram-ver-1.xls', # file is corrupt
    '/data/equalityhumanrights/2011-09-30/Final_20110930_21.11.xls', # replaced 3 mins later
    '/data/homeoffice/2012-09-30/300912-GEO.xls', # this period Home Office is a merge of its own organogram and this one, so we just take the combined one from the triplestore
    )
department_corrections = {
    '/data/dft/2015-09-30/300915-MCA-Organogram-ver-1.xls':'Maritime and Coastguard Agency',
    '/data/cabinet-office/2011-09-30/Independent-Office-staff-and-salary-data-FINAL-TEMPLATE.xls': 'Independent Offices',
    '/data/cabinet-office/2011-09-30/BCE-staff-and-salary-data-FINAL-TEMPLATE-v2.xls': 'Boundary Commission for England',
    }
version_corrections = {
    '/data/nmsi/2015-03-31/300915-SMG-Organogram-Data-v1.xls': '30/09/2015',
    '/data/dstl/2015-03-31/20150930-Final_ORGANOGRAM.xls': '30/09/2015',
}


def main():
    correct_uploads('uploads_report_raw.csv', 'uploads_report.csv')
    correct_uploads('uploads_report_raw_with_private.csv',
                    'uploads_report_with_private.csv')


def correct_uploads(in_filename, out_filename):
    assert in_filename != out_filename
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
        rows = []
        written_identities = dict()
        for row in csv_reader:

            # correct the 2011 states according to what is found in the
            # triplestore - they should all say they are published
            if row['version'] == '30/09/2011' and \
                    row['xls_path'] not in should_not_be_published:
                row['state'] = 'published'

            # correct some states that appear to be published in the
            # triplestore, but not on the uploads page (maybe they were changed
            # back on the uploads page but the triplestore didn't update?)
            if row['xls_path'] in should_be_published:
                row['state'] = 'published'

            # Corrections for duplicates etc
            if row['xls_path'] in ignore_duplicates:
                continue

            # Corrections
            if row['xls_path'] in department_corrections:
                row['org_name'] = department_corrections[row['xls_path']]
            if row['xls_path'] in version_corrections:
                row['version'] = version_corrections[row['xls_path']]

            # Select filenames for downloads
            filename_base = '{org}__{date}__{xls_path}'.format(
                org=munge_org(row['org_name']),
                date=row['version'].replace('/', '-'),
                xls_path=munge_xls_path(row['xls_path']))

            row['xls-filename'] = filename_base + '.xls'
            row['junior-csv-filename'] = filename_base + '-junior.csv'
            row['senior-csv-filename'] = filename_base + '-senior.csv'

            # duplicates check
            if row['state'] == 'published':
                identity = row_identity(row)
                if identity in written_identities:
                    if row['org_name'] == 'Ministry of Defence':
                        # we deal with MOD separately
                        pass
                    else:
                        print 'WARNING: duplicate row: %r - %r same as %r' % \
                            (repr(identity).encode('latin7', 'replace'),
                             row['xls_path'],
                             written_identities[identity]['xls_path'])
                else:
                    written_identities[identity] = row

            rows.append(row)

    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = unicodecsv.DictWriter(
            csv_write_file,
            fieldnames=csv_reader.fieldnames +
            ['xls-filename', 'junior-csv-filename', 'senior-csv-filename'],
            encoding='utf8')
        csv_writer.writeheader()
        for row in rows:
            csv_writer.writerow(row)
    print 'Written', out_filename


def row_identity(row_dict):
    return (row_dict['version'],
            row_dict['org_name'])

if __name__ == '__main__':
    main()
