# Convert csv files to json structure describing dept/org structure
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

def check_number_of_depts_and_orgs(org):
  if len(org['departments']) > 1:
    print 'more than 1 dept in ' + org_name
    print org['departments']

  if len(org['departments']) == 0:
    print 'zero depts in ' + org_name

  if len(org['organisations']) > 1:
    print 'more than 1 org in ' + org_name
    print org['organisations']

  if len(org['organisations']) == 0:
    print 'zero orgs in ' + org_name

def build_tree(orgs):
  # build nested array of depts and orgs
  depts = {}

  for org in orgs:
    organisation = org['organisations'][0] # HACK? just use first org
    department = org['departments'][0] # HACK? just use first dept

    if department not in depts:
      depts[department] = {
        'name': department,
        'organisations': []
      }

    depts[department]['organisations'].append({
      'name': organisation,
      'filename': org['filename']
      })

  # convert to array
  ret = []
  for dept in depts:
    ret.append(depts[dept])

  return ret



org_names = get_org_names()
# print org_names


orgs = []

out = open('output/depts_and_orgs.json', 'w')

for org_name in org_names:
#  print org_name

  org = {
    'filename': org_name,
    'departments': [],
    'organisations': []
  }

  senior_csv = open(csv_path + '/' + org_name + '-senior.csv', 'r')
  senior_data = list(csv.DictReader(senior_csv))

  for row in senior_data:
    department = row['Parent Department']
    organisation = row['Organisation']

    if department not in org['departments']:
      org['departments'].append(department)

    if organisation not in org['organisations']:
      org['organisations'].append(organisation)

  check_number_of_depts_and_orgs(org)

  orgs.append(org)



orgs = build_tree(orgs)

print orgs

out.write(json.dumps(orgs))
# out.write(json.dumps(orgs, indent=2, sort_keys = False))
