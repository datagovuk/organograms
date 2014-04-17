# Organograms 

View the viz at [http://zephod.github.io/organograms](http://zephod.github.io/organograms).

---

To run the ETL from the command line, first download the XLS archive and place the files in `data/xls`. Sorry I couldn't include them in the repo: They are not open data, and they are 1.06GB.

    sudo pip install pandas xlrd numpy
    ./etl_to_csv.py data/xls/*.xls data/csv
