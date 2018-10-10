import requests
from concurrent.futures import ThreadPoolExecutor

from hockey.constants import BASE_URL, TEAM_LINK


class Team():
    def __init__(self, id_):
        self.id = id_
        self._get_team_data()
        self._store_team_data()

    def __repr__(self):
        return 'Team({})'.format(self.name)

    def _get_team_data(self):
        url = BASE_URL + '/'.join([TEAM_LINK, str(self.id)])
        r = requests.get(url)
        data = r.json()
        self.team_data = data['teams'][0]

    def _store_team_data(self):
        self.name = self.team_data['teamName']
        self.full_name = self.team_data['name']
        self.short_name = self.team_data['shortName']
        self.abbreviation = self.team_data['abbreviation']
        self.venue_name = self.team_data['venue']['name']
        self.venue_city = self.team_data['venue']['city']
        self.venue_tz = self.team_data['venue']['timeZone']['id']


def all_team_ids():
    """Returns a list of all team ids from the API"""
    url = BASE_URL + TEAM_LINK
    r = requests.get(url)
    data = r.json()
    team_ids = [team['id'] for team in data['teams']]
    return team_ids


def get_team(team_id):
    """Returns a Team object for the supplied id"""
    team = Team(team_id)
    return team


def get_teams(team_ids):
    """Returns a list of Team objects for the supplied list of ids"""
    with ThreadPoolExecutor(max_workers=100) as pool:
        teams = list(pool.map(get_team, [team_id for team_id in team_ids]))
        return teams
