from hockey import team, game

if __name__ == "__main__":
    team_ids = team.all_team_ids()
    teams = team.get_teams(team_ids)
    for team in teams:
        print(team.name)

    games = game.get_todays_games()
    for game_ in games:
        print(game_.home_team.name + ' face ' + game_.away_team.name)
    teams = game.all_teams(games)
    print(teams)
