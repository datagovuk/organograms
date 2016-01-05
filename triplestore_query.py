'''Tool for querying a triplestore of organogram data'''

import argparse
import requests
from pprint import pprint

args = None


def departments():
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
    for result in resp['results']['bindings']:
        dept = {'title': result['dept']['value'],
                'uri': result['uri']['value'],
                'parent': result['parent']['value'] if 'parent' in result else None}
        depts.append(dept)
        print(dept['title'])
    print '%s departments' % len(depts)

def _run_query(query):
    resp = requests.post(args.sparql_endpoint, data={'query': query})
    if not resp.ok:
        print 'Error for query: %s\n%s' % (resp.status_code, resp.content)
        import pdb; pdb.set_trace()
    return resp.json()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '-s', '--sparql',
        dest='sparql_endpoint',
        default='http://46.43.41.16/sparql/organogram/query',
        help='URL of the sparql endpoint')
    parser.add_argument('query', help='The query to make',
                        choices=['departments'])
    args = parser.parse_args()
    if args.query == 'departments':
        departments()
    else:
        raise NotImplementedError()
