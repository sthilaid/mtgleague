#!python

import datetime
from flask import Flask
from flask import request
import functools
import json
from mtgsdk import Card
from mtgsdk import Set
import pdb
import os
import random
import uuid

app = Flask(__name__, static_folder="static")

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

# todo: defien decorator that can keep track of all the serializable instance
# and look in that list while desirializing instead of in globals(). the
# decorator can then add JsonSerializable as a subclass while decorating...?

class JsonSerializable:
    def shouldSerialize(self, k):
        return True

    @staticmethod
    def valueToJson(v):
        # print("valueToJson(%s)" % v)
        if getattr(v, 'toJson', False):
            v = v.toJson()
        elif isinstance(v, list):
            v = [JsonSerializable.valueToJson(v_el) for v_el in v]
        return v
    
    def toJson(self):
        # print ("toJson(%s)" % self)
        data = {}
        for k in self.__dict__:
            if self.shouldSerialize(k):
                v = self.valueToJson(self.__dict__[k])
                data[k] = v
        return [type(self).__name__, data]

    @staticmethod
    def jsonToValue(jsonData):
        # print ("jsonToValue(%s)" % jsonData)
        if isinstance(jsonData, list) and len(jsonData) > 0:
            serializableClass = next((c for c in serializableClasses.classes if c.__name__ == jsonData[0]), False)
            if serializableClass:
                if hasattr(serializableClass, 'fromJson'):
                    jsonData = serializableClass.fromJson(jsonData)
            else:
                jsonData = [JsonSerializable.jsonToValue(el) for el in jsonData]
            
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

class serializableClasses:
    classes = []
    
def jsonSerializableObj(cls):
    class newClass(cls, JsonSerializable):
        pass

    newClass.__name__ = cls.__name__
    newClass.__wrapped__ = cls
    serializableClasses.classes += [newClass]
    return newClass
    

class PersistentObject:
    savepath = ""
    def save(self):
        # pdb.set_trace()
        jsondata = self.toJson()
        jsonStr = json.dumps(jsondata)
        with open(self.savepath, "w+") as file:
            file.write(jsonStr)

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

@jsonSerializableObj
class Player():
    def __init__(self, playerName = ""):
        self.name   = playerName
        self.id     = str(uuid.uuid3(uuid.NAMESPACE_URL, playerName))

    def __str__(self):
        return "[Player: %s id: %s]" % (self.name, self.id)

@jsonSerializableObj
class PlayersDB(PersistentObject):
    savepath = 'players.dat'
    
    def __init__(self):
        self.players = []

    def __str__(self):
        return "[PlayersDB: %d elements]" % len(self.players)

    def add(self, newPlayerName):
        playerData = next((p for p in self.players if p.name == newPlayerName), False)
        if playerData:
            return playerData
        else:
            newPlayer = Player(newPlayerName)
            self.players += [newPlayer]
            playerData = newPlayer

        self.save()
        return playerData
    
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

