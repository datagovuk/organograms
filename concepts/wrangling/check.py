import os, string, csv
from collections import OrderedDict

csv_path = 'csv'

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
    org_names.append(org_name)

  return org_names



org_names = get_org_names()
print(org_names)

for org in org_names:

  print org

  with open(org + '-senior.csv', 'r') as senior_csv:
    csv_reader = csv.DictReader(senior_csv)

    parent_departments = []
    organisations = []
    num_rows = 0
    # num_roots = 0   - there can be >1 root

    for row in csv_reader:
      num_rows = num_rows + 1

      parent_departments.append(row['Parent Department'].upper())
      organisations.append(row['Organisation'].upper())
      # if(row['Reports to Senior Post']).upper() == 'XX':
      #   num_roots = num_roots + 1

    if num_rows == 0:   # some csvs have headers but no content
      continue

    parent_departments = list(OrderedDict.fromkeys(parent_departments))
    if len(parent_departments) != 1:
      print 'Error: >1 parent department (snr)'
      print parent_departments

    organisations = list(OrderedDict.fromkeys(organisations))
    if len(organisations) != 1:
      print 'Error: >1 organisation (snr)'
      print organisations

    # if num_roots != 1:
    #   print 'Error: >1 root node (XX)'

  with open(org + '-junior.csv', 'r') as junior_csv:
    csv_reader = csv.DictReader(junior_csv)

    parent_departments = []
    organisations = []

    for row in csv_reader:
      parent_departments.append(row['Parent Department'].upper())
      organisations.append(row['Organisation'].upper())

    parent_departments = list(OrderedDict.fromkeys(parent_departments))
    if len(parent_departments) != 1:
      print 'Error: >1 parent department (jnr)'
      print parent_departments

    organisations = list(OrderedDict.fromkeys(organisations))
    if len(organisations) != 1:
      print 'Error: >1 organisation (jnr)'
      print organisations



  # department = ''

  # with open(filename, 'r') as csvfile:
  #   csvreader = csv.DictReader(csvfile)

  #   for row in csvreader:
  #     print row

