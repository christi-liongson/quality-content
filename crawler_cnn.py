"""
CAPP 30122: CNN course crawler for final project

Charlie Sheils

"""

import bs4
import crawler_util
import re
import calendar

LIMIT_YEAR = 2020
MONTH_DICT = dict((v,k) for k,v in enumerate(calendar.month_name))

def get_cnn_transcript_date(article_soup):
    '''
    Given the soup from a transcript, return the date.
    '''

    airtime_raw = article_soup.find('p', class_="cnnBodyText")
    airtime_obj = re.search(\
        '([A-Z][a-z]+) ([0-9]{1,2}), ([0-9]{4}) - ([0-9]{1,2}:[ ]?[0-9]{2})',
        airtime_raw.get_text())
    year = airtime_obj.group(3)

    month = str(MONTH_DICT[airtime_obj.group(1)])
    if len(month) == 1:
        month = '0' + month
    day = str(airtime_obj.group(2))
    if len(day) == 1:
        day = '0' + day
    time = airtime_obj.group(4)
    if len(time) == 3:
        time = '0' + time
    airtime = year + '-' + month + '-' + day + ' ' + time

    return int(year), airtime


def crawl_transcript(link, db_cursor, db_connection, title, headline,
                episode_id_start, speaker_id_start, phrase_id_start):
    '''
    Crawl CNN transcript.

    Inputs:
        link: URL to transcript page
        db_cursor: DB cursor to perform SQL operations
        db_connection: connection to database
        title: title of show
        headline: name of article
        episode_id_start: (int) current episode ID
        speaker_id_start: (int) current speaker ID
        phrase_id_start: (int) current text clip ID
    '''

    transcript_request = crawler_util.get_request(link)
    transcript_text = transcript_request.text
    article_soup = bs4.BeautifulSoup(transcript_text, "html5lib")
    subheading = article_soup.find('p', class_="cnnTransSubHead")
    
    print("show is", title)
    print("headline is", headline)
    year, airtime = get_cnn_transcript_date(article_soup)

    if (headline == "White House Coronavirus Update; Federal Reserve Cuts Rate To Zero; Coronavirus Testing Available To All 50 States. Aired 5-6p ET" and
        airtime == "2020-03-15 17:00"):
        return year, episode_id_start, speaker_id_start, phrase_id_start

    if year != LIMIT_YEAR or "Did Not Air" in subheading.get_text():
        return year, episode_id_start, speaker_id_start, phrase_id_start

    for br in article_soup.find_all("br"):
        br.replace_with("\n")
    transcript_text = article_soup.find_all('p','cnnBodyText')[2].getText()

    begin_flag = '(\n[A-Z][^a-z^\n]+?:|\(BEGIN .*?\)).*'
    end_flag = ""

    phrase_id_init = phrase_id_start
    speaker_id_start, phrase_id_start = crawler_util.\
        crawl_transcript(transcript_text, begin_flag, end_flag,
            episode_id_start, speaker_id_start, phrase_id_start, db_cursor)

    if phrase_id_init != phrase_id_start:
        db_cursor.execute('INSERT INTO episode VALUES(?, ?, ?, ?)',
            (episode_id_start, headline, airtime, title))
        episode_id_start += 1
    else:
        print("DIDN'T INCREMENT, THIS TRANSCRIPT WAS EMPTY")

    db_connection.commit()

    return int(year), episode_id_start, speaker_id_start, phrase_id_start


def crawl_show(starting_url, transcript_link, db_cursor,
                           db_connection, title, episode_id_start,
                           speaker_id_start, phrase_id_start):
    '''
    Crawl all transcripts for a given show, for the requested time frame.

    Inputs:
        starting_url: (str) link to show page (to help give complete url for a
            transcript)
        transcript_link: (str) link to transcript page
        db_cursor, db_connection: database cursor and connection
        title: (str) name of show)
        episode_id_start, speaker_id_start, phrase_id_start: (ints) numbers at
            which to start speakers, episodes, and phrases

    Outputs:
        episode_id_start, speaker_id_start, phrase_id_start: (ints) updated
            starting points for the next transcript to be crawled
    '''
    episode_id_init = episode_id_start
    
    # Create soup object from starting page
    transcripts_request = crawler_util.get_request(transcript_link)
    transcripts_text = transcripts_request.text
    articles_soup = bs4.BeautifulSoup(transcripts_text, "html5lib")
    transcripts_by_day = articles_soup.find('div', class_='cnnSectBulletItems')
    transcripts_raw_links = transcripts_by_day.find_all('a', href=True)

    title = articles_soup.find('p', class_='cnnTransHead').get_text()

    most_recent_year = LIMIT_YEAR
    while most_recent_year >= LIMIT_YEAR:
        for article in transcripts_raw_links:
            headline = article.get_text()
            if "Did Not Air" in headline:
                continue
            link = crawler_util.convert_if_relative_url(starting_url,
                article.get('href'))
            link = re.sub("\n", "", link)
            transcript_request = crawler_util.get_request(link)
            if transcript_request is None:
                continue
            most_recent_year, episode_id_start, speaker_id_start, phrase_id_start = crawl_transcript(link, db_cursor, db_connection, title, headline,
                episode_id_start, speaker_id_start, phrase_id_start)

        transcripts_by_day = transcripts_by_day.find_next_sibling('div', class_='cnnSectBulletItems')
        transcripts_raw_links = transcripts_by_day.find_all('a', href=True)

    if episode_id_start > episode_id_init:
        db_cursor.execute('INSERT INTO show VALUES(?, ?)',
            (title, 'CNN')).fetchall()

    return episode_id_start, speaker_id_start, phrase_id_start


def go(db_cursor, db_connection, speaker_id_start=0, episode_id_start=0,
       phrase_id_start=0):
    '''
    Crawls transcripts of CNN shows and returns some TBD data structure.
    start_date: first date of transcripts to include (inclusive)
    end_date: last date of transcripts to include (inclusive)
    '''

    starting_url = ("http://transcripts.cnn.com/TRANSCRIPTS/")

    # Create soup object from starting page
    starting_request = crawler_util.get_request(starting_url)
    starting_text = starting_request.text
    starting_soup = bs4.BeautifulSoup(starting_text, "html5lib")
    show_subsection = starting_soup.find_all('span',
        class_='cnnSectBulletItems')
    show_dict = {}
    for section in show_subsection:
        for show in section.find_all('a'):

            title = show.get_text().strip()
            if title in show_dict:
                continue

            transcript_link = crawler_util.convert_if_relative_url(\
                    starting_url, show.get('href'))
            show_dict[title] = transcript_link

            episode_id_start, speaker_id_start, phrase_id_start = crawl_show(\
                starting_url, transcript_link, db_cursor, db_connection,
                title, episode_id_start, speaker_id_start, phrase_id_start)
    db_connection.commit()

    return speaker_id_start, episode_id_start, phrase_id_start
