"""
Query the database to get the relevant information for standard visuals.
Then produce the visuals!
"""

import sqlite3
import pandas as pd
import matplotlib
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
plt.rcdefaults()
matplotlib.use('TkAgg')

DATABASE_FILENAME = ('/home/student/'
                     'capp30122-win-20-casheils-christiannenic-kshaevel/'
                     'final_project/news_db_2020.sqlite3')
NETWORK_COLORS = {'CNN': 'y',
                  'MSNBC': 'b',
                  'Fox': 'r'}

def retrieve_data(args_from_ui, not_host=False):
    '''
    Takes a dictionary containing search criteria and returns courses
    that match the criteria.  The dictionary will contain some of the
    following fields:

      - speaker_name: string
      - speaker_title: string
      - datetime_start/datetime_end: datetime
      - network: string
      - show_name: string
      - term: string

    Returns a pair: an ordered list of attribute names and a list the
     containing query results.  Returns ([], []) when the dictionary
     is empty.
    '''

    if not args_from_ui or assert_valid_input(args_from_ui):
        return None

    query_dict = {'speaker_name': 'AND sp.speaker_name = ? ',
                  'speaker_title': 'AND sp.speaker_name IN '
                                   '(SELECT DISTINCT sp.speaker_name '
                                   'FROM title AS ti, speaker AS sp '
                                   'WHERE ti.speaker_title LIKE ? AND '
                                   'sp.speaker_id = ti.speaker_id'
                                   ') ',
                  'datetime_start': 'AND e.airtime >= ? ',
                  'datetime_end': 'AND e.airtime <= ? ',
                  'network_name': 'AND sh.network_name IN ({}) ',
                  'show_name': 'AND e.show_name = ? ',
                  'term': 'AND tr.words LIKE ? '}

    conn = sqlite3.connect(DATABASE_FILENAME)
    c = conn.cursor()

    query_select = ('SELECT sp.speaker_name, '
                    'sp.speaker_id, '
                    'tr.words, '
                    'e.show_name, '
                    'e.episode_id, '
                    'e.airtime, '
                    'sh.network_name ')

    query_from = ('FROM show AS sh, '
                  'episode AS e, '
                  'speaker AS sp, '
                  'transcript AS tr ')

    query_where = ('WHERE tr.speaker_id = sp.speaker_id AND '
                   'tr.episode_id = e.episode_id AND '
                   'e.show_name = sh.show_name ')

    parameters = []
    for spec, parameter in args_from_ui.items():
        if spec == 'term':
            query_where += query_dict[spec] * len(parameter)
            for entry in parameter:
                parameters += [enclose_in_percents(entry)]
        else:
            if spec == 'speaker_title':
                parameter = enclose_in_percents(parameter)
            query_where += (add_question_marks(query_dict[spec], len(parameter))
                            if '({})' in query_dict[spec]
                            else query_dict[spec])
            parameters += parameter if isinstance(parameter, list) else [parameter]

    if not_host:
        query_where += ('AND sp.speaker_name NOT IN '
                        '(SELECT DISTINCT sp.speaker_name '
                        'FROM title as ti, speaker AS sp '
                        'WHERE (ti.speaker_title like "%host%" '
                        'OR ti.speaker_title like "%anchor%") '
                        'AND sp.speaker_id = ti.speaker_id) ')

    result = pd.DataFrame(c.execute(query_select +
                                    query_from +
                                    query_where +
                                    'COLLATE NOCASE' +
                                    ";",
                                    parameters).fetchall())
    if result.empty:
        return None
    result.columns = get_header(c)
    result['airtime'] = (pd.to_datetime(result['airtime'].str[:10],
                                        infer_datetime_format=True)
                                        .dt.strftime('%m/%d/%Y'))
    conn.close()

    return result


def speaker_summary(result):
    '''
    Creates and shows a bar chart showing most common shows in the dataset.
    '''

    counts = result.groupby(['show_name', 'network_name']).episode_id.nunique().sort_values()

    show_names = [counts.index[x][0] for x in range(len(counts))]

    colors = [NETWORK_COLORS[counts.index[x][1]] for x in range(len(counts))]

    plt.barh(show_names, counts.tolist(), color=colors, edgecolor='black')

    for index, show in enumerate(show_names):
        plt.text(counts.tolist()[index] + .1, show, str(counts.tolist()[index]))

    legend_handles = []
    for network, color in NETWORK_COLORS.items():
        legend_handles.append(mpatches.Patch(color=color, label=network))
    plt.legend(handles=legend_handles, loc='best')

    plt.title('Most Frequent Show Appearances for\n'
              + result.iloc[0].speaker_name, fontweight='bold')
    plt.xlabel('Number of Appearances')
    plt.tight_layout()

    plt.show()


def most_frequent_speakers(result, bar_color):
    '''
    One-time script to produce charts of the most common speakers by network.
    '''
    speakers_to_exclude = ['UNIDENTIFIED MALE', 'UNIDENTIFIED FEMALE']
    counts = (result.loc[result.speaker_name.str.contains(' '), :]
              .loc[~result.speaker_name.isin(speakers_to_exclude)]
              .groupby(['speaker_name']).size().sort_values().tail(10))

    speaker_names = [counts.index[x] for x in range(len(counts))]

    plt.barh(speaker_names, counts.tolist(), color=bar_color, edgecolor='black')

    for index, speaker in enumerate(speaker_names):
        plt.text(counts.tolist()[index] + .1,
                 speaker,
                 str(counts.tolist()[index]))

    plt.title('Most Common Speakers for\n'
              + result.iloc[0].network_name, fontweight='bold')
    plt.xlabel('Number of Times Spoke')
    plt.tight_layout()

    plt.show()


