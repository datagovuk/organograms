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


Get counts of triples in each graph (version):

    $ python triplestore_query.py graph_counts
    All graphs 3723208
    default graph 590601
    2011-03-30 0
    2011-09-03 0
    2012-03-31 706749
    2012-09-30 658938
    2013-03-31 633963
    2013-09-30 590601
    2014-03-31 114257
    2014-09-30 0
    2015-03-31 0
    2015-09-30 0
'''

import argparse
import requests
from pprint import pprint

args = None


def departments_cmd():
    depts = departments_query(graph=args.graph)
    for dept in depts:
        print dept['uri'], dept['graph'] if 'graph' in dept else ''
    print '%s departments' % len(depts)


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
    elif graph:
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
    print query
    resp = _run_query(query)
    depts = []
    for result in resp['results']['bindings']:
        dept = {'title': result['dept']['value'],
                'uri': result['uri']['value'],
                'parent': result['parent']['value'] if 'parent' in result else None}
        if graph == 'all':
            dept['graph'] = graph_name(result['g']['value'])
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
    print 'All graphs', graph_counts('all')
    print 'default graph', graph_counts()
    versions = [
        '2011-03-30',
        '2011-09-03',
        '2012-03-31',
        '2012-09-30',
        '2013-03-31',
        '2013-09-30',
        '2014-03-31',
        '2014-09-30',
        '2015-03-31',
        '2015-09-30',
        ]
    for version in versions:
        print version, graph_counts(graph_uri(version))


def graph_counts(graph=None):
    if graph=='all':
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


def _run_query(query, json=True):
    resp = requests.post(args.sparql_endpoint, data={'query': query})
    if not resp.ok:
        print 'Error for query: %s\n%s' % (resp.status_code, resp.content)
        import pdb; pdb.set_trace()
    if json:
        return resp.json()
    else:
        return resp.content


def graph_uri(graph_name):
    return 'http://reference.data.gov.uk/organogram/graph/%s' % graph_name


def graph_name(graph_uri):
    return graph_uri.replace('http://reference.data.gov.uk/organogram/graph/', '')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-s', '--sparql',
        dest='sparql_endpoint',
        default='http://46.43.41.16/sparql/organogram/query',
        help='URL of the sparql endpoint')
    subparsers = parser.add_subparsers()

    # subparsers for commands which can have options/arguments

    parser_properties = subparsers.add_parser('departments')
    parser_properties.add_argument(
        '-g', '--graph',
        dest='graph',
        help='select graph e.g. "all" or 2011-03-30')
    parser_properties.set_defaults(func=departments_cmd)

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
