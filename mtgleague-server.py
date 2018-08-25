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

class Player:
    def __init__(self, name):
        self.name = name
        self.colros = []

class PlayersDB:
    player_data_file = 'd:/players.dat'
    
    def __init__(self):
        self.players = []

    def add(self, newPlayer):
        alreadyThere = list(filter(lambda x: x.name == newPlayer.name, self.players)) != []
        if not alreadyThere:
            self.players += [newPlayer]
            return True
        else:
            return False

    def save(self):
        pickle.dump(self, open(PlayersDB.player_data_file, "wb+"))

    @staticmethod
    def load():
        data = PlayersDB()
        if os.path.isfile(PlayersDB.player_data_file):
            data = pickle.load(open(PlayersDB.player_data_file, "rb"))
        return data

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
        

if __name__ == '__main__':
    app.run(debug=True)
