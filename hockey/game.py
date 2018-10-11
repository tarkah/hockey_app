import logging
import time
from datetime import datetime
import pytz

import requests

from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from hockey.team import Team
from hockey.constants import BASE_URL, GAME_LINK, SCHEDULE_LINK, GAME_CYCLE_TIME

log = logging.getLogger(__name__)


class Game(Thread):
    def __init__(self, id_):
        self.id = id_
        self.is_finished = False
        self._get_game_data()
        self._store_game_data()
        log.info('{} initiated'.format(self.__repr__()))

        Thread.__init__(self)

    def __repr__(self):
        return 'Game({} @ {})'.format(self.away_team.name, self.home_team.name)

    def __str__(self):
        return '{} @ {}'.format(self.away_team.name, self.home_team.name)

    def _get_game_data(self):
        game_link = GAME_LINK.format(id=self.id)
        url = BASE_URL + game_link
        r = requests.get(url)
        data = r.json()
        self.game_data = data['gameData']

    def _get_live_data(self):
        game_link = GAME_LINK.format(id=self.id)
        url = BASE_URL + game_link
        r = requests.get(url)
        data = r.json()
        self.live_data = data['liveData']

    def _store_game_data(self):
        home_team_id = self.game_data['teams']['home']['id']
        away_team_id = self.game_data['teams']['away']['id']
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_home_team = pool.submit(Team, home_team_id)
            future_away_team = pool.submit(Team, away_team_id)
        self.home_team = future_home_team.result()
        self.away_team = future_away_team.result()

        date = self.game_data['datetime']['dateTime']
        date = datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ")
        self.date = pytz.utc.localize(date)

    def loop(self):
        while not self.is_finished:
            start_time = time.time()
            # DO STUFF HERE
            end_time = time.time()
            time_delta = end_time - start_time
            if GAME_CYCLE_TIME > time_delta:
                sleep_time = GAME_CYCLE_TIME - time_delta
                time.sleep(sleep_time)
            else:
                sleep_time = 0
            log.info('{} cycle complete, took {}s, waited {}s'.format(
                self.__repr__(), time_delta, sleep_time))

    def run(self):
        '''
        Threaded loop for Game. When run, game will fetch live updates from
        API and send out notifications when milestones occur. Thread will
        live until game has concluded.        
        '''
        log.info('{} started'.format(self.__repr__()))
        self.loop()
        log.info('{} has finished'.format(self.__repr__()))


def get_todays_games():
    '''Returns a list of Games for today's schedule'''
    url = BASE_URL + SCHEDULE_LINK
    r = requests.get(url)
    data = r.json()
    with ThreadPoolExecutor(max_workers=100) as pool:
        games = list(pool.map(Game, [game['gamePk']
                                     for game in data['dates'][0]['games']]))
    return games


def all_teams(games):
    '''Returns a list of Teams the supplied list of Games'''
    teams = []
    for game in games:
        teams.append(game.home_team)
        teams.append(game.away_team)
    return teams


def _thread_all_games(games):
    for game in games:
        game.start()
    for game in games:
        game.join()
    log.info('All games have finished')


def start_all_games(games):
    '''
    Starts all Games from provided list in it's own control thread. Each Game 
    will run on it's own thread under that. Upon completion of all Games, 
    control thread will finish.
    '''
    thread = Thread(target=_thread_all_games, args=(games, ), daemon=True)
    thread.start()
    return thread
