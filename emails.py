'''Tool for dealing with email addresses of publishers
'''
import argparse
import unicodecsv
import datetime
import os
import json

import ckanapi

from running_stats import Stats
from departments_tidy import DguOrgs, canonize, Aliases


def get_ckan(ckan_domain_or_ini):
    if '.ini' in ckan_domain_or_ini:
        ckan = ckanapi.LocalCKAN(ckan_domain_or_ini)
    else:
        import ConfigParser
        domain = ckan_domain_or_ini
        config = ConfigParser.RawConfigParser()
        config.read('apikeys.cfg')
        apikey = config.get(domain, 'apikey')
        try:
            url = config.get(domain, 'url')
        except ConfigParser.NoOptionError:
            url = 'https://%s' % domain
        ckan = ckanapi.RemoteCKAN(url, apikey=apikey)
    return ckan

def get_uploads():
    with open('uploads_report_raw_with_private.csv', 'rb') as csv_read_file:
        csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
        uploads = [row for row in csv_reader]
    return uploads

def dgu_account(args):
    ckan = get_ckan(args.ckan)
    uploads = get_uploads()

    stats = Stats()
    publishers = {}  # by email.lower()
    for upload in uploads:
        version = datetime.datetime.strptime(upload['version'], '%d/%m/%Y')
        if version < datetime.datetime(2015, 1, 1):
            #stats.add('Ignore - before 2015',
            #          '%s %s' % (upload['version'], upload['submitter_email']))
            continue
        if '@' not in upload['submitter_email']:
            stats.add('Ignore - bad email address', upload['submitter_email'])
            continue
        if upload['submitter_email'].lower() not in publishers:
            publishers[upload['submitter_email'].lower()] = []
            stats.add('Added', upload['submitter_email'])
        else:
            stats.add('Appended', upload['submitter_email'])
        publishers[upload['submitter_email'].lower()].append(
            dict(email=upload['submitter_email'],
                 org_name=upload['org_name'],
                 version=upload['version'])
            )

    print 'Email addresses:'
    print stats

    cache_filename = '.users.%s.cache' % (args.ckan.replace(':', '-'))
    if os.path.exists(cache_filename):
        print 'Getting users from %s' % cache_filename
        with open(cache_filename, 'rb') as f:
            users_str = f.read()
        users = json.loads(users_str)
    else:
        print 'Getting users from %s' % args.ckan
        # NB this doesn't work remotely because varnish times out,
        # so run from prod3 itself against 8080 from ~/organograms
        users = ckan.action.user_list()
        print 'Saving users to %s' % cache_filename
        users_str = json.dumps(users)
        with open(cache_filename, 'wb') as f:
            f.write(users_str)
    print '%s users' % len(users)
    users_by_email = dict([(user['email'], user) for user in users])

    def get_user(email_variants):
        for email_variant in email_variants:
            if email_variant in users_by_email:
                return users_by_email[email_variant]

    stats = Stats()
    for email_lower in publishers:
        # see if they are a user on data.gov.uk
        email_variants = set((upload['email']
                              for upload in publishers[email_lower]))
        user = get_user(email_variants)
        emails_str = '/'.join(email_variants)
        if not user:
            print stats.add('Not registered', emails_str)
            continue
        # assume has confirmed email

        # find the organization
        org_names_raw = set((upload['org_name']
                             for upload in publishers[email_lower]))
        orgs = []
        for org_name_raw in org_names_raw:
            title = canonize(org_name_raw)
            match = DguOrgs.by_canonized_title().get(title) or Aliases.get_from_canonized(title)
            assert match, 'No match: %s' % org_name_raw
            if isinstance(match, basestring):
                match = DguOrgs.by_title()[match]
            if match not in orgs:
                orgs.append(match)

        # see if this user is an editor/admin for the organization
        for org in orgs:
            editors_and_admins = (user['name'] for user in org['users'])
            if user['name'] in editors_and_admins:
                print stats.add('Already an editor/admin',
                                '%s %s' %
                                (emails_str, org['title']))
            else:
                admins = (user['name'] for user in org['users']
                          if user['capacity'] == 'admin')
                if admins:
                    print stats.add('Need to get permission. Admin exists',
                                    '%s %s %s' %
                                    (emails_str, org['title'],
                                     ', '.join('"%s"' % a for a in admins)))
                else:
                    print stats.add('Need to get permission. No admin',
                                    '%s %s' %
                                    (emails_str, org['title']))

    def extract_email(stat):
        emails = stat.split(' ')[0] # the first word
        email = emails.split('/')[0] # ignore variants
        return email

    print '\nNot registered:'
    print ', '.join(stats['Not registered'])
    print '\nAlready an editor/admin:'
    print ', '.join([extract_email(email_and_org)
                     for email_and_org in stats['Already an editor/admin']])
    print '\nNeed to get permission. Admin exists:'
    print ', '.join([extract_email(email_and_org)
                     for email_and_org in stats['Need to get permission. Admin exists']])

    print '\nPermissions'
    print stats


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(help='sub-command help')

    parser_dgu = subparsers.add_parser('dgu-account', help='Checks status of DGU account')
    parser_dgu.add_argument('ckan', metavar='DOMAIN_OR_CKAN_INI_FILEPATH',
                            help='domain or ckan.ini filepath')
    parser_dgu.set_defaults(func=dgu_account)

    args = parser.parse_args()
    args.func(args)