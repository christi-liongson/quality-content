CS 122 W'20: Christi Liongson, Kenny Shaevel, and Charlie Sheils Group Project
Quality Content

========
INTRODUCTION
========

This project analyzes cable news transcripts from CNN, Fox, and MSNBC from 
January 1st, 2020 to the present. We were curious to know which speakers appeared 
most often and on the widest variety of different shows and networks, as well as 
how much speaking time they were given.


========
GENERAL USAGE NOTES
========

Create virtual environment and install required packages:

install.sh

**Note:** The webcrawler utilizes the Firefox web driver.  The driver must be 
installed in order for the crawler to run.

To run the full webcrawler:

python run_crawlers.py

To run a limited version of the webcrawler:

python run_crawlers_limited.py

To access the user interface:

In final_project/ui, run python manage.py runserver

========
REQUIREMENTS
========

All required packages can be installed using in the final_project/ui folder with 
command:

pip3 install -r requirements.txt

beautifulsoup4==4.8.2
bs4==0.0.1
joblib==0.14.1
nltk==3.4.5
numpy==1.18.1
pkg-resources==0.0.0
scikit-learn==0.22.2.post1
scipy==1.4.1
selenium==3.141.0
six==1.14.0
sklearn==0.0
soupsieve==2.0
urllib3==1.25.8


README: This file

news.sql: Schema for database news_db_2020.sqlite3. You must create the
    database by running "sqlite3 news_db_2020.sqlite3 < news.sql" from the
    command line.

run_crawlers.py: Running this file web-crawls Fox, CNN, and MSNBC and loads
    all information into the news_db_2020 database.

    crawler_fox.py: Crawls all Fox news transcripts.

    crawler_cnn.py: Crawls all CNN news transcripts.

    crawler_msnbc.py: Crawls all MSNBC news transcripts.

    news_db_2020.sqlite3: Database containing all 2020 transcripts from Fox,
        CNN, and MSNBC

run_crawlers_limited.py: Running this file web-crawls Fox, CNN, and MSNBC and
    loads all information into the news_db_limited database. This is limited
    to the first show from each network and only includes shows aired between
    2/15/2020 and 3/14/2020.

    crawler_fox_limited.py: Crawls limited range of Fox news transcripts.

    crawler_cnn_limited.py: Crawls limited range of CNN news transcripts.

    crawler_msnbc_limited.py: Crawls limited range of MSNBC news transcripts.

    news_db_limited.sqlite3: Database containing transcripts from Fox,
        CNN, and MSNBC (1 show per network) from 2/15/2020 to 3/14/2020.

crawler_util.py: Contains functions common to crawler_fox.py,
    crawler_cnn.py, crawler_msnbc.py, crawler_fox_limited.py,
    crawler_cnn_limited.py, and crawler_msnbc_limited.py

analyze.py: Performs textual analysis on transcript information

visualize.py: Queries database and returns Pandas dataframe, generates data
    viz