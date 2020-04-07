"""
Text analysis
"""

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer


SPEAKER_NAME = 'speaker_name'
SPEAKER_ID = 'speaker_id'
WORDS = 'words'
SHOW_NAME = 'show_name'
EPISODE_ID = 'episode_id'
AIRTIME = 'airtime'
NETWORK_NAME = 'network_name'
TOKENS = 'tokens'
TWO_GRAMS = '2grams'
THREE_GRAMS = '3grams'

TOP_WORDS = 10
TOP_SENTENCES = 3

def preprocess_text(df):
    '''
    Takes list of transcript text and splits the text.  If stopwords = True,
    strips out stopwords.

    Input:
        df (Pandas dataframe): dataframe of transcript text blocks
    Outputs: Pandas dataframe
    '''

    group_df = df.groupby([EPISODE_ID, AIRTIME, NETWORK_NAME, SHOW_NAME])[WORDS] \
                 .apply(' '.join).reset_index()
    no_punc = group_df[WORDS].str.replace(r"[^\w\s\'\"]", "")

    ##Removes time or standalone numbers
    no_nums = no_punc.str.replace(r"(\d+:\d{2})|(\d+)", "")

    tokens = no_nums.apply(lambda x: x.lower().split())

    stop_words = stopwords.words('english')
    stop_words.extend(["i'm", "ll", "coming", "know", "want", "evening",
                       "morning", "thank", "standby", "welcome", "oh", "ok",
                       "dr", "say", "happy", "good", "year"])
    no_stop_words = tokens.apply(lambda x: [word for word in x if word \
                                            not in stop_words])
    group_df[TOKENS] = no_stop_words.str.join(" ")

    return group_df

def tokenize(text):
    '''
    Remove punctuation and split words to tokenize string
    Inputs:
        text (string): textual string
    Outputs: List of strings
    '''
    no_punc = text.replace(r"[^\w\s\'\"]", "")
    tokens = no_punc.lower().split()

    return tokens


def analyze(df):
    '''
    Performs analysis on dataframe of transcripts.  Groups transcript blocks
    by episode and creates a tf-idf vectorizer to compute top tokens and
    sentences per episode.  Main output for Django front-end.

    Inputs:
        df (Pandas dataframe): Pandas dataframe
    Outputs: List of dictionaries
    '''
    # print(df)
    nltk.data.path.append('./nltk_data/')
    tokens = preprocess_text(df)
    # print(tokens)
    tfidf_vectorizer = TfidfVectorizer(stop_words='english',
                                       max_features=100000,
                                       use_idf=True)
    token_tfidf = tfidf_vectorizer.fit_transform(tokens[TOKENS])
    to_unpack = tokens.index.to_series().apply(lambda r: \
                                        find_top(tokens, r,
                                                 token_tfidf,
                                                 tfidf_vectorizer)) \
                                        .apply(pd.Series)
    to_unpack.columns = ['top_tokens', 'top_sentences']
    tokens = pd.concat([to_unpack, tokens], axis=1)

    ## Removes episode from dataframe if number of top sentences is fewer than
    ## the benchmark.

    tokens = tokens[tokens['top_sentences'].map(len) >= TOP_SENTENCES]
    tokens = tokens[tokens['top_tokens'].map(len) >= TOP_WORDS]

    tokens = tokens.sort_values(by=["airtime"])
    return tokens[["show_name", "airtime", "network_name", "top_tokens",
                   "top_sentences"]].to_dict('records')


def find_top(df, row_index, token_tfidf, tfidf_vectorizer):
    '''
    Using tf-idf word scores for each episode, calculate summary sentences
    comprising of top sentences with highest mean tf-idf score.

    Inputs:
        df (Pandas Dataframe): Dataframe of episode transcripts with
                               preprocessed text
        row_index (int): Index of dataframe row, representing an episode
        token_tfidf (sparse matrix object): TF-IDF score matrix
        tfidf_vectorizer
    Output: Pandas series of top words and top sentences
    '''

    tfidf_df = pd.DataFrame(token_tfidf[row_index].T.todense(),
                            index=tfidf_vectorizer.get_feature_names(),
                            columns=['tfidf']).sort_values(by='tfidf',
                                                           ascending=False)
    tfidf_df = tfidf_df[tfidf_df['tfidf'] > 0]

    sentences = df[WORDS].apply(sent_tokenize)
    sentence_df = pd.DataFrame((sentence for sentence in sentences[row_index]),
                               columns=["sentence"])
    sentence_df[WORDS] = sentence_df["sentence"].apply(tokenize)

    ## Filters out sentences with a word count of 3.  Assumes 3 words are
    ## greetings or other 'non-essential' asides.
    sentence_df = sentence_df[sentence_df[WORDS].map(len) > 3]

    sentence_df["sentence_score"] = sentence_df[WORDS].apply(lambda x: \
                                                             score_sentences(x,
                                                                             tfidf_df))

    return (tfidf_df[:TOP_WORDS].index.tolist(),
            sentence_df.sort_values(by='sentence_score', ascending=False) \
            ["sentence"][:TOP_SENTENCES].to_list())

def score_sentences(words, tfidf_score):
    '''
    Takes a list of sentences spoken by speaker in episode, returns a series
    of sentences with mean TF-IDF score
    Inputs:
        words (list): List of sentences
        tfidf_score (Pandas Dataframe): Pandas dataframe of tf-idf scores
    Outputs: integer
    '''

    words_df = pd.DataFrame((word for word in words), columns=[WORDS])
    merge_score = pd.merge(words_df, tfidf_score, left_on="words", right_index=True)

    return merge_score.sum()["tfidf"] / len(words_df)
