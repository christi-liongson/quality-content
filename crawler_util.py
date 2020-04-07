"""
CAPP 30122: Final Project Utility Functions
"""

import bs4
import urllib
import requests
import os
import re

VIDEO_START = "[[(](BEGIN|START) (VIDEO|VOICE|AUDIO).*?[])]"
VIDEO_END = "[[(]END (VIDEO|VOICE|AUDIO).*?[])]"

OTHER_SINGLES = ["[[(]CROSSTALK.*?[])]?", "[[(]LAUGHTER[])]",
                 "[[(]INAUDIBLE[])]", "[[(]UNINTELLIGIBLE[])]",
                 "[[(]COMMERCIAL BREAK[])]", "[[(]APPLAUSE[])]",
                 "[[(]CHEER.*? AND APPLAUSE[])]", "[[(]CHANTING[])]"
                 "[[(]MUSIC PLAYING[])]", "[[(]MUSIC.*?[])]",
                 "\[[0-9]{2}:[0-9]{2}:[0-9]{2}\]", " \(voice[- ]over\)",
                 " \(on camera\)", " \(through translator\)"]

HOSTS_DICT = {'MADDOW': 'RACHEL MADDOW',
              "O'DONNELL": "LAWRENCE O'DONNELL",
              'CARLSON': 'TUCKER CARLSON',
              'BAIER': 'BRET BAIER',
              'HANNITY': 'SEAN HANNITY',
              'GUTFELD': 'GREG GUTFELD',
              'MACCALLUM': 'MARTHA MACCALLUM',
              'INGRAHAM': 'LAURA INGRAHAM',
              'COOPER': 'ANDERSON COOPER'}

TITLE_TYPO_DICT = {"D HENRY, FOX NEWS HOST":
                        {'name_clean': "ED HENRY",
                        'speaker_title': "FOX NEWS HOST"},
    "EZEKIEL, EMANUEL, FORMER HEALTH POLICY ADVISOR, OBAMA WHITE HOUSE":
        {'name_clean': "EZEKIEL EMANUEL",
        'speaker_title': "FORMER HEALTH POLICY ADVISOR, OBAMA WHITE HOUSE"},
    'SEN. ANGUS KING (I-ME) INTELLIGENCE COMMITTEE':
        {'name_clean': "ANGUS KING",
        'speaker_title': "INTELLIGENCE COMMITTEE"},
    "UNIDENTIFIED MALE SAINT-NICOLAS-LA-CHAPELLE":
        {'name_clean': "UNIDENTIFIED MALE",
        'speaker_title': "SAINT-NICOLAS-LA-CHAPELLE, FRANCE"},
    "UNIDENTIFIED MALE SAINT-NICOLAS-LA-CHAPELLE, FRANCE":
        {'name_clean': "UNIDENTIFIED MALE",
        'speaker_title': "SAINT-NICOLAS-LA-CHAPELLE, FRANCE"}}


TYPO_NAME_DICT = {"ALEXANDRA OCASIO-CORTEZ": "ALEXANDRIA OCASIO-CORTEZ",
                  "ALEXANDRIAOCASIO-CORTEZ": "ALEXANDRIA OCASIO-CORTEZ",
                 "KRISTEN POWERS": "KIRSTEN POWERS",
                 "BRYON YORK": "BYRON YORK",
                 "SOLOMON WISENBERG": "SOL WISENBERG",
                 "PHIL BUMP": "PHILIP BUMP",
                 "MIKE BLOOMBERG": "MICHAEL BLOOMBERG",
                 "JOSEPH BIDEN": "JOE BIDEN",
                 "CHARLES SCHUMER": "CHUCK SCHUMER",
                 "TAKE TAPPER": "JAKE TAPPER",
                 "LAURAN CHOOLJIAN": "LAUREN CHOOLJIAN",
                 "EZEKIEL EMANUEL": "ZEKE EMANUEL",
                 "BRIANNE KEILAR": "BRIANNA KEILAR",
                 "JANNETTE NESHEIWAT": "JANETTE NESHEIWAT",
                 "LOVEGROVEE": "LOVEGROVE",
                 "BAIR": "BAIER",
                 'HANNTY': 'HANNITY',
                 "EMES SOTO RIVERA": "ERNES SOTO RIVERA",
                 "UNIDENTIFIED MALE TRANSLATED": "UNIDENTIFIED MALE"}


