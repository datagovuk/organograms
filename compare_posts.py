# -*- coding: utf-8 -*-
import re
import csv
import argparse
from collections import defaultdict
import os.path

import requests_cache
import requests
from requests.utils import quote
from progress.bar import Bar

from compare_departments import date_to_year_first
from uploads_scrape import munge_org

one_day = 60*60*24
one_month = one_day * 31
requests_cache.install_cache('.compare_posts.cache', expire_after=one_month)


def compare():
    in_filename_uploads = 'uploads_post_counts.csv'
    in_filename_triplestore = 'triplestore_post_counts.csv'
    out_filename_counts = 'compare_post_counts.csv'

    # (body_title, graph): {'senior_posts_uploads': 3, ...}
    counts = defaultdict(dict)

    all_value_names = set()
    for source, in_filename in (('uploads', in_filename_uploads),
                                ('triplestore', in_filename_triplestore)):
        with open(in_filename, 'rb') as csv_read_file:
            csv_reader = csv.DictReader(csv_read_file)
            for row in csv_reader:
                key = (row['body_title'], row['graph'])
                for field in ('senior_posts',):
                    value_name = '%s_%s' % (field, source)
                    counts[key][value_name] = row[field]
                    all_value_names.add(value_name)
    # save
    headers = ['body_title', 'graph'] + sorted(all_value_names)
    with open(out_filename_counts, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        csv_writer.writeheader()
        for key, values in sorted(counts.items(),
                                  key=lambda x: x[0][1] + x[0][0]):
            values['body_title'] = key[0]
            values['graph'] = key[1]
            csv_writer.writerow(values)
    print 'Written', out_filename_counts


def uploads_posts_all_departments():
    '''Gets a list of upload CSVs, counts the posts and saves to new files.'''
    in_filename = 'uploads_report_tidied.csv'
    out_filename_counts = 'uploads_post_counts.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        counts = []
        rows = [row for row in csv_reader]
        for row in Bar('Reading posts from organogram CSVs').iter(rows):
            senior_csv_filename = row['senior-csv-filename']
            if not senior_csv_filename:
                continue
            #print senior_csv_filename
            senior_csv_filepath = 'data/dgu/tso-csv/' + senior_csv_filename
            senior_posts = get_csv_posts(senior_csv_filepath)
            counts.append(dict(
                body_title=row['org_name'],
                graph=date_to_year_first(row['version']),
                senior_posts=len(senior_posts)))
    # save
    headers = ['body_title', 'graph', 'senior_posts']
    with open(out_filename_counts, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        csv_writer.writeheader()
        for row in counts:
            csv_writer.writerow(row)
    print 'Written', out_filename_counts


def get_csv_posts(csv_filepath):
    with open(csv_filepath, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        return [row for row in csv_reader]


def triplestore_posts(body_title, graph):
    '''Saves posts from a particular triplestore departments/graph.
    '''
    in_filename = 'triplestore_departments_tidied.csv'
    done_anything = False
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        for row in csv_reader:
            uris = row['uris'].split()
            if body_title and body_title not in (row['title'], row['name']):
                continue
            for i, graph_ in enumerate(row['graphs'].split()):
                if graph and graph != graph_:
                    continue
                body_uri = uris[i]
                senior_posts = get_triplestore_posts(body_uri, graph, print_urls=True)
                print '%s %s Senior:%s' % (row['title'], graph_,
                                           len(senior_posts))
                save_posts_csv(row['title'], graph, 'senior',
                               'data/dgu/csv-from-triplestore', senior_posts)
                done_anything = True
    if not done_anything:
        print 'Have not done anything - check arguments'


def save_posts_csv(body_title, graph, senior_or_junior, directory, posts):
    '''Given a list of posts, saves them in the standard CSV format.
    '''
    out_filename = '{org}-{graph}-{senior_or_junior}.csv'.format(
        org=munge_org(body_title),
        graph=graph.replace('/', '-'),
        senior_or_junior=senior_or_junior)
    out_filepath = os.path.join(directory, out_filename)
    headers = [
        'Post Unique Reference', 'Name', 'Grade', 'Job Title',
        'Job/Team Function',
        'Parent Department', 'Organisation', 'Unit',
        'Contact Phone', 'Contact E-mail',
        'Reports to Senior Post',
        'Salary Cost of Reports (£)',
        'FTE Actual Pay Floor (£)', 'Actual Pay Ceiling (£)',
        'Professional/Occupational Group',
        'Notes', 'Valid', 'URI',
        ]
    with open(out_filepath, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        csv_writer.writeheader()

        def get_id_from_uri(uri):
            if uri is None:
                return None
            return uri.split('/')[-1]

        def split_salary_range(range_txt):
            # e.g. u'\xa30 - \xa30'
            if range_txt is None:
                return (None, None)
            return range_txt.replace(u'£', '').split(' - ')

        for post in posts:
            # convert the LD post to the standard organogram type
            row = {}
            row['Post Unique Reference'] = get_id_from_uri(post['uri'])
            row['Name'] = ''
            row['Grade'] = post['grade']
            row['Job Title'] = post['label']
            row['Job/Team Function'] = post['comment']
            row['Parent Department'] = ''
            row['Organisation'] = body_title
            row['Unit'] = ''
            row['Contact Phone'] = ''
            row['Contact E-mail'] = ''
            row['Reports to Senior Post'] = \
                get_id_from_uri(post['reports_to_uri'])
            row['Salary Cost of Reports (£)'] = ''
            salary_range = split_salary_range(post['salary_range'])
            row['FTE Actual Pay Floor (£)'] = salary_range[0]
            row['Actual Pay Ceiling (£)'] = salary_range[1]
            row['Professional/Occupational Group'] = ''
            row['Notes'] = ''
            row['Valid'] = ''
            # linked data CSV only
            row['URI'] = post['uri']
            csv_writer.writerow(row)
    print 'Written', out_filepath


def triplestore_posts_all_departments():
    '''Gets a list of triplestore departments/graphs, gets the posts,
    and saves posts and counts to new files.
    '''
    in_filename = 'triplestore_departments_tidied.csv'
    out_filename_counts = 'triplestore_post_counts.csv'
    #out_filename_posts = 'triplestore_posts.csv'
    with open(in_filename, 'rb') as csv_read_file:
        csv_reader = csv.DictReader(csv_read_file)
        counts = []
        rows = [row for row in csv_reader]
        for row in Bar('Reading posts from organizations').iter(rows):
            #print row['title']
            uris = row['uris'].split()
            for i, graph in enumerate(row['graphs'].split()):
                body_uri = uris[i]
                senior_posts = get_triplestore_posts(body_uri, graph)
                counts.append(dict(
                    body_title=row['title'],
                    graph=graph,
                    senior_posts=len(senior_posts)))
    # save
    headers = ['body_title', 'graph', 'senior_posts']
    with open(out_filename_counts, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        csv_writer.writeheader()
        for row in counts:
            csv_writer.writerow(row)
    print 'Written', out_filename_counts


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
            senior_posts = get_triplestore_posts(row['uri'], row['graph'])
            row['num_senior_posts'] = len(senior_posts)
            rows.append(row)

    # save
    headers = csv_reader.fieldnames
    if 'num_senior_posts' not in headers:
        headers.append('num_senior_posts')
    with open(out_filename, 'wb') as csv_write_file:
        csv_writer = csv.DictWriter(csv_write_file,
                                    fieldnames=headers)
        for row in rows:
            csv_writer.writerow(row)
    print 'Written', out_filename


def get_triplestore_posts(body_uri, graph, print_urls=False):
    # uri
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

    def get_value(value, q='label'):
        if isinstance(value, dict):
            value_ = value.get(q)
            if value_:
                return get_value(value_, q)
            return value_
        elif isinstance(value, list):
            return '; '.join(get_value(val, q) for val in value)
        elif isinstance(value, basestring):
            return value
        elif value is None:
            return None
        else:
            import pdb; pdb.set_trace()
            raise NotImplementedError
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
                post = {}
                post['uri'] = item['_about']
                post['label'] = item['label'][0]
                post['comment'] = item.get('comment')

                post['salary_range'] = get_value(item.get('salaryRange'))
                post['grade'] = get_value(item.get('grade'))
                post['reports_to_uri'] = get_value(item.get('reportsTo'), '_about')
                senior_posts.append(post)
            except Exception, e:
                import pdb; pdb.set_trace()
        # is there another page?
        per_page = response.json()['result']['itemsPerPage']
        if len(items) < per_page:
            break
        page += 1
    return senior_posts


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', choices=['triplestore', 'uploads', 'compare'])
    parser.add_argument('--body')
    parser.add_argument('--graph')
    args = parser.parse_args()
    if args.input == 'triplestore':
        if not (args.body or args.graph):
            triplestore_posts_all_departments()
        else:
            triplestore_posts(args.body, args.graph)
    elif args.input == 'uploads':
        uploads_posts_all_departments()
    elif args.input == 'compare':
        compare()
    else:
        raise NotImplementedError
