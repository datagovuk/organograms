# Organograms

This repo contains some code related to the organograms policy.

The Prime Minister committed central government and agencies to publish organograms of all staff positions from October 2010. The data includes the hierarchy of senior staff, including names, grades, job titles & salaries and numbers of junior staff that report to them.

For more info, see: http://guidance.data.gov.uk/organogram-data.html


## Viz

The current organogram vizualization code running on data.gov.uk is in Drupal.

The old version, used by TSO and on data.gov.uk 2010-2016 is here:

* https://github.com/datagovuk/organogram-explorer

and an updated version with some docs and minor improvements here:

* https://github.com/datagovuk/organogram-viz

There is are also some 'concept' vizualizations, that were tried. They are in this repo in the 'concepts', 'src' and 'public' dirs. One is hosted at [http://zephod.github.io/organograms](http://zephod.github.io/organograms).


## XLS Downloader

To download the XLS archive (about 1.0GB):

NB These files are confidential - not open data - because they contain exact salaries, rather than rounded to the nearest 5k, and drafts and notes.

Set the variables with the secret credentials and then run scrape_data.py:

    cd organograms
    export SCRAPE_EMAIL=
    export SCRAPE_USERNAME=
    export SCRAPE_PASSWORD=
    python scrape_data.py data/xls data/csv-old


## XLS to CSV Converter

To run the converter from the command line, first download the XLS archive and place the files in `data/xls`. Then:

    sudo pip install pandas xlrd numpy
    ./etl_to_csv.py data/xls/*.xls data/csv-generated

NB if you get an error about `cc1plus` when installing pandas then you probably need to do this first:

    sudo apt-get install g++

To run the tests:

    nosetests tests/test_etl_to_csv.py


## Triple store querier

This is for querying a triple store about its organogram data. e.g.

    python triplestore_query.py departments


## TSO migration scripts

These scripts take the organogram data out of the TSO servers (as Excel files and triplestore), does some processing and outputs them as Excel files with an index, for reading into the Drupal-based organogram back-end system. These scripts were used 1st October 2016.

The triplestore data converted to CSV files is stored in data/dgu/csv-from-triplestore

How the migration was run:

pip install fuzzywuzzy
pip install progress
(export passwords)
mv .compare_posts.cache.sqlite .compare_posts.cache.sqlite.bak3
mv .dgu_departments.cache.sqlite .dgu_departments.cache.sqlite.bak
mv .scrape_cache.sqlite .scrape_cache.sqlite.bak
rm data/dgu/tso-csv/*
rm data/dgu/xls/*
python uploads_scrape.py
   (creates uploads_report_raw.csv)
python uploads_scrape.py --include-private-info
   (creates uploads_report_raw_with_private.csv)
python uploads_correct.py uploads_report.csv uploads_report_with_private.csv
   (creates uploads_report.csv uploads_report_with_private.csv)
python departments_tidy.py uploads
   (creates uploads_report_tidied.csv)
python triplestore_query.py --legacy-endpoint departments -g all --csv
    (creates triplestore_departments.csv)
python departments_tidy.py triplestore
    (creates triplestore_departments_tidied.csv)
python compare_departments.py -g all departments
    (creates compare_departments.csv)

python uploads_download.py data/dgu/xls data/dgu/tso-csv
    (downloads the organogram CSVs)
python compare_posts.py triplestore-counts --junior
    (creates triplestore_post_counts.csv)
python compare_posts.py uploads
  (creates uploads_post_counts.csv)
python compare_posts.py compare
  (creates compare_post_counts.csv)

mkdir data/dgu/csv-from-triplestore data/dgu/xls-from-triplestore
python compare_posts.py triplestore-to-csv --where-uploads-unreliable --junior --include-salary-cost-of-reports
   (generates CSVs eg data/dgu/csv-from-triplestore/ministry_of_defence-2013-09-30-senior.csv)
python csv2xls.py --where-uploads-unreliable
   (generates XLSs eg data/dgu/xls-from-triplestore/youth_justice_board-2011-09-30-organogram.xls)
python tso_combined.py --check

rsync -ra --progress ../organograms/data/dgu/xls prod2:/home/co/organogram-data/data/dgu/
rsync -ra --progress ../organograms/data/dgu/xls-from-triplestore prod2:/home/co/organogram-data/data/dgu/
