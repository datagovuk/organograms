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

import requests

args = None
NEW_SPARQL_ENDPOINT = 'http://46.43.41.16/sparql/organogram/query'


def departments_cmd():
    depts = departments_query(graph=args.graph)
    depts_printed = set()
    uris = set()
    for dept in depts:
        if args.display_full:
            pprint(dept)
        else:
            print dept['uri'], dept['graph'] if 'graph' in dept else ''

        # track duplicates
        if dept['uri'] in uris:
            print 'DUPLICATE URI'
        uris.add(dept['uri'])
        dept_json = json.dumps(dept)
        if dept_json in depts_printed:
            print 'DUPLICATE DEPT'
        depts_printed.add(dept_json)
    print '%s departments' % len(depts)


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
        SELECT DISTINCT ?uri ?dept ?parent ?g
        WHERE {
            GRAPH ?g {
                ?uri rdf:type org:Organization;
                rdf-schema:label ?dept
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
        SELECT DISTINCT ?uri ?dept ?parent
        WHERE {
            GRAPH <%s> {
                ?uri rdf:type org:Organization;
                rdf-schema:label ?dept
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
        SELECT DISTINCT ?uri ?dept ?parent
        WHERE {
            ?uri rdf:type org:Organization;
            rdf-schema:label ?dept
            OPTIONAL {
                ?uri <http://reference.data.gov.uk/def/central-government/parentDepartment> ?parent
            }
        }
        order by (?uri)'''.strip()
    resp = _run_query(query)
    depts = []
    if not args.legacy_endpoint:
        for result in resp['results']['bindings']:
            dept = {'title': result['dept']['value'],
                    'uri': result['uri']['value'],
                    'parent': result['parent']['value'] if 'parent' in result else None}
            if graph == 'all':
                dept['graph'] = graph_name(result['g']['value'])
            depts.append(dept)
    else:
        for result in resp.findall('.//{http://www.w3.org/2005/sparql-results#}result'):
            dept = {}
            for binding in result.findall('{http://www.w3.org/2005/sparql-results#}binding'):
                key = binding.attrib['name']
                if key == 'title':
                    key = 'dept'
                value = '; '.join([t for t in binding.itertext()])
                dept[key] = value
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
    versions = [
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
        ]
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