@jsonSerializableObj
class Season():
    ###########################################################################
    ## Season.PlayerInfo
    @jsonSerializableObj
    class PlayerInfo():
        def __init__(self, id = "", deckColors = []):
            self.playerId = id
            self.deckColors = deckColors
            self.paid = False
            self.rareTokens = 0

        def __str__(self):
            return "[pinfo id: %s colors: %s, paid: %d]" % (self.playerId, self.deckColors, self.paid)

    ###########################################################################
    ## Season.Match
    @jsonSerializableObj
    class Match():
        def __init__(self, p1 = "", p2 = "", week=0):
            self.p1 = p1
            self.p2 = p2
            self.week = week
            self.score = (0, 0) # (p1, p2)

        def isMatchup(self, p1, p2):
            return (self.p1 == p1 or self.p2 == p1) and (self.p1 == p2 or self.p2 == p2)
    
        def __str__(self):
            players = PlayersDB.load()
            p1 = next((p.name for p in players.players if p.id == self.p1), False)
            p2 = next((p.name for p in players.players if p.id == self.p2), False)
            return "[match week %d: %s %d vs %s %d]" % (self.week, p1, self.score[0], p2, self.score[1])

    ###############################################################################
    ## Season states
    @jsonSerializableObj
    class SeasonState():
        registration    = 0
        preseason       = 1
        started         = 2
        playoffs        = 3
        finished        = 4

        def __init__(self, weekCount=7):
            self.weekCount = weekCount
            self.state = self.registration
            self.week = 0

        def advanceState(self):
            if self.state == self.finished:
                return
            elif self.state != self.started:
                self.state += 1
            else:
                self.week += 1
                if self.week == self.weekCount:
                    self.state += 1

        def isInRegistration(self):
            return self.state == 0

        def isInPreseason(self):
            return self.state == 1

        def isStarted(self):
            return self.state == 2

        def isInPlayoffs(self):
            return self.state == 3

        def isFinished(self):
            return self.state == 4

        def __str__(self):
            if self.state == 0:
                return "[SeasonState: registration]"
            elif self.state == 1:
                return "[SeasonState: preseason]"
            elif self.state == 2:
                return "[SeasonState: started week: %d]" % self.week
            elif self.state == 3:
                return "[SeasonState: playoffs]"
            elif self.state == 4:
                return "[SeasonState: finished]"

    ###############################################################################
    ## Rare pool card
    @jsonSerializableObj
    class RarePoolCard():
        def __init__(self, id=0):
            self.id = id
            self.count = 1

         
    ###############################################################################
    ## Season impl

    def __init__(self, db = None, setname = ""):
        self.set = setname
        self.registeredPlayers = []
        self.matches = []
        self.rarePool = []
        self.db = db
        self.startDate = datetime.datetime.now().isoformat(' ')
        self.seasonLength = 7
        self.state = self.SeasonState()
    
    def __str__(self):
        return "[season set: %s, players: %d, rarePool: %d]" % (self.set, len(self.registeredPlayers), len(self.rarePool))

    def shouldSerialize(self, k):
        if k == "db":
            return False
        else:
            return super().shouldSerialize(k)

    def advanceState(self):
        prevState = self.state.state
        self.state.advanceState()
        newState = self.state.state
        if newState == self.SeasonState.preseason:
            self.generateMatches()
        self.db.save()

    def exchangeRareForToken(self, playerId, cardId):
        rare = next((r for r in self.rarePool if r.id == cardId), False)
        if rare:
            rare.count += 1
        else:
            self.rarePool += [RarePoolCard(cardId)]

        playerInfo = self.getPlayerInfo(playerId)
        if not playerInfo:
            return False

        playerInfo.rareTokens += 1
        self.db.save()

    def isMatchup(self, p1, p2):
        return next((m for m in self.matches if m.isMatchup(p1, p2)), False)
    
    def generateMatches(self):
        matchups = [[self.Match(p1.playerId, p2.playerId) for p2 in self.registeredPlayers if p1.playerId != p2.playerId] for p1 in self.registeredPlayers]
        matchups = [random.sample(playerMatchups, len(playerMatchups)) for playerMatchups in matchups]
        
        for playerMatchups in matchups:
            weekNum = min(self.seasonLength, len(matchups[0]))
            self.seasonLength = weekNum # if not enough players, will be lower
            for w in range(weekNum):
                nextOpponent = next((m for m in playerMatchups if not self.isMatchup(m.p1, m.p2)), False)
                if nextOpponent:
                    nextOpponent.week = w
                    self.matches += [nextOpponent]
        self.db.save()

    def updateMatchScore(self, p1Name, p2Name, p1Score, p2Score):
        players = PlayersDB.load()
        p1 = players.get(p1Name)
        p2 = players.get(p2Name)
        match = next((m for m in self.matches if m.isMatchup(p1.id, p2.id)), False)
        if (match):
            match.score = (p1Score, p2Score)
            self.db.save()

    def registerPlayer(self, name, deckColors = []):
        players = PlayersDB.load()
        playerData = players.add(name) # ensure player is in player db
        playerInfo = next((p for p in self.registeredPlayers if playerData.id == p.playerId), False)
        if playerInfo:
            playerInfo.deckColors = deckColors
        else:
            self.registeredPlayers += [Season.PlayerInfo(playerData.id, deckColors)]
        self.db.save()

    def unregisterPlayer(self, id):
        self.registeredPlayers = [p for p in self.registeredPlayers if p.playerId != id]
        self.db.save()
        return True

    def getPlayerInfo(self, id):
        pInfo = next((p for p in self.registeredPlayers if p.playerId == id), False)
        return pInfo

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
        self.db.save()

    def removeRaresFromPool(self, cardIds):
        for rareId in cardIds:
            for r in self.rarePool:
                if r['id'] == rareId:
                    r['count'] -= 1
        self.rarePool = [r for r in self.rarePool if r['count'] > 0]
        self.db.save()

@jsonSerializableObj
class SeasonsDB(PersistentObject):
    savepath = 'seasons.dat'

    def __init__(self):
        self.seasons = []

    def __str__(self):
        out = "[SeasonsDB ["
        for s in self.seasons:
            out += "%s, " % s.set
        return out + "]"

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
        for s in self.seasons:
            if (s.set == setname):
                return s
        return False

    def getLatestSeason(self):
        seasonCount = len(self.seasons)
        if (seasonCount == 0):
            return False
        else:
            return self.seasons[seasonCount-1]

    @staticmethod
    def reset():
        SeasonsDB().save()

###############################################################################
## /players_api

