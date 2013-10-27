"""
Data transfer objects:
- login, with OpenID, OpenID provider, email address, screenname
- user, with userid for user, system generated
- gameid for open, running or finished game
- range-based action
- open game, with list of users registered and details of situation
- general game, with status (open/running/finished), whose turn?, details of
  situation as per open game list
- hand history(!)
"""

class LoginDetails(object):
    """
    OpenID provider, email address, screenname
    """
    def __init__(self, userid, provider, email, screenname):
        self.userid = userid
        self.provider = provider
        self.email = email
        self.screenname = screenname

class UserDetails(object):
    """
    userid, screenname
    """
    def __init__(self, userid, screenname):
        self.userid = userid
        self.screenname = screenname

class RangeBasedActionDetails(object):
    """
    range-based action
    """
    pass

class OpenGameDetails(object):
    """
    list of users in game, and details of situation
    """
    def __init__(self, gameid, screennames, description):
        self.gameid = gameid
        self.screennames = screennames
        self.description = description
    
    @classmethod
    def from_open_game(cls, open_game):
        names = [ogp.user.screenname
                 for ogp in open_game.ogps] 
        description = open_game.situation.description
        return cls(open_game.gameid, names, description)

class RunningGameDetails(object):
    """
    list of users in game, and details of situation
    """
    def __init__(self, gameid, screennames, description):
        self.gameid = gameid
        self.screennames = screennames
        self.description = description
    
    @classmethod
    def from_running_game(cls, running_game):
        names = [rgp.user.screenname
                 for rgp in running_game.rgps] 
        description = running_game.situation.description
        return cls(running_game.gameid, names, description)

class GameDetails(object):
    """
    general game, with status (open/running/finished), whose turn?, details of
    situation as per open game list
    """
    pass

class HandHistoryDetails(object):
    """
    sufficient to show a completed game, analysis etc. to user
    sufficient for the user to choose their new range-based action
    """
    pass