'''
CAPP 30122: Fox Transcript Crawler

Charlie Sheils
'''

import re
import bs4
import time
import json
import calendar
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
import crawler_util
import datetime

LIMIT_YEAR = 2020
MAX_DATE = datetime.date(2020, 3, 14)
MIN_DATE = datetime.date(2020, 2, 15)
MONTH_DICT = dict((v,k) for k,v in enumerate(calendar.month_name))


def get_show_transcripts_page(show, starting_url):
    '''
    Get link to the show's transcript page.
    Returns None if there is no valid transcript.
    '''

    for show_link in show.find_all('a'):
        if show_link.get_text().strip() == "Transcripts":
            return crawler_util.convert_if_relative_url(\
                starting_url, show_link.get('href'))

    first_show_link = crawler_util.convert_if_relative_url(starting_url,
        show.find('a').get('href'))

    # Go to first show link to find transcripts page
    show_page_request = crawler_util.get_request(first_show_link)
    show_page_text = show_page_request.text
    show_page_soup = bs4.BeautifulSoup(show_page_text, "html5lib")
    subnav = show_page_soup.find('nav', class_='show-subnav')
    if subnav:
        for link in subnav.find_all('a'):
            if link.get_text() == "Transcripts":
                return crawler_util.convert_if_relative_url(\
                                    starting_url, link.get('href'))


def get_fox_transcript_date(transcript_page_soup):
    '''
    Given the soup from a transcript, return the date.
    '''

    transcript_info = transcript_page_soup.find('p', class_='speakable')
    date_obj = re.search('This is a rush transcript from [\"“].*?[\"”] ' + \
        '([A-Z][a-z]+) ([0-9]+), ([0-9]{4})', transcript_info.text)
    while not date_obj:
        transcript_info = transcript_info.nextSibling
        date_obj = re.search(\
            'This is a rush transcript from [\"“].*?[\"”] ([A-Z][a-z]+) ' + \
            '([0-9]+), ([0-9]{4})', transcript_info.text)

    year = date_obj.group(3)

    # if year != LIMIT_YEAR:
    #     # continue
    #     return year, None

    airtime = date_obj.group(1)
    if len(str(MONTH_DICT[date_obj.group(1)])) == 1:
        month_str = '0' + str(MONTH_DICT[date_obj.group(1)])
    else:
        month_str = str(MONTH_DICT[date_obj.group(1)])
    if len(date_obj.group(2)) == 1:
        day_str = '0' + date_obj.group(2)
    else:
        day_str = date_obj.group(2)
    # https://stackoverflow.com/questions/43655169/how-to-parse-ldjson-
    # using-python
    airtime = year + '-' + month_str + '-' + day_str

    return int(year), airtime


