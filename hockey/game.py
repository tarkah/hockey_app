import requests
from concurrent.futures import ThreadPoolExecutor
from threading import Thread

from hockey.team import Team
from hockey.constants import BASE_URL, GAME_LINK, SCHEDULE_LINK


class Game(Thread):
    def __init__(self, id_):
        Thread.__init__(self)
        self.id = id_
        self._get_game_data()
        self._store_game_data()
        print("I'm the {} home thread!".format(self.home_team.name))

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
        with ThreadPoolExecutor(max_workers=2) as pool:
            future_home_team = pool.submit(
                Team, self.game_data['teams']['home']['id'])
            future_away_team = pool.submit(
                Team, self.game_data['teams']['away']['id'])
        self.home_team = future_home_team.result()
        self.away_team = future_away_team.result()


def get_todays_games():
    '''Returns a list of Game objects for today's schedule'''
    url = BASE_URL + SCHEDULE_LINK
    r = requests.get(url)
    data = r.json()
    with ThreadPoolExecutor(max_workers=100) as pool:
        games = list(pool.map(Game, [game['gamePk']
                                     for game in data['dates'][0]['games']]))

    return games


def all_teams(games):
    '''Returns a list of Team objects the supplied list of Game objects'''
    team_ids = []
    for game in games:
        team_ids.append(game.home_team)
        team_ids.append(game.away_team)
    return team_ids
