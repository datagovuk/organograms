'''Tool for querying a triplestore of organogram data

Examples:

Get all departments (and other bodies) in the default graph (i.e. latest version)

    $ python triplestore_query.py departments
    http://reference.data.gov.uk/id/department/attorney-general
    http://reference.data.gov.uk/id/department/bis
    http://reference.data.gov.uk/id/department/co
    http://reference.data.gov.uk/id/department/cps
    http://reference.data.gov.uk/id/department/dclg
    http://reference.data.gov.uk/id/department/dcms
    http://reference.data.gov.uk/id/department/dcms
    http://reference.data.gov.uk/id/department/decc


Get all departments and which graphs (versions) there are for each:

    $ python triplestore_query.py departments -g all
    http://reference.data.gov.uk/id/department/attorney-general 2011-09-30
    http://reference.data.gov.uk/id/department/attorney-general 2012-03-31
    http://reference.data.gov.uk/id/department/attorney-general 2012-09-30
    http://reference.data.gov.uk/id/department/attorney-general 2011-09-30
    http://reference.data.gov.uk/id/department/attorney-general 2013-09-30
    http://reference.data.gov.uk/id/department/bis 2011-09-30
    http://reference.data.gov.uk/id/department/bis 2012-03-31
    http://reference.data.gov.uk/id/department/bis 2012-09-30


Get counts of triples in each graph (version) (at 46.43.41.16):

    $ python triplestore_query.py graph_counts
    All graphs 3723208
    default graph 590601
    2011-03-31 0
    2011-09-30 903953
    2012-03-31 706749
    2012-09-30 658938
    2013-03-31 633963
    2013-09-30 590601
    2014-03-31 114257
    2014-09-30 0
    2015-03-31 0
    2015-09-30 0
    other graphs 114747


Get counts of triples at reference.data.gov.uk:
    (currently broken)
    $ python triplestore_query.py --legacy-endpoint graph_counts

Compare departments
    $ python triplestore_query.py compare_departments -g 2012-03-31 [--display-full]

'''

import argparse
import json
from pprint import pprint
import sys
import csv

import requests

from uploads_scrape import VERSIONS

args = None
NEW_SPARQL_ENDPOINT = 'http://46.43.41.16/sparql/organogram/query'


def departments_cmd():
    if args.legacy_endpoint and args.graph == 'all':
        depts = []
        for graph in VERSIONS:
            args.graph = graph
            graph_depts = departments_query(graph=graph)
            depts += graph_depts
    else:
        depts = departments_query(graph=args.graph)
    depts_printed = set()
    uris = set()
    filename_bits = ['triplestore', 'departments']
    if not args.legacy_endpoint:
        filename_bits.append('new')
    filename = '_'.join(filename_bits) + '.csv'
    csv_writer = CsvWriter.init_if_enabled(filename, ('uri', 'title', 'graph', 'parent'))
    for dept in depts:
        if args.display_full:
            pprint(dept)
        else:
            print dept['uri'], dept['graph'] if 'graph' in dept else ''
        if csv_writer:
            csv_writer.write_row(dept)

        # track duplicates
        if dept['uri'] in uris:
            print 'DUPLICATE URI'
        uris.add(dept['uri'])
        dept_json = json.dumps(dept)
        if dept_json in depts_printed:
            print 'DUPLICATE DEPT'
        depts_printed.add(dept_json)
    print '%s departments' % len(depts)
    if csv_writer:
        print csv_writer.filename


def compare_departments_cmd():
    assert args.graph and args.graph != 'all'

    args.legacy_endpoint = False
    depts_new = departments_query(graph=args.graph)
    depts_new = dict((dept['uri'], dept) for dept in depts_new)

    args.legacy_endpoint = True
    depts_legacy = departments_query(graph=args.graph)
    depts_legacy = dict((dept['uri'], dept) for dept in depts_legacy)

    def print_depts(dept_uris, all_depts):
        for dept_uri in dept_uris:
            dept = all_depts[dept_uri]
            if args.display_full:
                pprint(dept)
            else:
                print dept['uri'], dept['graph'] if 'graph' in dept else ''
        print '%s departments' % len(dept_uris)
    only_in_new = set(depts_new) - set(depts_legacy)
    if only_in_new:
        print 'Only in new:'
        print_depts(only_in_new, depts_new)
    only_in_legacy = set(depts_legacy) - set(depts_new)
    if only_in_legacy:
        print 'Only in legacy:'
        print_depts(only_in_legacy, depts_legacy)


