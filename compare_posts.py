# -*- coding: utf-8 -*-
import re
import csv
import argparse
from collections import defaultdict
import os.path
import traceback
import copy
from pprint import pprint

import requests_cache
import requests
from requests.utils import quote
from progress.bar import Bar
# pip install unicodecsv
import unicodecsv
from departments_tidy import match_to_dgu_dept

from compare_departments import date_to_year_first
from uploads_scrape import munge_org
from csv2xls import int_if_possible


requests_cache.install_cache('.compare_posts.cache')
global args
args = None


def compare():
    in_filename_uploads = 'uploads_post_counts.csv'
    in_filename_triplestore = 'triplestore_post_counts.csv'
    out_filename_counts = 'compare_post_counts.csv'

    # (body_title, graph): {'senior_posts_uploads': 3, ...}
    counts = defaultdict(dict)

    for source, in_filename in (('uploads', in_filename_uploads),
                                ('triplestore', in_filename_triplestore)):
        with open(in_filename, 'rb') as csv_read_file:
            csv_reader = csv.DictReader(csv_read_file)
            for row in csv_reader:
                key = (row['body_title'], row['graph'])
                for field in ('senior_posts', 'junior_posts'):
                    value_name = '%s_%s' % (field, source)
                    counts[key][value_name] = int_if_possible(row[field])
    # save
    headers = ['body_title', 'graph',
               'senior_posts_triplestore', 'senior_posts_uploads', 'senior_diff',
               'junior_posts_triplestore', 'junior_posts_uploads', 'junior_diff',
               ]
    with open(out_filename_counts, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        csv_writer.writeheader()
        for key, values in sorted(counts.items(),
                                  key=lambda x: x[0][1] + x[0][0]):
            values['body_title'] = key[0]
            values['graph'] = key[1]
            for j_or_s in ('senior', 'junior'):
                diff = \
                    (values.get('%s_posts_triplestore' % j_or_s) or 0) - \
                    (values.get('%s_posts_uploads' % j_or_s) or 0)
                values['%s_diff' % j_or_s] = diff if diff > 0 else None
            csv_writer.writerow(values)
    print 'Written', out_filename_counts


def uploads_posts_all_departments():
    '''Gets a list of upload CSVs, counts the posts and saves the counts.'''
    in_filename = 'uploads_report_tidied.csv'
    in_csv_path = 'data/dgu/tso-csv/'
    out_filename_counts = 'uploads_post_counts.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        counts = []
        rows = [row for row in csv_reader
                if row['state'] == 'published']
        for row in Bar('Reading posts from organogram CSVs').iter(rows):
            posts = {}
            for junior_or_senior in ('senior', 'junior'):
                csv_filename = row['%s-csv-filename' % junior_or_senior]
                if not csv_filename:
                    continue
                #print csv_filename
                csv_filepath = in_csv_path + csv_filename
                if not os.path.exists(csv_filepath):
                    print '\nCSV is missing - skipping', csv_filepath
                    continue
                posts[junior_or_senior] = get_csv_posts(
                    csv_filepath, junior_or_senior)
            counts.append(dict(
                body_title=row['org_name'],
                graph=date_to_year_first(row['version']),
                senior_posts=len(posts['senior']) if 'senior' in posts else None,
                junior_posts=len(posts['junior']) if 'junior' in posts else None,
                ))

    # MOD fudge. Triplestore has MOD combined, but uploads it split up. So
    # combine counts here.
    mod_counts = defaultdict(lambda: [0, 0])
    counts_ = []
    for row in counts:
        if row['body_title'] in MOD_AGGREGATED_SUBPUBS:
            mod_counts[row['graph']][0] += row['senior_posts'] or 0
            mod_counts[row['graph']][1] += row['junior_posts'] or 0
        counts_.append(row)
    for graph, posts in mod_counts.items():
        counts_.append(dict(
            body_title='Ministry of Defence',
            graph=graph,
            senior_posts=posts[0],
            junior_posts=posts[1],
            ))

    # save
    headers = ['body_title', 'graph', 'senior_posts', 'junior_posts']
    with open(out_filename_counts, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        csv_writer.writeheader()
        for row in counts_:
            csv_writer.writerow(row)
    print 'Written', out_filename_counts


# MOD sub publishers that the triplestore aggregates under MoD
MOD_AGGREGATED_SUBPUBS = (
    'Permanent Joint Headquarters',
    'Air Command',
    'MoD Central Top Level Budget',
    'Army Command',
    'Defence Infrastructure Organisation',
    'Defence Equipment and Support',
    'Navy Command',
    'Defence Science and Technology Laboratory',
    'Head Office and Corporate Services (MoD)',
    'Joint Forces Command',
    'Single Source Regulations Office',
    #'National Army Museum',
    )


def get_csv_posts(csv_filepath, junior_or_senior):
    with open(csv_filepath, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        try:
            if junior_or_senior == 'senior':
                rows = [row for row in csv_reader
                        if row['Name'].lower() not in ('eliminated',
                                                       'elimenated')]
            else:
                rows = list(csv_reader)
        except Exception:
            traceback.print_exc()
            import pdb; pdb.set_trace()
        return rows


def triplestore_posts_to_csv(body_title_filter, graph_filter, where_uploads_unreliable):
    '''Saves posts as CSV, from a particular triplestore departments/graph,
    optionally including junior posts.
    '''
    from tso_combined import can_we_use_the_upload_spreadsheet

    in_filename = 'triplestore_departments_tidied.csv'
    done_anything = False
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        for row in csv_reader:
            uris = row['uris'].split()
            if body_title_filter and \
                    body_title_filter not in (row['title'], row['name']):
                continue
            for i, graph in enumerate(row['graphs'].split()):
                if graph_filter and graph_filter != graph:
                    continue
                if where_uploads_unreliable and \
                        can_we_use_the_upload_spreadsheet(
                            row['title'], graph):
                    continue
                body_uri = uris[i]
                senior_posts, junior_posts, num_eliminated_senior_posts, source_files = \
                    get_triplestore_posts(body_uri, graph, print_urls=args.verbose)
                print '%s %s Senior:%s Junior:%s' % (
                    row['title'], graph,
                    len(senior_posts) - num_eliminated_senior_posts,
                    len(junior_posts) if args.junior else 'not checked'
                    )
                pprint(dict(source_files))
                parent_department = \
                    get_triplestore_parent_department(body_uri, graph, print_urls=args.verbose)
                save_posts_csv(row['title'], graph, 'senior', senior_posts,
                               parent_department)
                if junior_posts is not None:
                    save_posts_csv(row['title'], graph, 'junior',
                                   junior_posts, parent_department)
                done_anything = True
    if not done_anything:
        print 'Have not done anything - check arguments'


def get_id_from_uri(uri):
    if uri is None:
        return None
    return uri.split('/')[-1]


payband_re = re.compile('http://reference.data.gov.uk/def/.+?/.+?/payband/')


def filepath_for_csv_from_triplestore(body_title, graph, senior_or_junior):
    directory = 'data/dgu/csv-from-triplestore'
    out_filename = '{org}-{graph}-{senior_or_junior}.csv'.format(
        org=munge_org(body_title, separation_char='_'),
        graph=graph.replace('/', '-'),
        senior_or_junior=senior_or_junior)
    out_filepath = os.path.join(directory, out_filename)
    return out_filepath


def save_posts_csv(body_title, graph, senior_or_junior, posts,
                   parent_department):
    '''Given a list of posts, saves them in the standard CSV format.
    '''
    out_filepath = filepath_for_csv_from_triplestore(
        body_title, graph, senior_or_junior)
    if senior_or_junior == 'senior':
        headers = [
            'Post Unique Reference', 'Name', 'Grade (or equivalent)',
            'Job Title',
            'Job/Team Function',
            'Parent Department', 'Organisation', 'Unit',
            'Contact Phone', 'Contact E-mail',
            'Reports to Senior Post',
            u'Salary Cost of Reports (£)',
            'FTE', u'Actual Pay Floor (£)', u'Actual Pay Ceiling (£)',
            '',  # blank column
            'Professional/Occupational Group',
            'Notes', 'Valid?',
            'URI',
            ]
    else:
        headers = [
            'Parent Department', 'Organisation', 'Unit',
            'Reporting Senior Post', 'Grade',
            u'Payscale Minimum (£)', u'Payscale Maximum (£)',
            'Generic Job Title', 'Number of Posts in FTE',
            'Professional/Occupational Group',
            ]

    with open(out_filepath, 'wb') as csv_write_file:
        csv_writer = unicodecsv.DictWriter(csv_write_file,
                                           fieldnames=headers,
                                           dialect=csv.excel,
                                           quoting=csv.QUOTE_ALL,
                                           encoding='utf-8')
        csv_writer.writeheader()

        def parse_salary_range(range_txt):
            range_ = split_salary_range(range_txt)

            # canonize variants of N/A and N/D (although the latter is not
            # strictly allowed)
            for i, bound in enumerate(range_):
                if not isinstance(bound, basestring):
                    continue
                bound = bound.lower().strip('-')
                if bound in ('n/a', 'na'):
                    range_[i] = 'N/A'
                if bound in ('n/d', 'nd'):
                    range_[i] = 'N/D'
            return range_

        def split_salary_range(range_txt):
            # e.g. u'\xa30 - \xa30'
            # occasionally: u'\xa330283 - \xa340777; \xa334068 - \xa344599'
            if range_txt is None:
                return [None, None]
            if range_txt.startswith(u'http://reference.data.gov.uk/id/salary-range/'):
                # e.g. u'http://reference.data.gov.uk/id/salary-range/Loan in non BIS PR 0-'
                # e.g. 'http://reference.data.gov.uk/id/salary-range/N / D-'
                salary = range_txt.replace('http://reference.data.gov.uk/id/salary-range/', '')
                return [salary, salary]
            if payband_re.search(range_txt):
                # e.g. 'http://reference.data.gov.uk/def/public-body/environment-agency/payband/ns'
                salary = payband_re.sub('', range_txt)
                return [salary, salary]
            range_ = range_txt.replace(u'£', '').split(' - ')
            if len(range_) < 2:
                import pdb; pdb.set_trace()
            return [range_[0], range_[-1]]

        try:
            if senior_or_junior == 'senior':
                for post in posts:
                    # convert the LD post to the standard organogram type
                    row = {}
                    row['Post Unique Reference'] = get_id_from_uri(post['uri'])
                    row['Name'] = post['name']
                    row['Grade (or equivalent)'] = post['grade']
                    row['Job Title'] = post['label']
                    row['Job/Team Function'] = post['comment']
                    row['Parent Department'] = parent_department
                    row['Organisation'] = body_title
                    row['Unit'] = post['unit']
                    row['Contact Phone'] = post['phone']
                    row['Contact E-mail'] = post['email']
                    row['Reports to Senior Post'] = \
                        get_id_from_uri(post['reports_to_uri']) or 'XX'
                    row[u'Salary Cost of Reports (£)'] = \
                        post.get('salary_cost_of_reports', '')
                    salary_range = parse_salary_range(post['salary_range'])
                    row['FTE'] = post['fte']
                    if not salary_range[0] or not salary_range[1]:
                        # simple correction
                        if post['grade'] == 'SCS1':
                            salary_range[0] = salary_range[1] = 'N/D'
                    row[u'Actual Pay Floor (£)'] = salary_range[0]
                    row[u'Actual Pay Ceiling (£)'] = salary_range[1]
                    row['Professional/Occupational Group'] = \
                        resolve_profession(post['profession'])
                    row['Notes'] = ''
                    row['Valid?'] = ''
                    # linked data CSV only
                    row['URI'] = post['uri']
                    row['source_file'] = post['source_file']
                    row['source_line'] = post['source_line']

                    # MOD denotes heads of navy/army etc as reporting to
                    # themselves. Convert to the 'XX' convention
                    if row['Organisation'] == 'Ministry of Defence' and \
                            row['Reports to Senior Post'] == \
                            row['Post Unique Reference']:
                        row['Reports to Senior Post'] = 'XX'

                    csv_writer.writerow(row)
            else:
                for post in sorted(posts, key=lambda p: p['row_index']):
                    row = {}
                    row['Parent Department'] = parent_department
                    row['Organisation'] = body_title
                    row['Unit'] = post['unit']
                    row['Reporting Senior Post'] = post['reports_to']
                    row['Grade'] = post['grade']
                    salary_range = parse_salary_range(post['salary_range'])
                    row[u'Payscale Minimum (£)'] = salary_range[0]
                    row[u'Payscale Maximum (£)'] = salary_range[1]
                    row['Generic Job Title'] = post['job_title']
                    row['Number of Posts in FTE'] = post['fte']
                    row['Professional/Occupational Group'] = post['profession']

                    # linked data CSV only
                    row['source_file'] = post['source_file']
                    row['source_line'] = post['source_line']

                    csv_writer.writerow(row)
        except Exception:
            traceback.print_exc()
            import pdb; pdb.set_trace()
    print 'Written', out_filepath


def triplestore_post_counts(body_title, graph):
    '''Gets a list of triplestore departments/graphs, gets the posts,
    and saves post counts in a CSV.
    '''
    in_filename = 'triplestore_departments_tidied.csv'
    out_filename_counts = 'triplestore_post_counts.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        counts = []
        rows = [row for row in csv_reader]
        for row in Bar('Reading posts from organizations').iter(rows):
            if body_title and body_title not in (row['title'], row['name']):
                continue
            #print row['title']
            uris = row['uris'].split()
            for i, graph_ in enumerate(row['graphs'].split()):
                if graph and graph != graph_:
                    continue
                body_uri = uris[i]
                (senior_posts, junior_posts, num_eliminated_senior_posts,
                    source_files) = \
                    get_triplestore_posts(body_uri, graph_)
                counts.append(dict(
                    body_title=row['title'],
                    graph=graph_,
                    senior_posts=len(senior_posts) - num_eliminated_senior_posts,
                    junior_posts=len(junior_posts) if junior_posts is not None else None,
                    source_files=repr(dict(source_files)),
                    num_source_files=len(source_files),
                    ))
    # save
    if not (body_title or graph):
        headers = ['body_title', 'graph', 'senior_posts', 'junior_posts', 'source_files', 'num_source_files']
        with open(out_filename_counts, 'wb') as csv_write_file:
            csv_writer = csv.DictWriter(csv_write_file,
                                        fieldnames=headers)
            csv_writer.writeheader()
            for row in counts:
                csv_writer.writerow(row)
        print 'Written', out_filename_counts
    else:
        if len(counts) == 1:
            from pprint import pprint
            pprint(counts[0])
        print 'Not written counts because of filters make them incomplete'



def triplestore_post_counts_all_departments():
    '''Gets a list of triplestore departments/graphs, counts the posts,
    and saves them back to triplestore_departments.csv.
    '''
    in_filename = 'triplestore_departments.csv'
    out_filename = 'triplestore_departments.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        rows = []
        for row in csv_reader:
            print row['title']
            senior_posts, junior_posts, num_eliminated_senior_posts = \
                get_triplestore_posts(row['uri'], row['graph'])
            row['num_senior_posts'] = len(senior_posts) \
                - num_eliminated_senior_posts
            if junior_posts is not None:
                row['num_junior_posts'] = len(junior_posts)
            rows.append(row)

    # save
    headers = csv_reader.fieldnames
    if 'num_senior_posts' not in headers:
        headers.append('num_senior_posts')
    if 'num_junior_posts' not in headers:
        headers.append('num_junior_posts')
    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        for row in rows:
            csv_writer.writerow(row)
    print 'Written', out_filename

def get_triplestore_parent_department(body_uri, graph, print_urls=False):
    # body_uri
    # http://reference.data.gov.uk/id/department/co
    # http://reference.data.gov.uk/id/public-body/consumer-focus
    body_type, body_name = \
        re.match('http://reference.data.gov.uk/id/(.*)/(.*)', body_uri).groups()
    # get
    # http://reference.data.gov.uk/2011-09-30/doc/public-body/appointments-commission.json
    url_base = 'http://reference.data.gov.uk/{graph}/doc/{body_type}/{body_name}.json'
    url = url_base.format(
        graph=graph,
        body_type=body_type,
        body_name=quote(body_name))
    if print_urls:
        print 'Getting: ', url
    response = requests.get(url)
    primary_topic = response.json()['result']['primaryTopic']
    if body_type == 'department':
        # in the spreadsheet, a department's parent is itself
        label = primary_topic['label'][0]
    else:
        parent_department = primary_topic['parentDepartment']
        if isinstance(parent_department, basestring) and '/hta/' in parent_department:
            # file:///cygdrive/c/temp/data/hta/2012-09-30/300912-HTA-Organogram-V1.ttl
            label = 'Department of Health'
        else:
            label = get_value(parent_department, dict_key='label', list_index=0)
        if 'http' in label:
            match = match_to_dgu_dept(label)
            label = match['title']
    return label
    # we want to store it as the triplestore did, so it matches the other CSVs
    # of the time
    #parent_department_uri = primary_topic['parentDepartment']['_about']
    #match = match_to_dgu_dept(parent_department_uri, label)
    #return match['title']

def canonize_value(value):
    value = value.strip(' \'\"\.').lower()  # remove enclosing junk
    value = re.sub('(and|the)', '', value)  # remove stop words
    value = re.sub('[^a-z0-9]', '', value)  # leave only chars
    value = re.sub('\s+', ' ', value)  # no double spaces
    return value

def get_value(value, dict_key='label', list_index=None,
              multiple_ok=False):
    '''Gets a value from a json-like mess of dicts, lists and strings. Usually
    it's just a dict with a 'label', but where it is more complicated, this
    recurses.
    '''
    options = dict(dict_key=dict_key, list_index=list_index,
                   multiple_ok=multiple_ok)
    if isinstance(value, dict):
        value_ = value.get(dict_key)
        if value_:
            return get_value(value_, **options)
        return value_
    elif isinstance(value, list):
        if len(value) == 1:
            return get_value(value[0], **options)
        if list_index is not None:
            # hopefully there are enough items in the list to get the one
            # we want, although the CSV->TSO linked data conversion was
            # lossy in this respect so if there are not enough, just assume
            # it is the same as the last one e.g. 2012-03-31 HMRC post 0
            # salary range
            if len(value) <= list_index:
                list_index = -1
            return get_value(value[list_index], **options)
        values = [get_value(val, **options) for val in value]
        deduped_values = []
        deduped_canonized_values = []
        for value__ in values:
            canonized_value = canonize_value(value__)
            if canonized_value in deduped_canonized_values:
                continue
            deduped_values.append(value__)
            deduped_canonized_values.append(canonized_value)
        if len(deduped_values) > 1 and not multiple_ok:
            print 'Which value is it?', deduped_values
            import pdb; pdb.set_trace()
        return '; '.join(deduped_values)
    elif isinstance(value, (basestring, int, float)):
        return value
    elif value is None:
        return None
    else:
        import pdb; pdb.set_trace()
        raise NotImplementedError

def get_triplestore_posts(body_uri, graph, print_urls=False):
    # body_uri
    # http://reference.data.gov.uk/id/department/co
    # http://reference.data.gov.uk/id/public-body/consumer-focus
    body_type, body_name = \
        re.match('http://reference.data.gov.uk/id/(.*)/(.*)', body_uri).groups()
    # get
    # http://reference.data.gov.uk/2015-09-30/doc/department/co/post.json?_page=1
    # http://reference.data.gov.uk/2012-09-30/doc/public-body/consumer-focus/post?_page=1
    url_base = 'http://reference.data.gov.uk/{graph}/doc/{body_type}/{body_name}/post.json?_page={page}'
    page = 1
    senior_posts = []
    source_files = defaultdict(int)

    def get_posts_from_triplestore_item(item):
        posts = []
        post = {}
        post['uri'] = item['_about']
        post['label'] = item['label'][0]
        post['comment'] = item.get('comment')
        unit_values = [d['label'][0] for d in item.get('postIn')
                       if '/unit/' in d['_about']]
        post['unit'] = unit_values[0]
        post['note'] = item.get('note')
        post['reports_to_uri'] = get_value(
            item.get('reportsTo'), dict_key='_about', list_index=0)
        # postStatus might be Current or Eliminated (or equiv URIs)
        # e.g. http://reference.data.gov.uk/2011-03-31/doc/department/dh/post/WFD005.json
        post['status'] = get_value(item.get('postStatus'), 'prefLabel',
                                   multiple_ok=True)
        if isinstance(post['reports_to_uri'], basestring) and \
                ' ' in post['reports_to_uri']:
            print 'Warning - reporting to multiple posts: %s %r' % \
                (post['uri'], post['reports_to_uri'])
            # e.g. This is due to two rows in the spreadsheet with the same ref
            # but reporting to different people - this is an error that wasn't
            # picked up at the time. Just ignore all but the first post
            # reported to.
            post['reports_to_uri'] = post['reports_to_uri'].split('; ')[0]

        held_by_list = item.get('heldBy', [])
        # Some posts are held by more than one person
        # e.g. jobshare or maternity cover
        # We save this as two or more "post_"s as that is how it is
        # represented in the organogram CSV.
        for i, held_by in enumerate(held_by_list):
            post_ = copy.deepcopy(post)
            if isinstance(held_by, basestring):
                # Some posts have a URI in the heldBy list, which is a duplicate we can ignore
                # e.g. http://reference.data.gov.uk/2011-03-31/doc/public-body/ofqual/post.json?_page=1
                continue
            post_['source_file'], post_['source_line'] = \
                parse_source(held_by['_about'])
            source_files[post_['source_file']] += 1
            post_['name'] = held_by.get('name', '')
            post_['fte'] = get_value(held_by.get('tenure'), 'workingTime', list_index=i)

            if 'profession' in held_by:
                profession_values = get_value(held_by['profession'], dict_key='prefLabel')
                profession = profession_values
            else:
                profession = None
            post_['profession'] = profession

            post_['email'] = get_value(held_by.get('email'), 'label', list_index=i)
            post_['phone'] = get_value(held_by.get('phone'), 'label', list_index=i)
            post_['salary_range'] = get_value(
                item.get('salaryRange'), list_index=i)
            post_['grade'] = get_value(item.get('grade'), list_index=i)
            posts.append(post_)
        if not held_by_list:
            # Some posts have no heldBy
            # e.g. http://reference.data.gov.uk/id/public-body/animal-health-veterinary-laboratories-agency/post/12 2011-03-31
            # so just record what we have
            post_ = copy.deepcopy(post)
            post_['name'] = ''
            post_['fte'] = ''
            post_['profession'] = ''
            post_['email'] = ''
            post_['phone'] = ''
            # multiples usually mean 2 posts have the same ID but different
            # values, which is a mistake in the spreadsheet
            post_['salary_range'] = get_value(item.get('salaryRange'),
                                              list_index=0)
            post_['grade'] = get_value(item.get('grade'), list_index=0)
            posts.append(post_)

        return posts

    while True:
        url = url_base.format(
            graph=graph,
            body_type=body_type,
            body_name=quote(body_name),
            page=page)
        if print_urls:
            print 'Getting: ', url
        response = requests.get(url)
        items = response.json()['result']['items']
        for item in items:
            try:
                posts = get_posts_from_triplestore_item(item)
                senior_posts.extend(posts)
            except Exception:
                traceback.print_exc()
                import pdb; pdb.set_trace()
        # is there another page?
        per_page = response.json()['result']['itemsPerPage']
        if len(items) < per_page:
            break
        page += 1

    # Get any missing bosses
    # e.g. this MOD post reports to an Eliminated post which is not returned by
    # the previous triplestore query.
    # It makes no sense for someone to report to an Eliminated post, and it
    # will not validate, so change them to report to the boss of the Eliminated
    # post, so that they are not orphaned.
    # http://reference.data.gov.uk/2012-03-31/doc/department/mod/post/00109782.json
    num_eliminated_senior_posts = 0
    boss_to_post_uri = dict((post['reports_to_uri'], post['uri'])
                            for post in senior_posts)
    post_uris = set(post['uri'] for post in senior_posts)
    missing_posts = set(boss_to_post_uri.keys()) \
        - post_uris \
        - set(('XX', 'xx', None, ''))
    if missing_posts:
        print 'Missing posts: ', missing_posts
        for post_uri in missing_posts:
            #e.g. http://reference.data.gov.uk/id/department/mod/post/00105232
            url = post_uri.replace('/id/',
                                   '/{graph}/doc/'.format(graph=graph)) \
                + '.json'
            if print_urls:
                print 'Getting: ', url
            response = requests.get(url)
            item = response.json()['result']['primaryTopic']
            try:
                if not 'label' in item:
                    # this means the triplestore doesn't have the item
                    # which can happen pre 2016 when things weren't validated
                    print 'Warning: Missing post %s (boss of %s) is not in the triplestore '\
                        'either: %s' % (post_uri, boss_to_post_uri.get(post_uri), url)
                    continue
                posts = get_posts_from_triplestore_item(item)
                # just check it is eliminated
                for post in posts:
                    assert post['name'] == 'Eliminated' or \
                        post['status'] in ('Eliminated', 'http://reference.data.gov.uk/def/civil-service-post-status/eliminated') or \
                        post['uri'] == 'http://reference.data.gov.uk/id/public-body/health-education-england/post/NORTH029'  # not sure why it's missing
                # record the eliminated post
                senior_posts.extend(posts)
                num_eliminated_senior_posts += len(posts)
                # change the post that reported to the eliminated post to
                # report to the eliminated post's boss
                for eliminated_post in posts:
                    for post in senior_posts:
                        if post['reports_to_uri'] == eliminated_post['uri']:
                            post['reports_to_uri'] = eliminated_post['reports_to_uri']

            except Exception:
                traceback.print_exc()
                import pdb; pdb.set_trace()

    # include_salary_cost_of_reports
    # http://reference.data.gov.uk/2012-09-30/doc/public-body/advisory-conciliation-and-arbitration-service/post/1/statistics.json
    if args.include_salary_cost_of_reports:
        url_base = 'http://reference.data.gov.uk/{graph}/doc/{body_type}/{body_name}/post/{post_id}/statistics.json?_page=1'
        for senior_post in senior_posts:
            senior_post_id = get_id_from_uri(senior_post['uri'])
            url = url_base.format(
                graph=graph,
                body_type=body_type,
                body_name=quote(body_name),
                post_id=senior_post_id,
                page=page)
            if print_urls:
                print 'Getting: ', url
            # Retry if failure
            for i in range(3):
                response = requests.get(url)
                if response.ok:
                    break
                else:
                    print "Failed request: %s" % response.reason
            items = response.json()['result']['items']
            # expect 2 items - one has the salary and the other is something
            # about 'total pay' but just seems to repeat basic info
            if not items:
                # not sure why, but occasionally there are no items
                # e.g. http://reference.data.gov.uk/2011-03-31/doc/department/dh/post/WFD005/statistics.json?_page=1
                continue
            post = {}
            for item in items:
                try:
                    if 'salaryCostOfReports' not in item['_about']:
                        # it must be the total pay item - ignore
                        continue
                    if 'salaryCostOfReports' not in item:
                        post['salary_cost_of_reports'] = 'N/D'
                        continue
                    post['salary_cost_of_reports'] = \
                        item['salaryCostOfReports']
                except Exception:
                    traceback.print_exc()
                    import pdb; pdb.set_trace()
            if 'salary_cost_of_reports' not in post:
                import pdb; pdb.set_trace()
            senior_post['salary_cost_of_reports'] = \
                post['salary_cost_of_reports']

    if not args.junior:
        return senior_posts, None, num_eliminated_senior_posts, source_files

    # junior posts
    # https://secure-reference.data.gov.uk/2012-09-30/doc/public-body/consumer-focus/post/CE1/immediate-junior-staff
    url_base = 'http://reference.data.gov.uk/{graph}/doc/{body_type}/{body_name}/post/{post_id}/immediate-junior-staff.json?_page={page}'
    junior_posts = []
    for senior_post in senior_posts:
        page = 1
        senior_post_id=get_id_from_uri(senior_post['uri'])
        while True:
            url = url_base.format(
                graph=graph,
                body_type=body_type,
                body_name=quote(body_name),
                post_id=senior_post_id,
                page=page)
            if print_urls:
                print 'Getting: ', url
            # Retry if failure
            for i in range(3):
                response = requests.get(url)
                if response.ok:
                    break
                else:
                    print "Failed request: %s" % response.reason
            items = response.json()['result']['items']
            for item in items:
                try:
                    post = {}
                    post['uri'] = item['_about']
                    post['source_file'], post['source_line'] = \
                        parse_source(item['_about'])
                    source_files[post['source_file']] += 1
                    post['reports_to'] = senior_post_id
                    post['row_index'] = \
                        int(post['uri'].split('#juniorPosts')[-1])
                    post['unit'] = get_value(item['inUnit'])
                    post['fte'] = item['fullTimeEquivalent']
                    if 'atGrade' in item:
                        post['grade'] = get_value(
                            item['atGrade'], dict_key='prefLabel',
                            list_index=0)
                        if 'salaryRange' in item['atGrade']['payband']:
                            # Sometimes you see multiple salary ranges for a
                            # payband. e.g. http://reference.data.gov.uk/2015-03-31/doc/department/mod/post/00001495/immediate-junior-staff.json?_page=1
                            # juniorPosts30 due to the two XLSs being loaded
                            # incorrectly for DSTL against one period - 09/2015
                            # and 03/2015 for the 03/2015 period. Ignore one.
                            post['salary_range'] = get_value(
                                item['atGrade']['payband']['salaryRange'],
                                list_index=0)
                        else:
                            post['salary_range'] = get_value(
                                item['atGrade']['payband'], dict_key='_about',
                                list_index=0)
                    else:
                        # sheet AirSalarySpreadsheetAsAt1Apr2016.xls junior row
                        # 300 has has a grade which is a reference to another
                        # cell, which validates, but gets lost on TSO import.
                        post['grade'] = None
                        post['salary_range'] = None
                    if 'withJob' in item:
                        post['job_title'] = get_value(item[
                            'withJob'], dict_key='prefLabel', list_index=0)
                    else:
                        post['job_title'] = item['label'][0]

                    if 'withProfession' in item:
                        profession_values = get_value(
                            item['withProfession'], dict_key='prefLabel',
                            list_index=0)
                        profession = profession_values
                    else:
                        profession = None
                    post['profession'] = profession
                except Exception:
                    traceback.print_exc()
                    import pdb; pdb.set_trace()
                junior_posts.append(post)
            # is there another page?
            per_page = response.json()['result']['itemsPerPage']
            if len(items) < per_page:
                break
            page += 1
    return senior_posts, junior_posts, num_eliminated_senior_posts, source_files


def parse_source(source_uri):
    # http://organogram.data.gov.uk/data/cabinetoffice/2015-09-30/CO-Template-FINAL#person73
    if '#' not in source_uri:
        return source_uri, ''
    splitted = source_uri.split('#')
    source_file = splitted[0].replace('http://organogram.data.gov.uk', '') + '.xls'
    source_line = splitted[-1]
    return source_file, source_line


PROFESSIONS = set('Communications, Economics, Finance, Human Resources, Information Technology, Internal Audit, Knowledge and Information Management (KIM), Law, Medicine, Military, Operational Delivery, Operational Research, Other, Planning, Policy, Procurement, Programme and Project Management (PPM), Property and asset management, Psychology, Science and Engineering, Social Research, Statisticians, Tax Professionals, Vets'.split(', '))
PROFESSIONS_LOWER = dict((p.lower(), p) for p in PROFESSIONS)
PROFESSIONS_LOWER_FIRST_WORD = dict((p.split()[0], p) for p in PROFESSIONS_LOWER)


def resolve_profession(profession_values):
    '''Takes a profession list (or maybe a string) and return a single
    profession that it represents.
    '''
    if not profession_values:
        return None
    if isinstance(profession_values, basestring):
        profession_values = [profession_values]
    assert isinstance(profession_values, list)
    matching_professions = set(profession_values) & PROFESSIONS
    if len(matching_professions) == 1:
        return list(matching_professions)[0]
    else:
        # Try any lowercase match
        for profession_value in profession_values:
            matching_profession = PROFESSIONS_LOWER.get(
                profession_value.lower().replace('project and programme',
                                                 'programme and project')
                )
            if matching_profession:
                return matching_profession
        # Try matching first word
        for profession_value in profession_values:
            matching_profession = PROFESSIONS_LOWER_FIRST_WORD.get(
                profession_value.lower().split()[0])
            if matching_profession:
                return matching_profession
        if 'scientist' in profession_values[0].lower():
            return 'Science and Engineering'
        if 'statistics' in profession_values[0].lower():
            return 'Statisticians'
        if 'project' in profession_values[0].lower():
            return 'Programme and Project Management (PPM)'
        if 'medical' in profession_values[0].lower():
            return 'Medicine'
        if 'legal' in profession_values[0].lower():
            return 'Law'
        print 'Could not resolve profession: %r', profession_values
        import pdb; pdb.set_trace()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', choices=['triplestore-to-csv', 'triplestore-counts',
                                          'uploads', 'compare'])
    #triplestore options
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Print the urls requested')
    parser.add_argument('--body')
    parser.add_argument('--graph')
    parser.add_argument('--where-uploads-unreliable', action='store_true')
    parser.add_argument('--junior', action='store_true',
                        help='Include junior posts too (expensive op)')
    parser.add_argument('--include-salary-cost-of-reports', action='store_true', help='Include the salary in the senior sheet (expensive op)')
    args = parser.parse_args()
    if args.input == 'triplestore-to-csv':
        assert (args.body or args.graph or args.where_uploads_unreliable), 'Please supply a --body or --graph filter or --where-uploads-unreliable'
        triplestore_posts_to_csv(args.body, args.graph, args.where_uploads_unreliable)
    elif args.input == 'triplestore-counts':
        triplestore_post_counts(args.body, args.graph)
    elif args.input == 'uploads':
        uploads_posts_all_departments()
    elif args.input == 'compare':
        compare()
    else:
        raise NotImplementedError
