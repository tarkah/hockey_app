import os
import time
from datetime import datetime
import pytz
import json
import logging
import requests
import redis
from twilio.rest import Client

logger = logging.getLogger(__name__)

local_tz = pytz.timezone('US/Pacific')
today = datetime.now().strftime('%Y-%m-%d')

redis_url = os.getenv('REDIS_URL', '127.0.0.1')
db = redis.StrictRedis.from_url(
    redis_url, charset="utf-8", decode_responses=True)

account_sid = os.getenv("TWIL_ACCOUNT_SID")
auth_token = os.getenv("TWIL_AUTH_TOKEN")
from_number = os.getenv("FROM_NUMBER")
twilio_client = Client(account_sid, auth_token)

phonebook = json.loads(os.environ['PHONEBOOK'])

team_id = 54  # find id from http://statsapi.web.nhl.com/api/v1/teams
base_url = 'http://statsapi.web.nhl.com'
schedule_link = '/api/v1/schedule'
team_link = '/api/v1/teams'


def main():
    game_state = todays_schedule()

    if game_state is None:
        print('No game scheduled today - {}'.format(today))
    elif 'Scheduled' in game_state:
        pre_game()
    elif 'In Progress' in game_state or 'Game Over' in game_state:
        in_game()
    elif 'Final' in game_state:
        post_game()


def get_response(link, params):
    full_url = '{}{}'.format(base_url, link)

    try:
        response = requests.get(full_url, params=params)
        response.raise_for_status()
    except requests.exceptions.HTTPError as err:
        logger.error(err)
        raise
    except requests.exceptions.ConnectionError as err:
        logger.error(err)
        raise
    except requests.exceptions.Timeout as err:
        logger.error(err)
        raise
    except requests.exceptions.RequestException as err:
        logger.error(err)
        raise

    return response.json()


def todays_schedule():
    print('Checking for today - {}'.format(today))
    params = {'teamId': team_id, 'startDate': today, 'endDate': today}
    data = get_response(schedule_link, params)
    if data['totalGames'] == 0:
        return None

    else:
        game = data['dates'][0]['games'][0]

        status = game['status']['detailedState']

        if db.get('pre_updated') == 'Yes' or 'Final' in status:
            return status

        else:
            game_date_utc = pytz.utc.localize(
                datetime.strptime(game['gameDate'], "%Y-%m-%dT%H:%M:%SZ"))
            game_date_local = game_date_utc.astimezone(local_tz)
            game_date_str = game_date_local.strftime("%m/%d/%Y")
            game_time_str = game_date_local.strftime("%I:%M %p")
            game_link = game['link']

            game_venue = game['venue']['name']

            if team_id == game['teams']['home']['team']['id']:
                my_field = 'home'
                opp_field = 'away'
            else:
                my_field = 'away'
                opp_field = 'home'

            opp_id = game['teams'][opp_field]['team']['id']

            get_team_values(team_id, 'my')
            get_team_values(opp_id, 'opp')

            db.set('game_date_str', game_date_str)
            db.set('game_time_str', game_time_str)
            db.set('game_link', game_link)
            db.set('status', status)
            db.set('my_field', my_field)
            db.set('opp_field', opp_field)
            db.set('opp_id', opp_id)
            db.set('game_venue', game_venue)

            db.set('pre_updated', 'Yes')

            return status


def get_team_values(_id, type):
    params = {'teamId': _id}
    data = get_response(team_link, params)

    team = data['teams'][0]

    db.set(type+'_full_name', team['name'])
    db.set(type+'_abbrev', team['abbreviation'])
    db.set(type+'_team_name', team['teamName'])
    db.set(type+'_location', team['locationName'])