def departments_query(graph=None):
    if graph == 'all':
        query = '''
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX org: <http://www.w3.org/ns/org#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX rdf-schema: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?uri ?title ?parent ?g
        WHERE {
            GRAPH ?g {
                ?uri rdf:type org:Organization;
                rdf-schema:label ?title
                OPTIONAL {
                    ?uri <http://reference.data.gov.uk/def/central-government/parentDepartment> ?parent
                }
            }
        }
        order by (?uri)'''.strip()
    elif graph and not args.legacy_endpoint:
        query = '''
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX org: <http://www.w3.org/ns/org#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX rdf-schema: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?uri ?title ?parent
        WHERE {
            GRAPH <%s> {
                ?uri rdf:type org:Organization;
                rdf-schema:label ?title
                OPTIONAL {
                    ?uri <http://reference.data.gov.uk/def/central-government/parentDepartment> ?parent
                }
            }
        }
        order by (?uri)'''.strip() % graph_uri(graph)
    else:
        query = '''
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX org: <http://www.w3.org/ns/org#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX rdf-schema: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?uri ?title ?parent
        WHERE {
            ?uri rdf:type org:Organization;
            rdf-schema:label ?title
            OPTIONAL {
                ?uri <http://reference.data.gov.uk/def/central-government/parentDepartment> ?parent
            }
        }
        order by (?uri)'''.strip()
    resp = _run_query(query)
    depts = []
    if not args.legacy_endpoint:
        for result in resp['results']['bindings']:
            dept = {'title': result['title']['value'],
                    'uri': result['uri']['value'],
                    'parent': result['parent']['value'] if 'parent' in result else None}
            if graph == 'all':
                dept['graph'] = graph_name(result['g']['value'])
            else:
                dept['graph'] = args.graph
            depts.append(dept)
    else:
        for result in resp.findall('.//{http://www.w3.org/2005/sparql-results#}result'):
            dept = {}
            for binding in result.findall('{http://www.w3.org/2005/sparql-results#}binding'):
                key = binding.attrib['name']
                value = '; '.join([t for t in binding.itertext()])
                dept[key] = value
                # legacy only returns results from one graph
                dept['graph'] = args.graph
            depts.append(dept)
    return depts


def describe_org_cmd():
    query = '''
    DESCRIBE <http://reference.data.gov.uk/def/central-government/SeniorCivilServicePost>
    '''
    resp = _run_query(query, json=False)
    print resp


def classes_cmd():
    query = '''
    SELECT DISTINCT ?class
    WHERE {
      ?s a ?class .
    }
    '''
    resp = _run_query(query)
    classes = [
        result['class']['value']
        for result in resp['results']['bindings']]
    pprint(classes)


def properties_cmd():
    if not args.class_:
        query = '''
        SELECT DISTINCT ?property
        WHERE {
        ?s ?property ?o .
        }
        '''
    else:
        query = '''
        SELECT DISTINCT ?property
        WHERE {
          ?s a <%s>;
               ?property ?o .
               }
        ''' % args.class_
    resp = _run_query(query)
    #pprint(resp)
    properties = [
        result['property']['value']
        for result in resp['results']['bindings']]
    pprint(properties)


def graph_counts_cmd():
    total_count = int(graph_counts('all'))
    print 'All graphs', total_count
    print 'default graph', graph_counts()
    versions = VERSIONS
    sum_of_counts = 0
    for version in versions:
        count = graph_counts(graph_uri(version))
        sum_of_counts += int(count)
        print version, graph_counts(graph_uri(version))
    print 'other graphs', total_count - sum_of_counts


def graph_counts(graph=None):
    if graph == 'all':
        query = '''select (count(*) as ?count) { graph ?g { ?s ?p ?o } }'''
    elif graph:
        query = '''select (count(*) as ?count) { graph <%s> { ?s ?p ?o } }''' % graph
    else:
        # i.e. default graph
        query = '''select (count(*) as ?count) { ?s ?p ?o }'''
    resp = _run_query(query)
    #pprint(resp)
    properties = [
        result['count']['value']
        for result in resp['results']['bindings']]
    return properties[0]


