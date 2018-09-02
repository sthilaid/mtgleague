class newSeason
{
	static send()
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
				newSeason.setStatus(xhttp.responseText, false);
			};
			xhttp.open("GET", "/season-api?cmd=new&set="+setid, true);
			xhttp.send();
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
			var color = isExisting ? "red" : "green"
			var msg = isExisting ? "Season already started on " + xhttp.responseText + "..." : "Set available"
			newSeason.setStatus(msg, !isExisting, color)
		};
		xhttp.open("GET", "/season-api?cmd=isExisting&set="+setid, true);
		xhttp.send();		
	}

	static setStatus(status, okToSend, color)
	{
		var statusEl = document.getElementById('status');
		statusEl.textContent = status
		statusEl.style.color = color

		var button = document.getElementById('createButton');
		button.style.display = okToSend ? 'inline' : 'none'
	}
}
