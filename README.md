# Organograms 

## Viz

View the draft viz at [http://zephod.github.io/organograms](http://zephod.github.io/organograms).


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


## Triple store querier

This is for querying a triple store about its organogram data. e.g.

    python triplestore_query.py departments