def _run_query(query):
    sparql_endpoint = get_sparql_endpoint()
    print query
    print sparql_endpoint
    resp = requests.post(sparql_endpoint, data={'query': query})
    if not resp.ok:
        print 'Error for query: %s\n%s' % (resp.status_code, resp.content)
        import pdb; pdb.set_trace()
    if not args.legacy_endpoint:
        if 'DESCRIBE' not in query:
            return resp.json()
        else:
            # DESCRIBE doesn't return json, so just return it as-is
            return resp.content
    else:
        #legacy returns XML
        from lxml import etree
        root = etree.fromstring(resp.content)
        return root


def graph_uri(graph_name):
    return 'http://reference.data.gov.uk/organogram/graph/%s' % graph_name


def graph_name(graph_uri):
    return graph_uri.replace('http://reference.data.gov.uk/organogram/graph/', '')


def get_sparql_endpoint():
    # based on args.legacy_endpoint, args.sparql_endpoing and args.graph
    if args.legacy_endpoint:
        if args.graph == 'all' or not args.graph:
            print 'Error: You need to specify an exact graph for the legacy '\
                  'endpoint e.g. 2014-03-31.'
            sys.exit(1)
        if not args.graph.find('-'):
            print 'Error: Graph must be of the format like "2014-03-31"'
            sys.exit(1)
        return 'http://reference.data.gov.uk/organograms-%s/sparql' % args.graph
    else:
        return args.sparql_endpoint


class CsvWriter(object):
    def __init__(self, filename, headings):
        self.headings = headings
        self.rows_written = 0
        csv_file = open(filename, 'wb')
        self.filename = filename
        self.date_columns = []
        self.csv_writer = csv.writer(csv_file, dialect='excel')
        self.csv_writer.writerow(headings)

    @classmethod
    def init_if_enabled(cls, *kargs, **kwargs):
        if not args.csv:
            return
        return cls(*kargs, **kwargs)

    def write_row(self, row_dict):
        row = []
        for heading in self.headings:
            cell = row_dict.get(heading, '')
            if heading in self.date_columns and cell:
                cell = cell.isoformat()
            row.append(cell)
        #print row
        self.csv_writer.writerow(row)
        self.rows_written += 1


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-s', '--sparql',
        dest='sparql_endpoint',
        default=NEW_SPARQL_ENDPOINT,
        help='URL of the sparql endpoint')
    parser.add_argument(
        '--legacy-endpoint',
        dest='legacy_endpoint',
        action='store_true',
        help='Use the old sparql endpoint and syntax')
    subparsers = parser.add_subparsers()

    # subparsers for commands which can have options/arguments

    parser_properties = subparsers.add_parser('departments')
    parser_properties.add_argument(
        '-g', '--graph',
        dest='graph',
        help='select graph e.g. "all" or 2011-03-31')
    parser_properties.add_argument(
        '-f', '--display-full',
        dest='display_full',
        action='store_true',
        help='Display full information about each result')
    parser_properties.add_argument(
        '--csv',
        action='store_true',
        help='Writes the results to a CSV file')
    parser_properties.set_defaults(func=departments_cmd)

    parser_properties = subparsers.add_parser('compare_departments')
    parser_properties.add_argument(
        '-g', '--graph',
        dest='graph',
        help='select graph e.g. "all" or 2011-03-31')
    parser_properties.add_argument(
        '-f', '--display-full',
        dest='display_full',
        action='store_true',
        help='Display full information about each result')
    parser_properties.set_defaults(func=compare_departments_cmd)

    parser_properties = subparsers.add_parser('properties')
    parser_properties.add_argument(
        '-c', '--class',
        dest='class_',
        help='filter by class e.g. http://www.w3.org/ns/org#Organization')
    parser_properties.set_defaults(func=properties_cmd)

    # create simple subparsers for commands which don't already have one
    commands = [(name.replace('_cmd', ''), func)
                for name, func in locals().items()
                if (callable(func) and name.endswith('_cmd')
                    and name not in subparsers.choices.keys())]
    for name, func in commands:
        if name not in subparsers.choices.keys():
            parser_properties = subparsers.add_parser(name)
            parser_properties.set_defaults(func=func)
    args = parser.parse_args()

    # call the function
    args.func()
