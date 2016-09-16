'''For some organogram data, reconciles the list of departments and public
bodies against those on data.gov.uk and saves the tidied data.
'''
import argparse
import re
import csv
import unicodecsv
from collections import defaultdict
import os.path
import datetime
import pickle
import sys

import requests_cache
# pip install fuzzywuzzy
# pip install python-levenshtein
import fuzzywuzzy.process
import fuzzywuzzy.fuzz
# pip install progress
from progress.bar import Bar
import ckanapi

one_day = 60 * 60 * 24
one_month = one_day * 30
requests_cache.install_cache('.dgu_departments.cache', expire_after=one_month)


class DguOrgs(object):
    _instance = None
    pickle_filename = '.dgu_departments_pickle.cache'

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        # NB Not using all_fields as it doesn't include extras, like category
        self._by_name = {}
        self._by_title = {}
        self._by_canonized_title = {}
        self.ckanapi = ckanapi.RemoteCKAN('https://data.gov.uk',
                                          get_only=True)
        self.ckanapi_uncached = ckanapi.RemoteCKAN('https://data.gov.uk',
                                          get_only=False)
        # try cached pickle of the departments
        if os.path.exists(self.pickle_filename) and \
                (datetime.datetime.fromtimestamp(os.stat(self.pickle_filename).st_mtime) >
                 (datetime.datetime.now() - datetime.timedelta(days=1))):
            print 'Reading DGU departments from pickle cache'
            with open(self.pickle_filename) as f:
                orgs = pickle.load(f)
        else:
            org_names = self.ckanapi_uncached.action.organization_list()
            orgs = []
            for org_name in Bar('Reading DGU organizations').iter(org_names):
                orgs.append(self.ckanapi.action.organization_show(id=org_name))
            self.save(orgs)
        for org in orgs:
            self._record_org(org)

    def _record_org(self, org):
        # convert the extras into a dict
        org['extras'] = dict((extra['key'], extra['value'])
                             for extra in org['extras'])
        self._by_name[org['name']] = org
        self._by_title[org['title']] = org
        self._by_canonized_title[canonize(org['title'])] = org

    def notify_of_new_org(self, org_name):
        '''Call this to let this know when a new org has been created on dgu'''
        with open(self.pickle_filename) as f:
            orgs = pickle.load(f)
        # Do post to avoid the cache
        ckanapi_ = ckanapi.RemoteCKAN('https://data.gov.uk',
                                      get_only=False)
        org = ckanapi_.action.organization_show(id=org_name)
        orgs.append(org)
        self.save(orgs)
        self._record_org(org)
        return org['title']

    def save(self, orgs):
        with open(self.pickle_filename, 'wb') as f:
            pickle.dump(orgs, f)

    @classmethod
    def by_name(cls):
        return cls.instance()._by_name

    @classmethod
    def by_title(cls):
        return cls.instance()._by_title

    @classmethod
    def by_canonized_title(cls):
        return cls.instance()._by_canonized_title

dept_char_filter_regex = re.compile('[^a-z0-9 ]')
stop_words = set(('and', 'to', 'of', 'for', 'the'))


def canonize(title):
    '''Returns a slightly simplified version of a public body name, for ironing
    out trivial differences when matching.'''
    title = title.lower().strip()
    if not title.startswith('http'):
        title = dept_char_filter_regex.sub('', title)
        title = ' '.join(w for w in title.split() if w not in stop_words)
    return title


