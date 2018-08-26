#!flask/bin/python

from flask import Flask
from flask import request
import pickle
from mtgsdk import Card
import os

app = Flask(__name__)

def getCards():
    cards = Card.where(supertypes='legendary') \
                .where(types='creature') \
                .where(set='M19') \
                .all()
    return cards

@app.route('/')
def index():
    txt = "<table>"
    for c in getCards():
        txt += "<tr><td><img src=\'"+ c.image_url +"'></td></tr>"
    txt += "</table>"
    return txt

@app.route('/test')
def test():
    txt = "<table>"
    for c in getCards():
        txt += "<tr><td>"+ c.name +"</td></tr>"
    txt += "</table>"
    return txt    


@app.route('/admin')
def admin():
    txt = ""
    txt += '<div><h2>Players</h2></div>\n'
    txt += '<div><h2>Games</h2></div>\n'
    txt += '<div><h2>Card Pool</h2></div>\n'
    return txt

###############################################################################
## Object Persistence

class PersistentObject:
    savepath = ""
    def save(self):
        pickle.dump(self, open(self.savepath, "wb+"))

    @classmethod
    def load(classObj):
        data = classObj()
        if os.path.isfile(classObj.savepath):
            data = pickle.load(open(classObj.savepath, "rb"))
        return data

###############################################################################
## Players

class Player:
    def __init__(self, name):
        self.name = name

class PlayersDB(PersistentObject):
    savepath = 'players.dat'
    
    def __init__(self):
        self.players = []

    def add(self, newPlayer):
        alreadyThere = list(filter(lambda x: x.name == newPlayer.name, self.players)) != []
        if not alreadyThere:
            self.players += [newPlayer]
            return True
        else:
            return False

@app.route('/player', methods=['POST', 'GET'])
def player():
    cmd = request.args.get('cmd','')
    players = PlayersDB.load()
    if cmd == 'add':
        name = request.args.get('player','')
        # colors = request.args.get('colors','')
        newPlayer = Player(name)
        if players.add(newPlayer):
            players.save()
            return "player %s added" % name
        else:
            return "player already present..."
    return 'unknown command'

###############################################################################
## Seasons

class Season():
    def __init__(self, db, setname):
        self.set = setname
        self.registeredPlayers = []
        self.matches = []
        self.db = db
    
    def generateMatches(self):
        self.match = [] # todo

    def registerPlayer(name):
        if name not in self.registerPlayer:
            players = PlayersDB.load()
            players.add(Player(name))
            registerPlayer += [name]
            db.save()

class SeasonsDB(PersistentObject):
    savepath = 'seasons.dat'

    def __init__(self):
        self.seasons = []

    def newSeason(self, setname):
        for s in self.seasons:
            if s.set == s:
                return False
        self.seasons += [Season(self, setname)]
        self.save()

    def getSeason(self, setname):
        for s in self.season:
            if (s.set == setname):
                return s
        return False

    def getLatestSeason(self):
        seasonCount = len(self.seasons)
        if (seasonCount == 0):
            return False
        else:
            return self.seasons[seasonCount-1]
        

@app.route('/season', methods=['POST', 'GET'])
def season():
    cmd = request.args.get('cmd','')
    seasons = SeasonsDB.load()
    currentSeason = seasons.getLatestSeason()
    if cmd == 'register':
        name = request.args.get('player','')
        if name != "" and currentSeason:
            currentSeason.registerPlayer(name)
            return "registered player: %s" % name
    elif cmd == 'newseason':
        set = request.args.get('set','')
        if set != "":
            if seasons.newSeason(set):
                return "started season: %s" % set
            else:
                return "season: %s already started" % set
    
    return "unknown command"
        

if __name__ == '__main__':
    app.run(debug=True)
