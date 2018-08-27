#!flask/bin/python

from flask import Flask
from flask import request
import json
# import pickle
from mtgsdk import Card
import os
import uuid

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

class JsonSerializable:
    def shouldSerialize(self, k):
        return True
    
    def valueToJson(self, v):
        # print("valueToJson(%s)" % v)
        if getattr(v, 'toJson', False):
            v = v.toJson()
        elif isinstance(v, list):
            v = [self.valueToJson(v_el) for v_el in v]
        return v
    
    def toJson(self):
        # print ("toJson(%s)" % self)
        data = {}
        for k in self.__dict__:
            if self.shouldSerialize(k):
                v = self.valueToJson(self.__dict__[k])
                data[k] = v
        return [type(self).__name__, data]

    @classmethod
    def jsonToValue(classobj, jsonData):
        # print ("jsonToValue(%s)" % jsonData)
        if isinstance(jsonData, list) and len(jsonData) > 0:
            if  isinstance(jsonData[0], str) and jsonData[0] in globals():
                valueClassObj = globals()[jsonData[0]]
                if hasattr(valueClassObj, 'fromJson'):
                    jsonData = valueClassObj.fromJson(jsonData)
            else:
                jsonData = [classobj.jsonToValue(el) for el in jsonData]
            
        return jsonData
    
    @classmethod
    def fromJson(classobj, obj):
        # print("fromJson(%s)" % obj)
        assert isinstance(obj, list)
        assert obj[0] == classobj.__name__
        data = obj[1]
        instance = classobj()
        for k in data:
            v = classobj.jsonToValue(data[k])
            instance.__dict__[k] = v
        return instance

class PersistentObject:
    savepath = ""
    def save(self):
        assert isinstance(self, JsonSerializable)
        json.dump(self.toJson(), open(self.savepath, "w+"))

    @classmethod
    def load(classObj):
        assert issubclass(classObj, JsonSerializable)
        data = classObj()
        if os.path.isfile(classObj.savepath):
            jsondata = json.load(open(classObj.savepath, "r+"))
            data = classObj.fromJson(jsondata)
        return data

            

###############################################################################
## Players

class Player(JsonSerializable):
    def __init__(self, playerName = ""):
        self.name   = playerName
        self.id     = str(uuid.uuid3(uuid.NAMESPACE_URL, playerName))

class PlayersDB(PersistentObject, JsonSerializable):
    savepath = 'players.dat'
    
    def __init__(self):
        self.players = []

    def add(self, newPlayerName):
        playerData = [p for p in self.players if p.name == newPlayerName]
        playerFound = playerData != []
        if playerFound:
            return playerData
        else:
            newPlayer = Player(newPlayerName)
            self.players += [newPlayer]
            return newPlayer
    
    def get(self, name):
        for p in self.players:
            if p.name == name:
                return p
        return False

@app.route('/player', methods=['POST', 'GET'])
def player():
    cmd = request.args.get('cmd','')
    players = PlayersDB.load()
    if cmd == 'add':
        name = request.args.get('player','')
        players.add(name)
        players.save()
        return "player %s added" % name
    return 'unknown command'

###############################################################################
## Seasons

class Season(JsonSerializable):
    class PlayerInfo(JsonSerializable):
        def __init__(self, id = ""):
            self.playerId = id
            self.deckColors = []
            self.paid = False

    def __init__(self, db = None, setname = ""):
        self.set = setname
        self.registeredPlayers = []
        self.matches = []
        self.rarePool = []
        self.db = db

    def shouldSerialize(self, k):
        if k == "db":
            return False
        else:
            return super().shouldSerialize(k)

    def generateMatches(self):
        self.match = [] # todo

    def registerPlayer(self, name):
        players = PlayersDB.load()
        playerData = players.add(name)
        isRegistered = next((p for p in self.registeredPlayers if playerData.id == p.playerId), False)
        if not isRegistered:
            self.registeredPlayers += [Season.PlayerInfo(playerData.id)]
            db.save()

    def addToRaresPool(self, cardIds):
        for newRareId in cardIds:
            added = False
            for rare in self.rarePool:
                if rare['id'] == newRareId:
                    rare['count'] += 1
                    added = True
                    break
            if not added:
                self.rarePool += [{'id' : newRareId, 'count' : 1}]
        db.save()

    def removeRaresFromPool(self, cardIds):
        for rareId in cardIds:
            for r in self.rarePool:
                if r['id'] == rareId:
                    r['count'] -= 1
        self.rarePool = [r for r in self.rarePool if r['count'] > 0]
        db.save()
    
class SeasonsDB(PersistentObject, JsonSerializable):
    savepath = 'seasons.dat'

    def __init__(self):
        self.seasons = []

    @classmethod
    def fromJson(classobj, obj):
        db = super().fromJson(obj)
        for s in db.seasons:
            s.db = db
        return db

    def newSeason(self, setname):
        for s in self.seasons:
            if s.set == s:
                return False
        self.seasons += [Season(self, setname)]
        self.save()
        return True

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
        if not currentSeason:
            return "no seasons started"
        elif name == "":
            return "invalid player name"
        else:
            currentSeason.registerPlayer(name)
            return "registered player: %s" % name
    elif cmd == 'newseason':
        set = request.args.get('set','')
        if set == "":
            return "invalid set name..."
        else:
            if seasons.newSeason(set):
                return "started season: %s" % set
            else:
                return "couldn't start new season %s" % set
    
    return "unknown command"
        
###############################################################################
## main

if __name__ == '__main__':
    app.run(debug=True)
    