NAME_CONFLICTS = {'HOLMES': {'names': {'MICHAEL HOLMES', 'KRISTEN HOLMES'},
                                'match': 'MICHAEL HOLMES'},
                 'PEREZ': {'names': {'EVAN PEREZ', 'TOM PEREZ'},
                           'match': 'TOM PEREZ'},
                 'ROBERTS': {'names': {'JOHN ROBERTS', 'PAT ROBERTS'},
                             'match': 'JOHN ROBERTS'},
                 'CUOMO': {'names': {'CHRIS CUOMO', 'ANDREW CUOMO'},
                           'match': 'CHRIS CUOMO'},
                 'JONES': {'names': {'ATHENA JONES', 'VAN JONES'},
                           'match': 'VAN JONES'},
                 'KING': {'names': {'JOHN KING', 'ANGUS KING'},
                          'match': 'JOHN KING'},
                 'TUCHMAN': {'names': {'LINDSAY TUCHMAN', 'GARY TUCHMAN'},
                             'match': 'GARY TUCHMAN'},
                 'WHITE': {'names': {'JOANNE WHITE', 'MICHAEL WHITE'},
                           'match': 'MICHAEL WHITE'},
                 'GHOSN': {'names': {'CAROLE GHOSN', 'CARLOS GHOSN'},
                           'match': 'CARLOS GHOSN'},
                 'KIM': {'names': {'SIMON KIM', 'DUHYEN KIM'},
                         'match': 'DUHYEN KIM'},
                 'KING': {'names': {'JOHN KING', 'ANGUS KING'},
                            'match': 'JOHN KING'},
                 'TURNER': {'names': {'NINA TURNER', 'NICHELLE TURNER'},
                            'match': 'NINA TURNER'},
                 'OBAMA': {'names': {'BARACK OBAMA', 'MICHELLE OBAMA'},
                           'match': 'BARACK OBAMA'},
                 'BIDEN': {'names': {'JOE BIDEN', 'JILL BIDEN'},
                           'match': 'JOE BIDEN'},
                 'JOHNSON': {'names': {'RICHARD JOHNSON', 'THARON JOHNSON'},
                             'match': 'RICHARD JOHNSON'},
                 'STEWART': {'names': {'IAN STEWART', 'ANNA STEWART'},
                             'match': 'ANNA STEWART'},
                 'MITCHELL': {'names': {'JEREZ MITCHELL', 'JOHN MITCHELL'},
                              'match': 'JOHN MITCHELL'}}

STARTS_ENDS_TITLES = ["PRESIDENTIAL CANDIDATE", "MAYOR", "CHIEF JUSTICE",
                      "DR", "SENATOR", "PRESIDENT",
                      "PRESIDENT OF THE UNITED STATES"]


