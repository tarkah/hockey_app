import requests
from concurrent.futures import ThreadPoolExecutor

from constants import BASE_URL, TEAM_LINK


class Team():
    def __init__(self, id_):
        self.id = id_
        self._get_api_values()
        self._store_api_values()

    def _get_api_values(self):
        url = BASE_URL + '/'.join([TEAM_LINK, str(self.id)])
        r = requests.get(url)
        data = r.json()
        self.api_values = data['teams'][0]

    def _store_api_values(self):
        self.name = self.api_values['teamName']
        self.full_name = self.api_values['name']
        self.short_name = self.api_values['shortName']
        self.abbreviation = self.api_values['abbreviation']
        self.venue_name = self.api_values['venue']['name']
        self.venue_city = self.api_values['venue']['city']
        self.venue_tz = self.api_values['venue']['timeZone']['id']


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
    with ThreadPoolExecutor(max_workers=50) as pool:
        teams = list(pool.map(get_team, [team_id for team_id in team_ids]))
        return teams


if __name__ == "__main__":
    team_ids = all_team_ids()
    teams = get_teams(team_ids)
    for team in teams:
        print(team.name)