def most_verbose(result):
    '''
    One-time script to produce charts of the most verbose speakers.
    '''
    speakers_to_exclude = ['UNIDENTIFIED MALE',
                           'UNIDENTIFIED FEMALE',
                           'PAT PHILBIN',
                           'MALE SPEAKER',
                           'FEMALE SPEAKER',
                           'UNIDENTIFIED CLERK',
                           'SENATE CLERK']
    result = (result.loc[result.speaker_name.str.contains(' '), :]
                    .loc[~result.speaker_name.isin(speakers_to_exclude)])
    result['length'] = result.loc[:, 'words'].str.split().str.len()

    #plot verbose networks
    network_verbosity = (result.groupby('network_name').length
                         .agg('mean').round(2).sort_values())
    network_names = [network_verbosity.index[x]
                     for x in range(len(network_verbosity))]

    colors = [NETWORK_COLORS[network_verbosity.index[x]]
              for x in range(len(network_verbosity))]
    plt.barh(network_names, network_verbosity.tolist(),
             color=colors, edgecolor='black')

    for index, network in enumerate(network_names):
        plt.text(network_verbosity.tolist()[index] + .1,
                 network,
                 str(network_verbosity.tolist()[index]))

    plt.title('Verbosity by Network', fontweight='bold')
    plt.xlabel('Average words per statement')
    plt.tight_layout()
    plt.show()

    #plot verbose shows
    show_verbosity = (result.groupby(['show_name', 'network_name']).length
                      .agg('mean').round(2).sort_values())
    show_names = [show_verbosity.index[x][0]
                  for x in range(len(show_verbosity))]

    colors = [NETWORK_COLORS[show_verbosity.index[x][1]]
              for x in range(len(show_verbosity))]
    plt.barh(show_names, show_verbosity.tolist(),
             color=colors, edgecolor='black')

    for index, show in enumerate(show_names):
        plt.text(show_verbosity.tolist()[index] + .1,
                 show,
                 str(show_verbosity.tolist()[index]),
                 fontsize=8)

    legend_handles = []
    for network, color in NETWORK_COLORS.items():
        legend_handles.append(mpatches.Patch(color=color, label=network))
    plt.legend(handles=legend_handles, loc='best')

    plt.title('Verbosity by Show', fontweight='bold')
    plt.xlabel('Average words per statement')
    plt.tight_layout()
    plt.show()

    #plot verbose speakers
    instance_counts = result.groupby('speaker_name').size()
    common_speakers = [instance_counts.index[x]
                       for x in range(len(instance_counts))
                       if instance_counts[x] >= 10]
    result = result.loc[result.speaker_name.isin(common_speakers)]
    speaker_verbosity = (result.groupby('speaker_name').length
                         .agg('mean').round(2).sort_values().tail(20))
    speaker_names = [speaker_verbosity.index[x]
                     for x in range(len(speaker_verbosity))]

    plt.barh(speaker_names, speaker_verbosity.tolist(), edgecolor='black')

    for index, speaker in enumerate(speaker_names):
        plt.text(speaker_verbosity.tolist()[index] + .1,
                 speaker,
                 str(speaker_verbosity.tolist()[index]),
                 fontsize=8)

    #least verbose speakers
    speaker_verbosity = (result.groupby('speaker_name').length
                         .agg('mean').round(2).sort_values().head(20))
    speaker_names = [speaker_verbosity.index[x]
                     for x in range(len(speaker_verbosity))]

    plt.title('Most Verbose Speakers\n(must have spoken 10+ times)',
              fontweight='bold')
    plt.xlabel('Average words per statement')
    plt.tight_layout()
    plt.show()

    plt.barh(speaker_names, speaker_verbosity.tolist(), edgecolor='black')

    for index, speaker in enumerate(speaker_names):
        plt.text(speaker_verbosity.tolist()[index] + .1,
                 speaker,
                 str(speaker_verbosity.tolist()[index]),
                 fontsize=8)

    plt.title('Least Verbose Speakers\n(must have spoken 10+ times)',
              fontweight='bold')
    plt.xlabel('Average words per statement')
    plt.tight_layout()
    plt.show()


def add_question_marks(string, number):
    '''
    Formats a given string to insert the needed number of question marks to
    prepare for SQL query.
    '''
    return string.format(",".join('?'*number))


def enclose_in_percents(string):
    '''
    encloses a given string in percent signs
    '''
    return '%' + string + '%'


def get_header(cursor):
    '''
    Given a cursor object, returns the appropriate header (column names)
    '''
    header = []

    for i in cursor.description:
        s = i[0]
        if "." in s:
            s = s[s.find(".")+1:]
        header.append(s)

    return header

def assert_valid_input(args_from_ui):
    '''
    Verify that the input conforms to the standards set in the
    assignment.
    '''

    acceptable_keys = set(['speaker_name', 'speaker_title', 'datetime_start',
                           'datetime_end', 'network_name', 'show_name', 'term'])

    if (not isinstance(args_from_ui, dict) or
        not set(args_from_ui.keys()).issubset(acceptable_keys) or
        not isinstance(args_from_ui.get("speaker_name", ""), str) or
        not isinstance(args_from_ui.get("speaker_title", ""), str) or
        not isinstance(args_from_ui.get("datetime_start", ""), str) or
        not isinstance(args_from_ui.get("datetime_end", ""), str) or
        not isinstance(args_from_ui.get("network", []), list) or
        not all([isinstance(s, str) for s in args_from_ui.get("network", [])]) or
        not isinstance(args_from_ui.get("show_name", ""), str) or
        not isinstance(args_from_ui.get("term", []), list) or
        not all([isinstance(s, str) for s in args_from_ui.get("term", [])])):
        return True