def clean_and_filter_text(transcript_text, begin_flag, end_flag,
                          video_start=VIDEO_START, video_end=VIDEO_END,
                          other_singles=OTHER_SINGLES):
    '''
    Given raw transcript text, return list of cleaned text, dictionary of
        all speakers within text, and dictionary of filtered speakers within
        text.

    Inputs:
        transcript_text: raw transcript text
        begin_flag: regular expression indicating beginning of speech
        end_flag: regular expression indicating end of speech
        video_start: regular expression matching beginning of video or audio
            clip (defaulting to VIDEO_START)
        video_end: regular expression matching end of video or audio
            clip (defaulting to VIDEO_END)
        other_singles: Other words and expressions to remove (defaulting
            to OTHER_SINGLES)
    '''

    text_find = '\n[A-Z][^a-z^\n]+?:'
    speaker_find = '\n([A-Z][^a-z^\n]+?):'

    clean_text = transcript_text
    
    #clean Unicode characters
    clean_text = re.sub("\\xa0", "\n", clean_text)

    #replace slanted quotes with straight quotes
    clean_text = re.sub("[`’]", "'", clean_text)
    clean_text = re.sub('[“”]', '"', clean_text)

    # Remove anything between "<" and ">"
    clean_text = re.sub("<.+?>", "", clean_text, flags=re.DOTALL)

    # Remove text following end of transcript
    clean_text = re.sub(end_flag, "", clean_text, flags=re.DOTALL)

    # Remove text before beginning of transcript
    match1_obj = re.search(begin_flag, clean_text, flags=re.DOTALL)

    if match1_obj is None:
        # print("THIS TRANSCRIPT IS PROPER CASE")
        text_find = text_find.replace('^a-z', '').replace('BEGIN', 'begin')
        speaker_find = speaker_find.replace('^a-z', '')
        begin_flag = begin_flag.replace('^a-z', '')
        match1_obj = re.search(begin_flag, clean_text, flags=re.DOTALL)
    
    if match1_obj is None:
        # print("THIS TRANSCRIPT HAS NO TEXT")
        return [], [], []


    clean_text2 = match1_obj.group(0)
    
    for term in other_singles + [str.lower(single) for single in other_singles]:
        clean_text2 = re.sub(term, "", clean_text2)
    assert "(CROSSTALK" not in clean_text2
    assert "(crosstalk" not in clean_text2
    assert "(COMMERCIAL BREAK)" not in clean_text2
    
    all_speakers = re.findall(speaker_find, clean_text2)

    clean_text2 = re.sub("{0}.+?{1}".format(\
        "[[(](BEGIN|START) (VIDEO|VOICE|AUDIO)[ ]?TAPE.*?[])]",
        "[[(]END (VIDEO|VOICE)[ ]?TAPE.*?[])]"),
        "", clean_text2, flags=re.DOTALL)
    clean_text2 = re.sub("{0}.+?{1}".format(\
        "[[(](BEGIN|START) (VIDEO|VOICE|AUDIO)[ ]?CLIP[S]?.*?[])]",
        "[[(]END (VIDEO|VOICE)[ ]?CLIP[S]?.*?[])]"),
        "", clean_text2, flags=re.DOTALL)
    while re.search(VIDEO_START + ".*?" + VIDEO_END, clean_text2,
                    flags=re.DOTALL) is not None:
        clean_text2 = re.sub("{0}.+?{1}".format(VIDEO_START, VIDEO_END),
            "", clean_text2, flags=re.DOTALL)
    clean_text2 = re.sub("{0}.+?{1}".format(video_start.lower(), video_end.lower()),
        "", clean_text2, flags=re.DOTALL)


    for term in [VIDEO_START, VIDEO_END] + \
                [str.lower(single) for single in [VIDEO_START, VIDEO_END]]:
        clean_text2 = re.sub(term, "", clean_text2)

    filtered_speakers = re.findall(speaker_find, clean_text2)

    filtered_text_list = re.split(text_find, clean_text2)[1:]
    filtered_text_list2 = []
    for chunk in filtered_text_list:
        chunk_clean = re.sub("\n", " ", chunk).strip()
        chunk_clean = " ".join(chunk_clean.split())
        filtered_text_list2.append(chunk_clean)
    filtered_text_list = filtered_text_list2

    assert len(filtered_text_list) == len(filtered_speakers), "lengths differ"

    return all_speakers, filtered_speakers, filtered_text_list


def join_text_chunks(transcript_raw_text):
    '''
    Combine text blocks into one, inputting newline characters when a new
    speaker begins.

    Inputs:
        transcript_raw_text: list of text blocks from transcript

    Outputs: (str) Full transcript text, with newline characters where
        appropriate.
    '''

    transcript_final_text = ""
    for chunk in transcript_raw_text:
        text = chunk.get_text().strip()
        if (text and
                re.search("[a-z]", text) is None and
                not text.startswith("(") and
                not text.startswith("[") and
                not text.startswith("END") and
                ":" not in text):
            transcript_final_text += text + " "
        else:
            transcript_final_text += text + '\n'

    return transcript_final_text


def check_conflict_dict(name_clean, name_matches):
    '''
    Make manual corrections for when two people with the same last name appear
    in the same transcript and both people are referred to by the same last
    name.

    Inputs:
        name_clean: last name to be reconciled
        name_matches: set of full names to which last name matches

    Outputs: (str) updated set of name matches
    '''
    if (name_clean in NAME_CONFLICTS and
        NAME_CONFLICTS[name_clean]['names'] == name_matches):
        return {NAME_CONFLICTS[name_clean]['match']}

    return name_matches


