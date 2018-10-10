import argparse
import logging
import random
import sys
import time
import pytz

import threading

from hockey import team, game

ALL_TIMEZONES = [
    pytz.timezone(tz) for tz in pytz.all_timezones if 'US/' in tz or 'Canada/' in tz]
LOCAL_TZ = pytz.timezone('US/Pacific')

parser = argparse.ArgumentParser()
parser.add_argument(
    '-d', '--debug',
    help="Print lots of debugging statements",
    action="store_const", dest="loglevel", const=logging.DEBUG,
    default=logging.WARNING,
)
parser.add_argument(
    '-v', '--verbose',
    help="Be verbose",
    action="store_const", dest="loglevel", const=logging.INFO,
)
args = parser.parse_args()

logging.basicConfig(format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
                    datefmt="%Y-%m-%d %H:%M:%S",  stream=sys.stdout, level=args.loglevel)
log = logging.getLogger(__name__)


def main():
    '''
    Main loop will get all of today\'s games, start a control thread which will
    kick off each game into it\'s own daemon thread. Once all games have finished,
    control thread will finish and program will exit.
    '''
    games = game.get_todays_games()
    game.start_all_games(games)
    time.sleep(1)
    for game_ in games:
        print('\t' + game_.home_team.name, 'face',
              game_.away_team.name, '@',
              game_.date.astimezone(LOCAL_TZ).strftime("%I:%M%p"),
              '(' + game_.date.astimezone(LOCAL_TZ).tzname() + ')')
        i = random.randint(1, 1)
        time.sleep(i)
        game_.is_finished = True
    time.sleep(1)
    log.info('Program exiting')


if __name__ == "__main__":
    main()