def crawl_transcripts(starting_url, all_show_transcripts, db_cursor,
    db_connection, title, episode_id_start, speaker_id_start, phrase_id_start,
    index_start):
    '''
    Crawl all transcripts for a given show.

    Inputs:
        starting_url: URL to network page
        all_show_transcripts: list of transcripts
        db_cursor: DB cursor to perform SQL operations
        db_connection: connection to database
        title: title of show
        episode_id_start: (int) current episode ID
        speaker_id_start: (int) current speaker ID
        phrase_id_start: (int) current text clip ID
        index_start: index of transcript in list (to reference
            after clicking "Show More" button)
    '''
    year = None
    for transcript in all_show_transcripts[index_start:]:
        link = crawler_util.convert_if_relative_url(starting_url,
            transcript.find('a').get('href'))

        # Skip over non-transcripts:
        if "transcript" not in link:
            continue

        transcript_page_request = crawler_util.get_request(\
            link)
        transcript_page_text = transcript_page_request.text
        transcript_page_soup = bs4.BeautifulSoup(\
            transcript_page_text, "html5lib")

        year, airtime = get_fox_transcript_date(transcript_page_soup)

        # if year != LIMIT_YEAR:
        #     continue
        # print("AIRTIME is", airtime)
        py_date = datetime.date(year, int(airtime[5:7]), int(airtime[8:10]))
        # print("python date is", py_date)
        if py_date >= MAX_DATE:
            return year, len(all_show_transcripts), episode_id_start, \
                speaker_id_start, phrase_id_start, True
        elif py_date <= MIN_DATE:
            return year, len(all_show_transcripts), episode_id_start, \
                speaker_id_start, phrase_id_start, False
        assert (py_date <= MAX_DATE and py_date >= MIN_DATE)

        meta_data = transcript_page_soup.find("script",
            {"type":"application/ld+json"})
        meta_data_dict = json.loads("".join(meta_data.contents))
        headline = meta_data_dict['headline']

        db_cursor.execute('INSERT INTO episode VALUES(?, ?, ?, ?)',
            (episode_id_start, headline, airtime, title))

        # https://stackoverflow.com/questions/54162988/how-to-find-a-tag-without-specific-attribute-using-beautifulsoup
        transcript_raw_text = transcript_page_soup.find_all('p',
            class_='speakable') + transcript_page_soup.find_all('p', class_=None)

        transcript_text = crawler_util.join_text_chunks(transcript_raw_text)

        begin_flag = '(\n[A-Z][^a-z^\n]+?:|\(BEGIN .*?\)).*'
        end_flag = "Content and Programming Copyright.*"

        speaker_id_start, phrase_id_start = crawler_util.\
            crawl_transcript(transcript_text, begin_flag, end_flag,
                episode_id_start, speaker_id_start, phrase_id_start, db_cursor)

        db_connection.commit()
        episode_id_start += 1

    return year, len(all_show_transcripts), episode_id_start, \
        speaker_id_start, phrase_id_start, True


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
    
    # https://pythonspot.com/selenium-click-button/
    driver = webdriver.Firefox()
    driver.get(transcript_link)
    xpath_elems = driver.find_element_by_xpath(\
        '//*[@id="wrapper"]/div[2]/div[3]/div/main/section/div')
    articles_soup = bs4.BeautifulSoup(xpath_elems.get_attribute('innerHTML'),
        "html5lib")
    all_show_transcripts = articles_soup.find_all('article', class_='article')

    # # Close CDC warning if any
    # elem_popup = driver.find_element_by_xpath(\
    #     '//*[@id="wrapper"]/div[2]/div[4]/div/div/a')
    # if elem_popup:
    #     elem_popup.click()
    #     time.sleep(1)

    index_start = 0
    most_recent_year = LIMIT_YEAR
    while most_recent_year >= LIMIT_YEAR:
        most_recent_year, index_start, episode_id_start, speaker_id_start, \
            phrase_id_start, within_date_range = crawl_transcripts(starting_url,
            all_show_transcripts, db_cursor, db_connection,
            title, episode_id_start, speaker_id_start, phrase_id_start, index_start)

        if not within_date_range:
            break

        # For shows that have no actual transcripts in first 10, skip show
        if most_recent_year is None:
            break

        elem = driver.find_element_by_xpath(\
            "//div[@class='button load-more js-load-more']/a")
        elem.click()
        time.sleep(2.5)
        xpath_elems = driver.find_element_by_xpath(\
            '//*[@id="wrapper"]/div[2]/div[3]/div/main/section/div')
        articles_soup = bs4.BeautifulSoup(xpath_elems.get_attribute(\
            'innerHTML'), "html5lib")
        all_show_transcripts = articles_soup.find_all('article',
            class_='article')

    driver.close()

    if episode_id_start > episode_id_init:
        db_cursor.execute('INSERT INTO show VALUES(?, ?)',
            (title, 'Fox')).fetchall()

    return episode_id_start, speaker_id_start, phrase_id_start


def go(db_cursor, db_connection, speaker_id_start=0, episode_id_start=0,
       phrase_id_start=0):
    '''
    Crawls the Fox transcripts site and updates database of transcripts,
    speakers, titles, shows, and episodes.
    This function modifies the input database.

    Inputs:
        db_cursor, db_connection: cursor and connection to database
        speaker_id_start, episode_id_start, phrase_id_start: (ints) numbers at
            which to start speakers, episodes, and phrases

    Outputs:
        episode_id_start, speaker_id_start, phrase_id_start: (ints) updated
            starting points for the next transcript to be crawled

    '''

    starting_url = "https://www.foxnews.com/shows"

    # Create soup object from starting page
    starting_request = crawler_util.get_request(starting_url)
    starting_text = starting_request.text
    starting_soup = bs4.BeautifulSoup(starting_text, "html5lib")

    # Get list of shows to loop through
    show_info_list = starting_soup.find_all('li', class_='showpage')
    for show in show_info_list[0:1]:
        title = show.find('h2', class_='title').get_text().strip()
        print(title)

        transcript_link = get_show_transcripts_page(show, starting_url)
            
        # If show has transcripts available, scrape episodes
        if transcript_link:

            episode_id_start, speaker_id_start, phrase_id_start = crawl_show(\
                starting_url, transcript_link, db_cursor, db_connection,
                title, episode_id_start, speaker_id_start, phrase_id_start)
            db_connection.commit()

    return speaker_id_start, episode_id_start, phrase_id_start