def create_speaker_dict(all_speakers, filtered_speakers):
    '''
    Given a list of all the speakers in the text, consolidate into speakers
    with full names, using a series of assignment rules described in comments
    below.

    Inputs:
        all_speakers: list of all speakers as they appear in the text of the
            transcript
        filtered_speakers: list of speakers that do not appear within video
            clips (to help in case of name conflicts)

    Outputs: speakers_dict: nested dictionary of the following format:
        {'<official name for database>': {'title': '<title for database',
                                          'aliases': set of aliases that
                                                appear in transcript}}
    '''

    speakers_dict = {}
    for speaker in all_speakers:

        if "," in speaker:
            [name, speaker_title] = str.upper(speaker).split(',', 1)
            name_clean = clean_name(name)
        else:
            name_clean = str.upper(clean_name(speaker))
            speaker_title = ""
        
        
        # Remove titles that appear in name that cause name conflicts
        for title in STARTS_ENDS_TITLES:
            if name_clean.startswith(title + " "):
                name_clean = name_clean[len(title):].strip()
            elif name_clean.endswith(" " + title):
                name_clean = name_clean[:len(name_clean) - len(title)].strip()

        # Correct typos in raw speaker name that cause name conflicts
        if speaker in TITLE_TYPO_DICT:
            name_clean = TITLE_TYPO_DICT[speaker]['name_clean']
            speaker_title = TITLE_TYPO_DICT[speaker]['speaker_title']

        # Correct typos in cleaned speaker name that cause name conflicts
        name_clean = TYPO_NAME_DICT.get(name_clean, name_clean)

        # Additional manual name conflicts
        if speaker == "MOOSE" and "JEANNE MOOS" in speakers_dict:
            name_clean = "MOOS"
        if (speaker == "ROBERTSON" and
            "TRAV ROBERTSON, CHAIRMAN, SOUTH CAROLINA DEMOCRATIC PARTY" in all_speakers and
            "NIC ROBERTSON, CNN INTERNATIONAL DIPLOMATIC EDITOR" in all_speakers):
            name_clean = "TRAV ROBERTSON"


        # Create set of all preceding name matches for the current name
        name_matches = {word for word in speakers_dict if name_clean in word}

        # If multiple name matches, correct if it's because of initials
        if len(name_matches) > 1 and re.search("^[A-Z]\. [A-Z]+", speaker) is not None:
            first_initial = re.search("(^[A-Z])\. [A-Z]+", speaker).group(1)
            names_rvsd = set()
            for name in name_matches:
                if name.startswith(first_initial):
                    names_rvsd.add(name)
            name_matches = names_rvsd

        # If still multiple name matches, limit to those starting with or
        # ending with the name being considered.
        if len(name_matches) > 1:
            names_rvsd = set()
            for match in name_matches:
                if (match.startswith(name_clean + " ") or
                        match.endswith(" " + name_clean)):
                    names_rvsd.add(match)
            name_matches = names_rvsd

        # If still multiple names, filter on those that just end with the name
        # being considered.
        if len(name_matches) > 1:
            names_rvsd = {key for key in name_matches if \
                key.endswith(" " + name_clean)}
            name_matches = names_rvsd

        # If still multiple names, correct for manual name conflicts
        if len(name_matches) > 1:
            name_matches = check_conflict_dict(name_clean, name_matches)
            
        # If still multiple names, filter out those only in video clips
        if len(name_matches) > 1:
            names_rvsd = set()
            for name in filtered_speakers:
                if (name_clean in str.upper(name) and
                    clean_name(str.upper(name).split(',', 1)[0]) in name_matches):
                    names_rvsd.add(clean_name(name.split(',', 1)[0]))
            name_matches = names_rvsd

        assert len(name_matches) <= 1, "2 names, %r" % speaker + str(name_matches)

        # Once there is one name match, assign the raw name to the dictionary aliases
        if name_matches:
            name_clean = str.upper(name_matches.pop())
        else:
            speakers_dict[name_clean] = {'title': speaker_title.strip(),
                                         'aliases': set()}
        speakers_dict[name_clean]['aliases'] = speakers_dict[name_clean]['aliases'].union({str.upper(speaker)})

        # If the current name is a full name, attribute any previous
        # single-word name matches to this name (rare)
        if len(name_clean.split()) == 2:
            names_to_remove = []
            for name in speakers_dict:
                if len(name.split()) == 1 and name in name_clean:
                    # print("NEW going to replace unusual one name with full name", name, name_clean)
                    speakers_dict[name_clean]['aliases'] = speakers_dict[name_clean]['aliases'].union(speakers_dict[name]['aliases'])
                    names_to_remove.append(name)
            for name in names_to_remove:
                # print("REMOVING THIS ITEM FROM SPEAKER DICT", name)
                del speakers_dict[name]

    # Replace show host names with full names if a different person with the
    # same last name is not present
    for last_name, full_name in HOSTS_DICT.items():
        if last_name in speakers_dict:
            # https://stackoverflow.com/questions/4406501/change-the-name-of-a-key-in-dictionary
            print('UPDATING HOST', last_name, full_name, speakers_dict[last_name])
            speakers_dict[full_name] = speakers_dict.pop(last_name)
            print('updated dict now', speakers_dict[full_name])

    return speakers_dict

