/*
 * Installation: Requires node.js (for windows).
 *
 * www.nodejs.org
 *
 * Configuration: Set iC IR to Auto-Export Trend Data with a file 
 * format of ${Date}_{$Time}_TrendData so that all of the files
 * end up in the same directory.
 *
 * This script checks this directory and picks data from the
 * file with the greatest filename. It updates the internal data as
 * new files are added.
 *
 * You may need to open port 
 *
 * Usage: node irserver.js
 * 
 * Ctrl+C to quit.
 */
 
var net = require('net');
var fs  = require('fs');

var directory = "C:\\Documents and Settings\\Administrator\\My Documents\\IR-Export\\";

var server = net.createServer(function (socket) {

	console.log('client connected');
	socket.on('close', function () {
		console.log('client disconnected');
	});

	var 
	buffer = "",
	encoding = "utf8",
	delimeter = "\r\n"
	delimeterLength = delimeter.length;

	socket.on('data', function (data) {
		buffer += data;

		var pos = buffer.indexOf(delimeter);
		if (pos !== -1) {
			var line = buffer.substring(0, pos);
			buffer = buffer.substring(pos + delimeterLength);

			//console.log("Request:", line);

			action(line, function (error, response) {
				if (error) {
					//console.error(error);
					socket.write("error" + delimeter, encoding);
				} else {
					//console.log("Response:", response);
					socket.write(response + delimeter, encoding);
				}
			});
		}
	
	});	
});

var lastData = {
	time: null,
	streams: []
};

function action (req, callback) {
	updateStreams(function (error) {
		if (error) callback(error);

		if (req === "requestData") {
			return callback(null, JSON.stringify(lastData));
		}
	});
}

function updateStreams (callback) {
	fs.readdir(directory, function (error, dirlist) {
		if (error) callback(error);

		var latestFile = "";

		//console.log("dirlist", dirlist);

		dirlist.forEach(function (fileName) {
			if (fileName.substr(-13) === "TrendData.txt")
				if (fileName > latestFile)
					latestFile = fileName;
		});

		if (latestFile.length) {
			//console.log("Using data file", latestFile);
			return readFile(directory + latestFile, callback);
		} else {
			return callback();
		}
	});
}

function readFile (fileName, callback) {
	fs.readFile(fileName, 'utf8', function (error, data) {
		if (error) callback(error);

		var lines = data.split("\n").map(function (line) { return line.trim().split(",").map(function (v) { return v.slice(1,-1).trim(); }); });
		var data = {
			time: (new Date(lines.shift()[1])).valueOf(),
			streams: []
		};

		lines.forEach(function (line) {
			if (line[0] === "") return;

			data.streams.push({
				name: line[0],
				value: parseFloat(line[1])
			});
		});

		//console.log("Extracted data:", data);

		lastData = data;

		callback();
	});
}

var port = 8124;
server.listen(port, function () {
	console.log('IR Data server listening on port ' + port);
});
