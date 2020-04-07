CREATE TABLE show(
    show_name varchar(25) NOT NULL PRIMARY KEY,
    network_name varchar(7));

CREATE TABLE episode(
    episode_id varchar(7) NOT NULL PRIMARY KEY,
    headline varchar(200),
    airtime datetime,
    show_name varchar(7),
    FOREIGN KEY(show_name) REFERENCES show(show_name));

CREATE TABLE speaker(
    speaker_id int NOT NULL PRIMARY KEY,
    speaker_name varchar(50));

CREATE TABLE title(
    speaker_id varchar(7),
    speaker_title varchar(50),
    FOREIGN KEY(speaker_id) REFERENCES speaker(speaker_id));

CREATE TABLE transcript(
    phrase_id int NOT NULL PRIMARY KEY,
    episode_id varchar(7),
    words text,
    speaker_id varchar(7),
    FOREIGN KEY(episode_id) REFERENCES episode(episode_id),
    FOREIGN KEY(speaker_id) REFERENCES speaker(speaker_id));
