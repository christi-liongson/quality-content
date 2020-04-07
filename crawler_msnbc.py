"""
CAPP 30122: MSNBC Transcript Crawler

Charlie Sheils
"""

import bs4
import crawler_util
import re
import calendar
import time

LIMIT_YEAR = 2020
MONTH_DICT = dict((v,k) for k,v in enumerate(calendar.month_name))


def get_msnbc_transcript_date(article_soup):
    airtime_raw = article_soup.find('meta', property="nv:date").get('content')
    # print("raw airtime is", airtime_raw)
    airtime_obj = re.search('([0-9]{2})/([0-9]{2})/([0-9]{4}) ([0-9]{2}:[0-9]{2}:[0-9]{2})', airtime_raw)
    year = airtime_obj.group(3)

    if int(year) != LIMIT_YEAR:
        return episode_id_start, speaker_id_start, phrase_id_start

    month = airtime_obj.group(1)
    day = airtime_obj.group(2)
    time_of_day = airtime_obj.group(4)
    airtime = year + '-' + month + '-' + day + ' ' + time_of_day
    if year + '-' + month + '-' + day == '2020-03-26':
        airtime = '2020-02-26' + ' ' + time_of_day

    return int(year), airtime


def crawl_msnbc_transcript(link, db_cursor, db_connection, title,
                episode_id_start, speaker_id_start, phrase_id_start):
    '''
    Crawl MSNBC transcript.
    '''

    transcript_request = crawler_util.get_request(link)
    transcript_text = transcript_request.text
    article_soup = bs4.BeautifulSoup(transcript_text, "html5lib")
    
    year, airtime = get_msnbc_transcript_date(article_soup)
    if year != LIMIT_YEAR:
        return episode_id_start, speaker_id_start, phrase_id_start

    headline_raw = article_soup.find('meta', property="nv:title").get('content')
    headline = re.search("(.*?) TRANSCRIPT", headline_raw).group(1)
    db_cursor.execute('INSERT INTO episode VALUES(?, ?, ?, ?)',
        (episode_id_start, headline, airtime, title))

    transcript_raw_text = article_soup.find('div', itemprop="articleBody").find_all('p')
    transcript_text = crawler_util.join_text_chunks(transcript_raw_text)

    begin_flag = ".*"
    end_flag = "(THIS IS A RUSH TRANSCRIPT|Copyright 2020).*"
    speaker_id_start, phrase_id_start = crawler_util.\
        crawl_transcript(transcript_text, begin_flag, end_flag,
            episode_id_start, speaker_id_start, phrase_id_start, db_cursor)

    db_connection.commit()
    episode_id_start += 1

    return episode_id_start, speaker_id_start, phrase_id_start


def crawl_show(starting_url, transcripts_link, db_cursor,
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
    transcripts_request = crawler_util.get_request(transcripts_link)
    transcripts_text = transcripts_request.text
    articles_soup = bs4.BeautifulSoup(transcripts_text, "html5lib")
    show_day = articles_soup.find('div', class_='transcript-item')

    year = int(show_day.find('a').get_text()[-4:])
    while year >= LIMIT_YEAR:
        # Crawl transcript
        link = crawler_util.convert_if_relative_url(\
                starting_url, show_day.find('a').get('href'))
        episode_id_start, speaker_id_start, phrase_id_start = crawl_msnbc_transcript(\
            link, db_cursor, db_connection, title, episode_id_start,
            speaker_id_start, phrase_id_start)

        show_day = show_day.find_next('div', class_='transcript-item')
        if show_day is None:
            break
        year = int(show_day.find('a').get_text()[-4:])

    if episode_id_start > episode_id_init:
        db_cursor.execute('INSERT INTO show VALUES(?, ?)',
            (title, 'MSNBC')).fetchall()

    return episode_id_start, speaker_id_start, phrase_id_start


def go(db_cursor, db_connection, speaker_id_start=0, episode_id_start=0,
       phrase_id_start=0):
    '''
    Crawls transcripts of CNN shows and returns some TBD data structure.
    start_date: first date of transcripts to include (inclusive)
    end_date: last date of transcripts to include (inclusive)
    '''

    starting_url = ("http://www.msnbc.com/transcripts")

    # Create soup object from starting page
    starting_request = crawler_util.get_request(starting_url)
    starting_text = starting_request.text
    starting_soup = bs4.BeautifulSoup(starting_text, "html5lib")
    show_list = starting_soup.find('div', class_='item-list').find_all('a')

    for show in show_list:
        link = show.get('href')
        if "/nav-" in link:
            continue
        title = show.get_text()
        transcripts_link = crawler_util.convert_if_relative_url(\
                starting_url, show.get('href'))

        episode_id_start, speaker_id_start, phrase_id_start = crawl_show(\
            starting_url, transcripts_link, db_cursor, db_connection,
            title, episode_id_start, speaker_id_start, phrase_id_start)

    return speaker_id_start, episode_id_start, phrase_id_start