def create_alias_dict(speakers_dict, filtered_speakers):
    '''
    Given the speaker dictionary created from the transcript, create a
    parallel dictionary mapping aliases to official names for the database.
    In case the same alias is attributed to multiple official names, choose
    the name that appears outside of video clips.

    Inputs:
        speakers_dict: dictionary of speakers in transcript (created in
            create_speakers_dict)
        filtered_speakers: list of speakers that appear outside video clips

    Outputs: dictionary mapping aliases to official names
    '''
    alias_dict = {}
    for official_name, attributes in speakers_dict.items():
        for al in attributes['aliases']:
            if al in alias_dict:
                # print("alias already in dict, name1, name2", [al, alias_dict[al], official_name])
                filtered_speakers_clean_names = [clean_name(name.split(',', 1)[0]) for name in filtered_speakers]
                if alias_dict[al] in filtered_speakers_clean_names:
                    assert official_name not in filtered_speakers_clean_names
                    continue
                else:
                    assert official_name in filtered_speakers_clean_names
                    # print("replacing name in video only with name outside video")
            alias_dict[al] = official_name

    return alias_dict


def update_db_speakers_and_titles(speakers_dict, speaker_id_start, db_cursor):
    '''
    Load all speakers appearing in the transcript into the
    database.

    Inputs:
        speakers_dict: dictionary of speakers in transcript (created in
            create_speakers_dict)
        speaker_id_start: (int) current speaker ID
        db_cursor: cursor to perform SQL statements on the database
    '''

    for speaker in speakers_dict:
        id = db_cursor.execute('''SELECT speaker_id FROM speaker
                                  WHERE speaker_name = ?''',
                               (speaker,)).fetchall()

        if not id:
            id = speaker_id_start
            speaker_id_start += 1

            # Add speaker to speaker & title table
            db_cursor.execute('INSERT INTO speaker VALUES(?, ?)',
                (id, speaker))

            if speakers_dict[speaker]['title']:
                db_cursor.execute('INSERT INTO title VALUES(?, ?)',
                    (id, speakers_dict[speaker]['title']))


        else:
            assert len(id) == 1

            # Query title table to see if title is already in table
            existing_titles = db_cursor.execute('''SELECT speaker_title
                                            FROM title
                                            WHERE speaker_id = ?''',
                               (id[0][0],)).fetchall()

            existing_titles_list = []
            for title_tuple in existing_titles:
                existing_titles_list.append(title_tuple[0])

            if (speakers_dict[speaker]['title'] and 
                speakers_dict[speaker]['title'] not in existing_titles_list):
                db_cursor.execute('INSERT INTO title VALUES(?, ?)',
                    (id[0][0], speakers_dict[speaker]['title']))

    return speaker_id_start


