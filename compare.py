"""Tool for comparing between the legacy and new data/triplestores

Compare departments in the triplestores:

    python compare.py -g all departments

"""
import argparse
from pprint import pprint
import sys

import requests

args = None


class InvalidGraph(Exception):
    pass


def departments_cmd():
    if args.graph and args.graph != 'all':
        graphs = [args.graph]
    else:
        graphs = GRAPHS
        args.query_quiet = True

    for graph in graphs:

        depts_new = departments_query(graph=graph, legacy_endpoint=False)
        depts_new = dict((dept['uri'], dept) for dept in depts_new)

        depts_legacy = departments_query(graph=graph, legacy_endpoint=True)
        depts_legacy = dict((dept['uri'], dept) for dept in depts_legacy)

        print 'Compare %s:' % graph
        print_difference(depts_new, depts_legacy)


def print_difference(new, legacy):
    print 'Legacy: %s  New: %s' % (len(legacy), len(new))
    if not new or legacy:
        return

    def print_some(keys, all_values):
        for key in keys:
            value = all_values[key]
            if args.display_full:
                pprint(value)
            else:
                print key, value['graph'] if 'graph' in value else ''
        print '%s departments' % len(keys)
    only_in_new = set(new) - set(legacy)
    if only_in_new:
        print 'Only in new:'
        print_some(only_in_new, new)
    only_in_legacy = set(legacy) - set(new)
    if only_in_legacy:
        print 'Only in legacy:'
        print_some(only_in_legacy, legacy)
    if not only_in_new or only_in_legacy:
        print 'No differences'


def departments_query(graph, legacy_endpoint):
    if not legacy_endpoint:
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
    elif legacy_endpoint:
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
    try:
        resp = _run_query(query, graph, legacy_endpoint)
    except InvalidGraph:
        return []
    depts = []
    if not legacy_endpoint:
        for result in resp['results']['bindings']:
            dept = {'title': result['dept']['value'],
                    'uri': result['uri']['value'],
                    'parent': result['parent']['value']
                    if 'parent' in result else None}
            if graph == 'all':
                dept['graph'] = graph_name(result['g']['value'])
            depts.append(dept)
    else:
        for result in resp.findall(
                './/{http://www.w3.org/2005/sparql-results#}result'):
            dept = {}
            for binding in result.findall(
                    '{http://www.w3.org/2005/sparql-results#}binding'):
                key = binding.attrib['name']
                if key == 'title':
                    key = 'dept'
                value = '; '.join([t for t in binding.itertext()])
                dept[key] = value
            depts.append(dept)
    return depts


def _run_query(query, graph, legacy_endpoint):
    # get_sparql_endpoint
    if legacy_endpoint:
        if graph == 'all' or not graph:
            print 'Error: You need to specify an exact graph for the legacy '\
                  'endpoint e.g. 2014-03-31.'
            sys.exit(1)
        if not graph.find('-'):
            print 'Error: Graph must be of the format like "2014-03-31"'
            sys.exit(1)
        sparql_endpoint = 'http://reference.data.gov.uk/organograms-%s/sparql'\
            % graph
    else:
        sparql_endpoint = 'http://46.43.41.16/sparql/organogram/query'

    if not args.query_quiet:
        print sparql_endpoint
        print query
    resp = requests.post(sparql_endpoint, data={'query': query})
    if not resp.ok:
        if resp.text.startswith('Invalid knowledge base name'):
            raise InvalidGraph
        print 'Error for query: %s\n%s' % (resp.status_code, resp.content)
        import pdb; pdb.set_trace()
    if not args.query_quiet:
        print
    if not legacy_endpoint:
        return resp.json()
    else:
        #legacy returns XML
        from lxml import etree
        root = etree.fromstring(resp.content)
        return root


def graph_uri(graph_name):
    return 'http://reference.data.gov.uk/organogram/graph/%s' % graph_name


def graph_name(graph_uri):
    return graph_uri.replace('http://reference.data.gov.uk/organogram/graph/', '')

GRAPHS = [
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

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-g', '--graph',
        choices=GRAPHS + ['all'],
        dest='graph',
        help='select graph e.g. "all" or 2011-03-30')
    parser.add_argument(
        '-f', '--display-full',
        dest='display_full',
        action='store_true',
        help='Display full information about each result')
    parser.add_argument(
        '-q', '--query-quiet',
        dest='query_quiet',
        action='store_true',
        help='Don\'t display the queries made')
    subparsers = parser.add_subparsers()

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
