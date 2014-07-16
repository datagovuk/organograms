# coding=UTF-8
# Convert each csv file pair (senior + junior) to individual json trees
# This is sketchy code - could do with a rewrite
import os, string, csv, json
from collections import OrderedDict

exclude = [
  '300913-DWP.xls',   # circular reporting structure
  '20131002-300913_Air_Govt_Data_Template-u',   # circular
  'clean-version-of-DWP-September-2013',  # circular
  'Copy-of-300913-DWP',  # circular
  'sources', # empty
  'Government-staff-and-salary-data-blank-template---September-2013-FINAL-junior-data.csv', # empty
  'Government-staff-and-salary-data-blank-template---September-2013-FINAL-senior-data.csv', # empty
]
csv_path = 'csv full'

def get_org_names():
  # compute list of org names from current dir
  files = os.listdir(csv_path)
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
      'jobtitle' : row['Job Title'],
      'name' : row['Name'],
      'grade' : row['Grade'],
      'FTE': float(row['FTE']),
      'unit': row['Unit'],
      'payfloor': row['Actual Pay Floor (£)'],
      'payceiling': row['Actual Pay Ceiling (£)'],
      'ref' : row['Post Unique Reference']
    })

  for row in junior_data:
    reports_to = row['Reporting Senior Post']

    if reports_to not in lookup:
      lookup[reports_to] = []

    lookup[reports_to].append({
      'jobtitle' : row['Generic Job Title'],
      'grade' : row['Grade'],
      'FTE': float(row['Number of Posts in FTE']),
      'unit': row['Unit'],
      'payfloor': row['Payscale Minimum (£)'],
      'payceiling': row['Payscale Maximum (£)'],
      'junior': True
    })

  return lookup


def get_children(ref):
  # print ref
  if ref not in children_lu:
    return []

  children = children_lu[ref]

  for child in children:
    if 'ref' in child: # senior
      my_children = get_children(child['ref'])
      if my_children:
        child['children'] = my_children

  return children


org_names = get_org_names()
print org_names


children_lu = {}


for org_name in org_names:
  out = open('output/orgs/' + org_name + '.json', 'w')

  senior_csv = open(csv_path + '/' + org_name + '-senior.csv', 'r')
  senior_data = list(csv.DictReader(senior_csv))

  junior_csv = open(csv_path + '/' + org_name + '-junior.csv', 'r')
  junior_data = list(csv.DictReader(junior_csv))

  children_lu = build_children_lookup(junior_data, senior_data)

  roots = []
  for row in senior_data:
    # dept = row['Parent Department']
    # org = row['Organisation']
    ref = row['Post Unique Reference']

    if row['Reports to Senior Post'].upper() != 'XX':
      continue

    children = get_children(ref)

    roots.append({
      'jobtitle': row['Job Title'],
      'name' : row['Name'],
      'grade' : row['Grade'],
      'FTE': float(row['FTE']),
      'unit': row['Unit'],
      'payfloor': row['Actual Pay Floor (£)'],
      'payceiling': row['Actual Pay Ceiling (£)'],
      'children': children
    })

  # create a single root representing the organisation
  root = {
    'jobtitle': row['Organisation'],
    'children': roots
  }

  # out.write(json.dumps(roots, indent=2, sort_keys = False))
  out.write(json.dumps(root))
  out.close()