def pre_game():
    if db.get('pre_sent') == 'Yes':
        print('Notification text already sent')

    elif datetime.now().hour == 7:
        my_team_name = db.get('my_team_name')
        opp_full_name = db.get('opp_full_name')
        game_venue = db.get('game_venue')
        game_time_str = db.get('game_time_str')
        my_field = db.get('my_field')

        if my_field == 'home':
            message = 'The {} play at home against the {}!  Game starts at {}.'.format(my_team_name, opp_full_name,
                                                                                       game_time_str)
        else:
            message = 'The {} play the {} on the road at {}!  Game starts at {}.'.format(my_team_name, opp_full_name,
                                                                                         game_venue, game_time_str)

        for to_number in phonebook:
            twilio_client.messages.create(
                body=message, to=to_number, from_=from_number)
        print(message)

        db.set('pre_sent', 'Yes')


def in_game():
    response = get_response(db.get('game_link'), None)

    my_team_name = db.get('my_team_name')
    opp_team_name = db.get('opp_team_name')
    my_abbrev = db.get('my_abbrev')
    opp_abbrev = db.get('opp_abbrev')
    my_field = db.get('my_field')
    opp_field = db.get('opp_field')

    past_scores = db.get('past_scores')
    if past_scores is None:
        past_scores = []
    else:
        past_scores = json.loads(past_scores)

    scoring_plays_notified = db.get('scoring_plays_notified')
    if scoring_plays_notified is None:
        scoring_plays_notified = []
    else:
        scoring_plays_notified = json.loads(scoring_plays_notified)

    scoring_plays = response['liveData']['plays']['scoringPlays']

    scoring_plays_unnotified = list(
        set(scoring_plays) - set(scoring_plays_notified))

    for score in sorted(scoring_plays_unnotified):
        play = response['liveData']['plays']['allPlays'][score]

        description = play['result']['description']
        try:
            game_winning = play['result']['gameWinningGoal']
        except:
            game_winning = False

        scoring_period = play['about']['ordinalNum']
        scoring_time = play['about']['periodTimeRemaining']
        my_score = play['about']['goals'][my_field]
        opp_score = play['about']['goals'][opp_field]

        if str(my_score)+str(opp_score) in past_scores:
            print("Duplicate scoring play! Not notified.")
            scoring_plays_notified.append(score)
            continue
        else:
            past_scores.append(str(my_score)+str(opp_score))
            db.set('past_scores', json.dumps(past_scores))

        if game_winning:
            if team_id == play['team']['id']:
                message = '{} wins!!\n\n{} {}, {} {} - {} {}\n\n{}'.format(my_team_name, scoring_time,
                                                                           scoring_period, my_abbrev,
                                                                           my_score, opp_abbrev,
                                                                           opp_score, description)
            else:
                message = '{} wins :(\n\n{} {}, {} {} - {} {}\n\n{}'.format(opp_team_name, scoring_time,
                                                                            scoring_period, my_abbrev,
                                                                            my_score, opp_abbrev,
                                                                            opp_score, description)
        else:
            if team_id == play['team']['id']:
                message = '{} score!!\n\n{} {}, {} {} - {} {}\n\n{}'.format(my_team_name, scoring_time,
                                                                            scoring_period, my_abbrev,
                                                                            my_score, opp_abbrev,
                                                                            opp_score, description)
            else:
                message = '{} score :(\n\n{} {}, {} {} - {} {}\n\n{}'.format(opp_team_name, scoring_time,
                                                                             scoring_period, my_abbrev,
                                                                             my_score, opp_abbrev,
                                                                             opp_score, description)

        for to_number in phonebook:
            twilio_client.messages.create(
                body=message, to=to_number, from_=from_number)
        print(message)

        scoring_plays_notified.append(score)

    db.set('scoring_plays_notified', json.dumps(scoring_plays_notified))


def post_game():
    if db.get('pre_sent') == 'Yes':
        db.flushall()
        message = 'Database flushed'
        print(message)

    print('Nothing new for today...')


if __name__ == '__main__':
    while 1 == 1:
        main()
        time.sleep(10)
