# Convert csv files to ONE BIG json object. Used by bartree
import os, string, csv, json
from collections import OrderedDict

exclude = [
  '300913-DWP.xls',   # circular reporting structure
  '20131002-300913_Air_Govt_Data_Template-u',   # circular
  'clean-version-of-DWP-September-2013',  # circular
  'Copy-of-300913-DWP',  # circular
]
csv_path = 'csv full'

os.chdir(csv_path)

def get_org_names():
  # compute list of org names from current dir
  files = os.listdir('.')
  org_names = []
  for filename in files:
    if string.find(filename, 'csv') == -1:
      continue
    if string.find(filename, '-senior.csv') == -1:
      continue
    org_name = string.replace(filename, '-senior.csv', '')

    if org_name in exclude:
      continue

    org_names.append(org_name)

  return org_names


def build_children_lookup(junior_data, senior_data):
  # returns dict where each key is a parent node and the value is an array of children objects
  lookup = {}

  for row in senior_data:
    reports_to = row['Reports to Senior Post']

    if reports_to not in lookup:
      lookup[reports_to] = []

    lookup[reports_to].append({
      'Name' : row['Job Title'],
      'FTE': float(row['FTE']),
      # 'Senior' : True,
      'Ref' : row['Post Unique Reference']
    })

  for row in junior_data:
    reports_to = row['Reporting Senior Post']

    if reports_to not in lookup:
      lookup[reports_to] = []

    lookup[reports_to].append({
      'Name' : row['Generic Job Title'],
      'FTE': float(row['Number of Posts in FTE']),
      'Junior': True
    })

  return lookup


def get_children(ref):
  # print ref
  if ref not in children_lu:
    return []

  children = children_lu[ref]

  for child in children:
    if 'Ref' in child: # senior
      my_children = get_children(child['Ref'])
      if my_children:
        child['children'] = my_children

  return children

def convert_to_arrays(tree):
  # convert the dept and org layers to arrays
  ret = []

  for d in tree:
    dept = tree[d]
    dept['Name'] = d

    children = []
    for o in dept['children']:
      org = dept['children'][o]
      org['Name'] = o
      children.append(org)

    dept['children'] = children
    ret.append(dept)

  return ret

def compute_fte_totals(node):
  total = 0

  if 'children' in node:
    for child in node['children']:
      compute_fte_totals(child)
      if 'FTE' in child:
        total = total + child['FTE']
      total = total + child['Subtotal']

  node['Subtotal'] = total

def round_fte_totals(node):
  subtotal = node['Subtotal']
  if int(subtotal) != subtotal:
    node['Subtotal'] = round(subtotal, 1)

  if 'children' in node:
    for child in node['children']:
      round_fte_totals(child)


org_names = get_org_names()
print org_names

org_tree = {}
children_lu = {}

out = open('../all.json', 'w')

for org_name in org_names:
  print org_name

  senior_csv = open(org_name + '-senior.csv', 'r')
  senior_data = list(csv.DictReader(senior_csv))

  junior_csv = open(org_name + '-junior.csv', 'r')
  junior_data = list(csv.DictReader(junior_csv))

  # lu = build_lookup(junior_data, senior_data)
  children_lu = build_children_lookup(junior_data, senior_data)
  # print children_lu

  for row in senior_data:
    dept = row['Parent Department']
    org = row['Organisation']
    ref = row['Post Unique Reference']

    if row['Reports to Senior Post'].upper() != 'XX':
      continue

    children = get_children(ref)
    # print children

    if dept not in org_tree:
      org_tree[dept] = {
        'children': {}
      }

    if org not in org_tree[dept]['children']:
      org_tree[dept]['children'][org] = {
        'Name': org,
        'children': []
      }

    org_tree[dept]['children'][org]['children'].append({
      'Name' : row['Job Title'],
      'Ref' : row['Post Unique Reference'],
      'FTE' : float(row['FTE']),
      'children': children
    })

org_tree = convert_to_arrays(org_tree)

org_tree = {
  'Name': 'HM Government',
  'children': org_tree
}

compute_fte_totals(org_tree)
round_fte_totals(org_tree)

# print org_tree
# out.write(json.dumps(org_tree, indent=2, sort_keys = False))
out.write(json.dumps(org_tree))