class Aliases(object):
    _instance = None
    filename = 'dgu_department_aliases.csv'

    def __init__(self):
        self.aliases = {}
        self.canonized_aliases = {}
        with open(self.filename, 'rb') as csv_read_file:
            csv_reader = csv.DictReader(csv_read_file)
            for row in csv_reader:
                self.aliases[row['alias']] = row['name']
                self.canonized_aliases[canonize(row['alias'])] = row['name']

    @classmethod
    def instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def get(cls, key, default=None):
        return cls.instance().canonized_aliases.get(canonize(key), default)

    @classmethod
    def get_from_canonized(cls, canonized_key, default=None):
        return cls.instance().canonized_aliases.get(canonized_key, default)

    def add(self, alias, name):
        c_alias = canonize(alias)
        # shouldn't really have to do any checks here, but just in case
        if c_alias == canonize(name):
            print 'Discarding alias that is the same canonized: "%s"="%s"' % \
                (alias, name)
            return
        self.aliases[alias] = name
        self.canonized_aliases[c_alias] = name

    def save(self):
        with open(self.filename, 'wb') as csv_file:
            csv_writer = csv.writer(csv_file)
            csv_writer.writerow(['alias', 'name'])
            for alias, name in sorted(self.aliases.iteritems(), key=lambda x: x[0]):
                print '%s\n%s\n' % (canonize(alias), canonize(name))
                csv_writer.writerow([alias, name])
        print 'Written %s' % self.filename

    def get_or_reconcile(self, *names):
        '''Look for a match of any of the names. If any are not already
        associated, then add aliases for them.
        Returns the matching title, or None if the user bailed.
        '''
        matches = defaultdict(list)
        for name in names:
            matches[self.get(name)].append(name)
        matching_names = set(matches) - set((None,))
        if len(matching_names) > 1:
            print 'ERROR: Multiple matches for names %r: %r' % (names, matching_names)
            return
        elif len(matching_names) == 0:
            # ask user and get aliases added
            match = self.reconcile(*names)
        else:
            # 1 match
            match = list(matching_names)[0]
            # Add any missing aliases
            for name in matches.get(None, []):
                self.add(name, match)
        return match

    def reconcile(self, *names):
        '''Ask the user (its assumed that the names aren't in DGU or aliases).
        It adds aliases for all the names supplied.
        Returns the matching title, or None if the user bailed.
        '''
        print '\n>>>>>>>>>>>>>'
        print 'Reconcile: %s' % repr(names)
        print '>>>>>>>>>>>>>'
        suggestions = {}
        if not hasattr(self, 'canonized_dgu_titles'):
            # aliases change
            dgu_titles = DguOrgs.by_title().keys()
            self.canonized_dgu_titles = (canonize(t) for t in dgu_titles)
        canonized_alias_titles = self.canonized_aliases.keys()
        score_threshold = 50
        scorer = fuzzywuzzy.fuzz.WRatio
        for name in names:
            if name.startswith('http'):
                name = name.split('/')[-1]
            name = canonize(name)
            # similar to fuzzywuzzy.process.extract
            for c_title in self.canonized_dgu_titles:
                score = scorer(name, c_title)
                if score < score_threshold:
                    continue
                title = DguOrgs.by_canonized_title()[c_title]['title']
                suggestions[title] = score
            for c_title in canonized_alias_titles:
                score = scorer(name, c_title)
                if score < score_threshold:
                    continue
                title = self.get_from_canonized(c_title)
                if title in suggestions and suggestions[title] >= score:
                    # that suggestion is already there with a higher score
                    continue
                suggestions[title] = score
        top_suggestions = sorted(suggestions.items(), key=lambda s: -s[1])[:10]
        for i, suggestion_tuple in enumerate(top_suggestions):
            print '%s: %s' % (i+1, suggestion_tuple[0])
        print 'None: ignore for now'
        print '(https://...): new one on DGU'
        print '(custom): Or type another'
        while True:
            response = raw_input('> ').strip()
            try:
                match = top_suggestions[int(response) - 1][0]
                break
            except ValueError:
                pass
            if response.lower() == 'none' or response == '':
                match = None
                return None
            if response.startswith('https://data.gov.uk/publisher'):
                org_name = response.split('/')[-1]
                match = DguOrgs.instance().notify_of_new_org(org_name)
                if not match:
                    print 'Publisher %r not found in DGU' % org_name
                    continue
                break
            if response not in DguOrgs.by_title():
                print 'Not found in DGU'
                continue
            match = response
            break
        # save the reconciliation against the names
        for name in names:
            print 'Adding alias: "%s" "%s"' % (name, match)
            self.add(name, match)
        self.save()
        return match