def update_db_transcripts(filtered_text_list, filtered_speakers, alias_dict, 
                          db_cursor, episode_id_start, phrase_id_start):
    '''
    Load all text clips (after removing video clips), attributed to each
    speaker, into the transcript table in the database.

    Inputs:
        filtered_text_list: List of text clips, not including video clips
        filtered_speakers: List of speakers corresponding to text clips
        alias_dict: dictionary mapping speakers to their official name
        db_cursor: cursor to perform SQL statements on the database
        episode_id_start: (int) current episode ID
        phrase_id_start: (int) current text clip ID
    '''

    for i, speaker_raw in enumerate(filtered_speakers):
        official_name = alias_dict[str.upper(speaker_raw)]
        id = db_cursor.execute('''SELECT speaker_id FROM speaker
                                  WHERE speaker_name = ?''',
                               (official_name,)).fetchall()
        assert len(id) == 1
        db_cursor.execute('INSERT INTO transcript VALUES(?, ?, ?, ?)',
            (phrase_id_start, episode_id_start, filtered_text_list[i], id[0][0]))
        phrase_id_start += 1

    return phrase_id_start


def clean_name(name):
    '''
    Given a name with punctuation and other titles, return only the
    words that are not titles.

    Inputs: raw name
    Outputs: cleaned name
    '''
    clean_name = []
    for word in name.split():
        name_sub = re.search("^[A-Za-z][A-Za-z'-]+$", word)
        if name_sub:
            clean_name.append(name_sub.group(0))
    return ' '.join(clean_name)


def crawl_transcript(transcript_text, begin_flag, end_flag, episode_id_start,
            speaker_id_start, phrase_id_start, db_cursor):
    '''
    Given the text of a transcript, load its information into the database.

    Inputs:
        transcript_text: raw transcript text
        begin_flag: regular expression indicating beginning of speech
        end_flag: regular expression indicating end of speech
        episode_id_start: (int) current episode ID
        speaker_id_start: (int) current speaker ID
        phrase_id_start: (int) current text clip ID
        db_cursor: cursor to perform SQL statements on the database

    Outputs: updated speaker_id and phrase_id after processing transcript

    '''
    all_speakers, filtered_speakers, filtered_text_list = clean_and_filter_text(\
        transcript_text, begin_flag, end_flag)

    if not all_speakers and not filtered_speakers and not filtered_text_list:
        return speaker_id_start, phrase_id_start

    speakers_dict = create_speaker_dict(all_speakers, filtered_speakers)
    alias_dict = create_alias_dict(speakers_dict, filtered_speakers)

    speaker_id_start = update_db_speakers_and_titles(\
        speakers_dict, speaker_id_start, db_cursor)

    phrase_id_start = update_db_transcripts(filtered_text_list,
        filtered_speakers, alias_dict, db_cursor, episode_id_start,
        phrase_id_start)

    return speaker_id_start, phrase_id_start


## Code below is provided from pa1 in util.

def get_request(url):
    '''
    Open a connection to the specified URL and if successful
    read the data.

    Inputs:
        url: must be an absolute URL

    Outputs:
        request object or None

    Examples:
        get_request("http://www.cs.uchicago.edu")
    '''

    if is_absolute_url(url):
        try:
            r = requests.get(url)
            if r.status_code == 404 or r.status_code == 403:
                r = None
        except Exception:
            # fail on any kind of error
            r = None
    else:
        r = None

    return r


def is_absolute_url(url):
    '''
    Is url an absolute URL?
    '''
    if url == "":
        return False
    return urllib.parse.urlparse(url).netloc != ""


def convert_if_relative_url(current_url, new_url):
    '''
    Attempt to determine whether new_url is a relative URL and if so,
    use current_url to determine the path and create a new absolute
    URL.  Will add the protocol, if that is all that is missing.

    Inputs:
        current_url: absolute URL
        new_url:

    Outputs:
        new absolute URL or None, if cannot determine that
        new_url is a relative URL.

    Examples:
        convert_if_relative_url("http://cs.uchicago.edu", "pa/pa1.html") yields
            'http://cs.uchicago.edu/pa/pa.html'

        convert_if_relative_url("http://cs.uchicago.edu", "foo.edu/pa.html")
            yields 'http://foo.edu/pa.html'
    '''
    if new_url == "" or not is_absolute_url(current_url):
        return None

    if is_absolute_url(new_url):
        return new_url

    parsed_url = urllib.parse.urlparse(new_url)
    path_parts = parsed_url.path.split("/")

    if len(path_parts) == 0:
        return None

    ext = path_parts[0][-4:]
    if ext in [".edu", ".org", ".com", ".net"]:
        return "http://" + new_url
    elif new_url[:3] == "www":
        return "http://" + new_path
    else:
        return urllib.parse.urljoin(current_url, new_url)
