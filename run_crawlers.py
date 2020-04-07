'''
CAPP 30122: Run all crawlers

Charlie Sheils
'''

import sqlite3
import crawler_cnn
import crawler_msnbc
import crawler_fox


DATABASE_FILENAME = 'news_db_2020.sqlite3'
LIMIT_YEAR = 2020


def go(db_name=DATABASE_FILENAME):
    '''
    This function modifies the database that is passed as a parameter to the
    function.
    '''

    conn = sqlite3.connect(db_name)
    db_cursor = conn.cursor()

    # Clear out database before running crawlers
    db_cursor.execute('DELETE FROM show')
    db_cursor.execute('DELETE FROM episode')
    db_cursor.execute('DELETE FROM speaker')
    db_cursor.execute('DELETE FROM title')
    db_cursor.execute('DELETE FROM transcript')

    # Run web crawlers & input results into database
    speaker_id_start = 0
    episode_id_start = 0
    phrase_id_start = 0
    speaker_id_start, episode_id_start, phrase_id_start = crawler_fox.go(\
        db_cursor, conn, speaker_id_start, episode_id_start, phrase_id_start)
    speaker_id_start, episode_id_start, phrase_id_start = crawler_cnn.go(\
        db_cursor, conn, speaker_id_start, episode_id_start, phrase_id_start)
    speaker_id_start, episode_id_start, phrase_id_start = crawler_msnbc.go(\
        db_cursor, conn, speaker_id_start, episode_id_start, phrase_id_start)

    conn.commit()
    conn.close()