def match_to_dgu_dept(*synonymous_names):
    '''Given a department/body name (or name and URL) it looks it up in the DGU
    names and aliases and returns the equivalent DguOrg dict. If it is not
    known then it will prompt the user to reconcile it.
    '''
    canonized_names = (canonize(name) for name in synonymous_names)
    for canonized_name in canonized_names:
        match = DguOrgs.by_canonized_title().get(canonized_name)
        if match:
            break
    if not match:
        match = \
            Aliases.instance().get_or_reconcile(*synonymous_names)
        if not match:
            print 'Not matched'
            return None
    if isinstance(match, basestring):
        match = DguOrgs.by_title()[match]
    return match


def tidy_triplestore():
    in_filename = 'triplestore_departments.csv'
    out_filename = 'triplestore_departments_tidied.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        out_depts = {}  # name: dept
        for dept in csv_reader:

            # Bad parent fields
            if dept['uri'] == dept['parent'] or \
                    'reference.data.gov.uk' not in dept['parent']:
                dept['parent'] = None

            # Match to a DGU department
            match = match_to_dgu_dept(dept['uri'], dept['title'])
            if not match:
                continue

            # Fill in info from the matching DguOrg
            name = match['name']
            if name in out_depts:
                out_dept = out_depts[name]
            else:
                out_dept = {'graphs': [], 'uris': [], 'viz_urls': []}
                out_depts[name] = out_dept
            out_dept['name'] = match['name']
            out_dept['title'] = match['title']
            #out_dept['top_level_department'] = match['top_level_department']
            out_dept['graphs'].append(dept['graph'])
            out_dept['uris'].append(dept['uri'])
            out_dept['viz_urls'].append(get_viz_url(dept['uri']))
    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = csv.writer(csv_write_file)
        write_headers = ['name', 'title', 'graphs', 'uris', 'viz_urls'] #, 'top_level_department']
        csv_writer.writerow(write_headers)
        out_depts = sorted(out_depts.values(), key=lambda d: d['name'])
        for out_dept in out_depts:
            out_dept['graphs'] = ' '.join(out_dept['graphs'])
            out_dept['uris'] = ' '.join(out_dept['uris'])
            out_dept['viz_urls'] = ' '.join(set(out_dept['viz_urls']))
            csv_writer.writerow([out_dept[header] for header in write_headers])
    print 'Written', out_filename


def get_viz_url(body_uri):
    ''' Returns a URL for the viz corresponding to the body URI provided.

    e.g. department
    http://reference.data.gov.uk/id/department/co
    http://reference.data.gov.uk/gov-structure/organogram/?dept=co

    e.g. public body
    http://reference.data.gov.uk/id/public-body/boundary-commission
    http://reference.data.gov.uk/gov-structure/organogram/?pubbod=boundary-commission
    '''
    uri_match = re.match('http://reference.data.gov.uk/id/([a-z\-]+)/([a-z\-]+)',
                         body_uri)
    if not uri_match:
        import pdb; pdb.set_trace()
    body_type_longhand, body_slug = uri_match.groups()
    body_type_shorthand = {'department': 'dept',
                           'public-body': 'pubbod'}[body_type_longhand]
    viz_url = 'http://reference.data.gov.uk/gov-structure/organogram/?'\
        '{type_shorthand}={slug}'.format(
            type_shorthand=body_type_shorthand,
            slug=body_slug)
    return viz_url


