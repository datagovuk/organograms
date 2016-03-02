import re
import csv
import argparse

import requests_cache
import requests
from requests.utils import quote
from progress.bar import Bar

from departments_tidy import match_to_dgu_dept

one_day = 60*60*24
one_month = one_day * 31
requests_cache.install_cache('.compare_posts.cache', expire_after=one_month)


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
            print senior_csv_filename
            senior_csv_filepath = 'data/dgu/tso-csv/' + senior_csv_filename
            senior_posts = get_csv_posts(senior_csv_filepath)
            counts.append(dict(
                body_title=row['org_name'],
                graph=row['version'],
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


def get_triplestore_posts(body_uri, graph):
    # uri
    # http://reference.data.gov.uk/id/department/co
    # http://reference.data.gov.uk/id/public-body/consumer-focus
    body_type, body_name = \
        re.match('http://reference.data.gov.uk/id/(.*)/(.*)', body_uri).groups()
    # get
    # http://reference.data.gov.uk/2015-09-30/doc/department/co/post.json?_page=1
    # http://reference.data.gov.uk/2012-09-30/doc/public-body/consumer-focus/post?_page=1
    url_base = 'http://reference.data.gov.uk/{graph}/doc/{body_type}/{body_name}/post.json?_page={page}'
    page = 0
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
        #print 'Getting: ', url
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


#posts = get_triplestore_posts(
    #'http://reference.data.gov.uk/id/department/co', '2015-09-30'
#    'http://reference.data.gov.uk/id/public-body/consumer-focus', '2011-09-30'
#)
#print len(posts)
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', choices=['triplestore', 'uploads'])
    args = parser.parse_args()
    if args.input == 'triplestore':
        #triplestore_post_counts_all_departments()
        triplestore_posts_all_departments()
    elif args.input == 'uploads':
        uploads_posts_all_departments()
    else:
        raise NotImplementedError