@app.route('/players_api', methods=['POST', 'GET'])
def players_api():
    cmd = request.args.get('cmd','')
    playersDB = PlayersDB.load()
    if cmd == 'getDB':
        return json.dumps(playersDB.toJson()), 200
    else:
        return 'invalid cmd', 400 # bad request

###############################################################################
## /season_api

@app.route('/season_api', methods=['POST', 'GET'])
def season_api():
    cmd = request.args.get('cmd','')
    seasonsDB = SeasonsDB.load()
    currentSeason = seasonsDB.getLatestSeason()
    if cmd == 'register':
        set = request.args.get('set','')
        name = request.args.get('player','')
        season = seasonsDB.getSeason(set)
        if not season:
            return "no seasons started", 404 # not found
        elif name == "":
            return "invalid player name", 406 # not acceptable
        else:
            season.registerPlayer(name)
            return "registered player: %s" % name, 200 # OK
    elif cmd == 'new':
        set = request.args.get('set','')
        if set == "":
            return "invalid set name...", 406 # not acceptable
        else:
            if seasonsDB.newSeason(set):
                return "started season: %s" % set, 201 # created
            else:
                return "couldn't start new season %s" % set, 406 # not acceptable
    elif cmd == 'getSeason':
        set = request.args.get('set','')
        season = next((s for s in seasonsDB.seasons if s.set == set), False)
        if not bool(season):
            return 'false', 200
        else:
            return json.dumps(season.toJson()), 200

    elif cmd == 'getMatches':
        set = request.args.get('seasonSet','')
        week = request.args.get('week','')
        season = next((s for s in seasonsDB.seasons if s.set == set), False)
        if not bool(season) or week == '':
            return "bad request", 406 # not acceptable
        return JsonSerializable.valueToJson([m for m in season.matches if m.week == week]), 200

    elif cmd == 'reset':
        set = request.args.get('set','')
        sure = request.args.get('AREYOUSURE','')
        if sure == "YES":
            seasonsDB.seasons = [s for s in seasonsDB.seasons if s.set != set]
            seasonsDB.save()
            return "", 200
    elif cmd == 'unregister':
        set = request.args.get('set','')
        playerId = request.args.get('playerId','')
        season = seasonsDB.getSeason(set)
        if season and season.unregisterPlayer(playerId):
            return 'done', 200
        return 'failed to delete player %s' % playerId, 400 # bad request
    elif cmd == 'advance':
        set = request.args.get('set','')
        season = seasonsDB.getSeason(set)
        if season:
            season.advanceState()
            return "OK", 200
        
    return "unknown command", 400 # bad request

###############################################################################
## /season

@app.route('/season', methods=['POST', 'GET'])
def season():
    page = ""
    sets = Set.all()
    sets = [s for s in sets if s.type == 'core' or s.type == 'expansion']
    list.sort(sets, key=lambda s: s.release_date, reverse=True)
    page += "<script src='static/mtgleague.js?test=%s'></script>" % uuid.uuid4()
    page += "<h1>MTG League Season</h1>"
    page += '<select id="setname" onchange="newSeason.updateStatus()">'
    for set in sets:
        setId = set.code
        setInfo = "%s [%s - %s]" % (set.name, set.type, set.release_date)
        page += "<option value='%s'>%s</option>" % (setId, setInfo)
    page += '</select>'
    page += '<button onclick="newSeason.create()" id="createButton">create</button>'
    page += '<button onclick="newSeason.reset()" id="resetButton">reset</button>'
    page += '<br/>'
    page += '<div>status: <span id="status"></div>'
    page += '<div id="season-state-div">state: <span id="season-state"></span>'
    page += '<button onclick="newSeason.advance()" id="advanceButton">advance</button>'
    page += '</div>' # season-state
    page += '<div id="SeasonContent">'
    page += '<div id="Players"><h2>Players</h2>'
    page += '<div id="player-registration">'
    page += '<input type="text" id="newPlayerName" placeholder="Please use your office login"/><button onclick="newSeason.registerPlayer()">register</button>'
    page += '</div>' # player-registration
    page += '<table id="players-table"></table>'
    page += '</div>' # Players
    page += '<div id="Matches"><h2>Matches</h2><select id="match-week" onchange="newSeason.updateMatches()"></select>'
    page += '<table id="match-table"></table>'
    page += '</div>' # Matches
    page += '</div>' # SeasonContent
    page += '''
<script type='text/javascript'>
    window.onload = newSeason.updateStatus()
    var playerNameInput = document.getElementById('newPlayerName')
    playerNameInput.addEventListener("keydown", function(evt) {
                                                    if (evt.keyCode == 13) {
                                                        newSeason.registerPlayer() ;
                                                        playerNameInput.value=""
                                                }})
</script>'''
    return page

###############################################################################
## /reset

# @app.route('/reset', methods=['POST', 'GET'])
# def reset():
    
        
###############################################################################
## main

if __name__ == '__main__':
    app.run(debug=True)