MOD_SUBPUBS = {
    'Permanent Joint Headquarters': ('pjhq',),
    'Air Command': ('air cmd', 'air command', 'air govt', 'air'),
    'MoD Central Top Level Budget': ('ctlb',),
    'Army Command': ('army', 'land forces',),
    'Defence Infrastructure Organisation': ('dio',),
    'Defence Equipment and Support': ('des', 'de and s'),
    'Navy Command': ('navy command', 'nc', 'navy cmd', 'navy'),
    'Defence Science and Technology Laboratory': ('dstl', 'taz',),
    'Head Office and Corporate Services (MoD)': ('hocs', 'ho and cs'),
    'Joint Forces Command': ('joint forces command', 'jfc'),
    'National Army Museum': ('nam', 'national army museum'),
    'Single Source Regulations Office': ('ssro',),
    }
MOD_SUBPUBS_BY_ABBREV = None


def mod_subpublisher(row):
    '''Changes the row's publisher from MOD to one of MOD's sub-publishers,
    based on the XLS filename.  Because MOD organogram files come split-up.
    '''
    global MOD_SUBPUBS_BY_ABBREV
    if MOD_SUBPUBS_BY_ABBREV is None:
        MOD_SUBPUBS_BY_ABBREV = {}
        for name, abbrev_list in MOD_SUBPUBS.items():
            for abbrev in abbrev_list:
                MOD_SUBPUBS_BY_ABBREV[abbrev] = name

    path = row['xls_path']
    path_words = re.findall('([A-Za-z]+)', path)
    path_words = ' '.join([pt.lower() for pt in path_words])
    all_matching_subpubs = set()

    # whole word match
    for name, abbrev_list in MOD_SUBPUBS.items():
        for abbrev in abbrev_list:
            if re.search(r'\b%s\b' % abbrev, path_words):
                all_matching_subpubs.add(name)

    if len(all_matching_subpubs) == 0:
        # match anywhere
        for name, abbrev_list in MOD_SUBPUBS.items():
            for abbrev in abbrev_list:
                if re.search(r'%s' % abbrev, path_words):
                    all_matching_subpubs.add(name)

    #for path_token in path_words:
    #    matching_subpub = MOD_SUBPUBS_BY_ABBREV.get(path_token)
    #    if matching_subpub:
    #        all_matching_subpubs.add(matching_subpub)
    if all_matching_subpubs == set(['National Army Museum', 'Army Command']):
        all_matching_subpubs = set(['National Army Museum'])
    if len(all_matching_subpubs) == 0:
        print 'ERROR: No matching MoD sub-pub for: %s' % path
        print path_words
        sys.exit(0)
    elif len(all_matching_subpubs) > 1:
        print 'ERROR: Multiple matching MoD sub-pubs for: %s' % path
        print path_words
        print 'Matches: ', all_matching_subpubs
        sys.exit(0)
    row['org_name'] = list(all_matching_subpubs)[0]


def tidy_uploads():
    in_filename = 'uploads_report.csv'
    out_filename = 'uploads_report_tidied.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = unicodecsv.DictReader(csv_read_file, encoding='utf8')
        rows = []
        for row in csv_reader:
            if row['org_name'] == 'Ministry of Defence':
                mod_subpublisher(row)

            title = canonize(row['org_name'])

            match = DguOrgs.by_canonized_title().get(title)
            if not match:
                match = \
                    Aliases.instance().get_or_reconcile(row['org_name'])
                if not match:
                    print 'Not matched'
                    #rows.append(row)  # save it anyway?
                    continue
            if isinstance(match, basestring):
                match = DguOrgs.by_title()[match]
            row['org_name'] = match['title']
            rows.append(row)
    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = unicodecsv.DictWriter(
            csv_write_file,
            fieldnames=csv_reader.fieldnames,
            encoding='utf8')
        csv_writer.writeheader()
        for row in rows:
            csv_writer.writerow(row)
    print 'Written', out_filename


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', choices=['triplestore', 'uploads'])
    args = parser.parse_args()
    if args.input == 'triplestore':
        tidy_triplestore()
    elif args.input == 'uploads':
        tidy_uploads()
    else:
        raise NotImplementedError
