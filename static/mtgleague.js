class newSeason
{
	static send()
	{
		var setnameOption = document.getElementById('setname');
		var setid = setnameOption.value
		alert('id: '+setid)
		if (setnameOption)
		{
			var xhttp =  new XMLHttpRequest();
			xhttp.onreadystatechange = function() {
				alert("xhttp.status: "+ xhttp.status)
				if (xhttp.status == 200)
					newSeason.setStatus("season created")
				else
					newSeason.setStatus("failed to create season...")
			};
			xhttp.open("GET", "season?cmd='new'&set="+setid, true);
			xhttp.send();
		}
	}

	static updateStatus()
	{
		alert('updateStatus()')
	}

	static setStatus(status)
	{
		var statusEl = document.getElementById('status');
		statusEl.value = status
	}
}
