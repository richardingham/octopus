/*
 * Installation: Requires node.js (for windows).
 *
 * www.nodejs.org
 *
 * Configuration: Set iC IR to Auto-Export Trend Data with a file 
 * format of ${Date}_{$Time}_TrendData so that all of the files
 * end up in the same directory.
 *
 * Update directory variable below to reflect the folder.
 *
 * This script checks this directory and picks data from the
 * file with the greatest filename. It updates the internal data as
 * new files are added.
 *
 * You may need to open port 8124.
 *
 * Usage: node irserver.js
 * 
 * Ctrl+C to quit.
 */
 
var net  = require('net');
var fs   = require('fs');
var path = require('path');

// Directory that will contain the data files
// NB the trailing "\\" is required.
var directory = "C:\\Users\\[my-user]\\IR-Export\\";

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

			action(line, function (error, response) {
				if (error) {
					socket.write("error" + delimeter, encoding);
				} else {
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

		dirlist.forEach(function (fileName) {
			if (fileName.substr(-13) === "TrendData.txt")
				if (fileName > latestFile)
					latestFile = fileName;
		});

		if (latestFile.length) {
			return readFile(directory + latestFile, callback);
		} else {
			return callback();
		}
	});
}

function readFile (fileName, callback) {
	fs.readFile(fileName, 'utf8', function (error, data) {
		if (error) callback(error);

		// Pull the time out of the filename. Expects the filename
		// to be in the format "YYYY-MM-DD_HH-MM-SS_TrendData.txt"
		// Uses the local timezone.
		var time = +(new (Function.bind.apply(
			Date, 
			path.basename(fileName).split("_").slice(0, 2).map(function (s) {
				// Produce an array of two arrays of integers.
				return s.split("-").map(function (n) {
					return +n;
				}; 
			}).reduce(function (p, c) {
				// Combine the two arrays
				return p.concat(c);
			}, [null]).map(function (n, i) {
				// Compensate for the fact that months are indexed 0-11
				return n - +(i === 2);
			})
		)));

		var data = {
			time: time,
			streams: []
		};

		var lines = data.split("\n").slice(1).map(function (line) {
			return line.trim().split(",").map(function (v) {
				return v.slice(1,-1).trim(); 
			}); 
		});

		lines.forEach(function (line) {
			if (line[0] === "") return;

			data.streams.push({
				name: line[0],
				value: parseFloat(line[1])
			});
		});

		lastData = data;

		callback();
	});
}

var port = 8124;
server.listen(port, function () {
	console.log('IR Data server listening on port ' + port);
});
