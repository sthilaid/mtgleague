class newSeason
{
	static create()
	{
		var setnameOption = document.getElementById('setname');
		var setid = setnameOption.value
		if (setnameOption)
		{
			var xhttp =  new XMLHttpRequest();
			xhttp.onreadystatechange = function() {
				if (xhttp.readyState != 4)
					return;
				var color = xhttp.status == 201 ? "green" : "red"
				newSeason.setStatus(xhttp.responseText, false, "green");
			};
			xhttp.open("GET", "/season_api?cmd=new&set="+setid, true);
			xhttp.send();
		}
	}

	static reset()
	{
		var setnameOption = document.getElementById('setname');
		var setid = setnameOption.value
		if (setnameOption)
		{
			if (window.confirm("Are you sure you want to reset season '"+setid+"'?"))
			{
				var xhttp =  new XMLHttpRequest();
				xhttp.onreadystatechange = function() {
					if (xhttp.readyState != 4)
						return;
					alert("season reset")
					newSeason.updateStatus()
				};
				xhttp.open("GET", "/season_api?cmd=reset&set="+setid+"&AREYOUSURE=YES", true);
				xhttp.send();
			}
		}
	}


	static updateStatus()
	{
		var setnameOption = document.getElementById('setname');
		var setid = setnameOption.value
		var xhttp =  new XMLHttpRequest();
		xhttp.onreadystatechange = function() {
			if (xhttp.readyState != 4)
				return;
			var isExisting = xhttp.responseText != "false"
			if (isExisting)
				newSeason.selectedSeason = JSON.parse(xhttp.responseText)
			else
				newSeason.selectedSeason = null

			newSeason.updateStatusWithSeason()
		};
		xhttp.open("GET", "/season_api?cmd=getSeason&set="+setid, true);
		xhttp.send();		
	}

	static updatePlayersDB()
	{
		if (newSeason.playersDBRequest != null)
			return;
		
		newSeason.playersDBRequest =  new XMLHttpRequest();
		newSeason.playersDBRequest.onreadystatechange = function() {
			if (newSeason.playersDBRequest.readyState != 4)
				return;

			if (newSeason.playersDBRequest.status != 200)
				newSeason.playersDB = null
			else
			{
				var db = JSON.parse(newSeason.playersDBRequest.responseText)
				newSeason.playersDB = db ? db[1] : null
				newSeason.updateStatusWithSeason()
			}
			newSeason.playersDBRequest = null
		};
		newSeason.playersDBRequest.open("GET", "/players_api?cmd=getDB", true);
		newSeason.playersDBRequest.send();		
	}

	static getPlayerNameFromId(id)
	{
		if (newSeason.playersDB == null)
			return id

		for(var i=0; i<newSeason.playersDB.players.length; ++i)
		{
			var playerData = newSeason.playersDB.players[i][1]
			if (playerData.id == id)
				return playerData.name
		}
		return id
	}

	static deleteAllChilds(element)
	{
		while(element.firstChild)
			element.removeChild(element.firstChild);
	}

	static registerPlayer()
	{
		var setnameOption = document.getElementById('setname');
		var setid = setnameOption.value
		var nameInput = document.getElementById('newPlayerName')
		var xhttp =  new XMLHttpRequest();
		xhttp.onreadystatechange = function() {
			if (xhttp.readyState != 4)
				return;
			newSeason.playersDB = null // invalidate players cached data
			newSeason.updateStatus()
		};
		xhttp.open("GET", "/season_api?cmd=register&set="+setid+"&player="+nameInput.value, true);
		xhttp.send();
	}

	static deletePlayer(playerId)
	{
		var setnameOption = document.getElementById('setname');
		var setid = setnameOption.value
		var xhttp =  new XMLHttpRequest();
		xhttp.onreadystatechange = function() {
			if (xhttp.readyState != 4)
				return;
			newSeason.updateStatus()
		};
		xhttp.open("GET", "/season_api?cmd=unregister&set="+setid+"&playerId="+playerId, true);
		xhttp.send();
	}

	static updateStatusWithSeason()
	{
		var seasonContent = document.getElementById('SeasonContent');
		if (newSeason.selectedSeason == null)
		{
			newSeason.setStatus("Set available", true, "green")
			seasonContent.style.display = 'none'
			return;
		}
		else if (newSeason.playersDB == null)
		{
			newSeason.updatePlayersDB()
			return;
		}
		var season = newSeason.selectedSeason[1]
		newSeason.setStatus(season['startDate'], false, "red")

		seasonContent.style.display = 'block'

		// Players
		var playersTable = document.getElementById("players-table")
		{
			newSeason.deleteAllChilds(playersTable)

			var thead = playersTable.createTHead();
			thead.innerHTML = "<td>Name</td><td>Rare Tokens</td>"

			var tbody = document.createElement("tbody")
			playersTable.appendChild(tbody)

			for(var i=0; i<season.registeredPlayers.length; ++i)
			{
				var playerData = season.registeredPlayers[i][1]
				var row = tbody.insertRow(-1)
				var playerName = newSeason.getPlayerNameFromId(playerData.playerId)
				row.innerHTML = "<td>"+playerName+"</td>"
					+"<td>"+playerData.rareTokens+"</td>"
					+"<td><button onclick='newSeason.deletePlayer(\""+playerData.playerId+"\")'>X</button></td>"
			}
		}

		// Matches
		var matches = season['matches']
		var matchesEl = document.getElementById('Matches');
		if (matches == null || matches.length == 0)
			matchesEl.style.display = 'none'
		else
		{
			matchesEl.style.display = 'block'

			var matchWeekOption = document.getElementById('match-week')
			newSeason.deleteAllChilds(matchWeekOption)

			for(var w=0; w<season.seasonLength; ++w)
			{
				var weekOption = document.createElement("option")
				weekOption.value = w
				weekOption.textContent = "Week "+(w+1)
				matchWeekOption.appendChild(weekOption)
			}
			newSeason.updateMatches()
		}
	}

	static setStatus(status, okToCreate, color)
	{
		var statusEl = document.getElementById('status');
		statusEl.textContent = status
		statusEl.style.color = color

		var button = document.getElementById('createButton');
		button.style.display = okToCreate ? 'inline' : 'none'

		var button = document.getElementById('resetButton');
		button.style.display = okToCreate ? 'none' : 'inline'
	}

	static updateMatches()
	{
		if (newSeason.selectedSeason == null)
			return;
		
		var matchWeekOption = document.getElementById('match-week')
		var weekNum = matchWeekOption.value
		var matches = newSeason.selectedSeason[1]['matches']
		var matchTable = document.getElementById('match-table');
		newSeason.deleteAllChilds(matchTable)

		var thead = matchTable.createTHead();
		thead.innerHTML = "<td>Player1</td><td>Score</td><td>Player2</td><td>Score</td>"

		var tbody = document.createElement("tbody")
		matchTable.appendChild(tbody)
		for(var i=0; i<matches.length; ++i)
		{
			var matchData = matches[i][1]
			if (matchData.week != weekNum)
				continue;
			var row = tbody.insertRow(-1)
			var p1Name = newSeason.getPlayerNameFromId(matchData.p1)
			var p2Name = newSeason.getPlayerNameFromId(matchData.p2)
			row.innerHTML = "<td>"+p1Name+"</td><td>"+matchData.score[0]+"</td><td>"
				+p2Name+"</td><td>"+matchData.score[1]+"</td>"
		}
	}
}
newSeason.selectedSeason = null		// static var def
newSeason.playersDB = null			// static var def
newSeason.playersDBRequest = null	// static var def
