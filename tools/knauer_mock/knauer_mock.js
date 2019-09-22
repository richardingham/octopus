var net = require('net');

var server = net.createServer();  

server.on('connection', handleConnection);

server.listen(8050, function() {  
    console.log('server listening to %j', server.address());
});

function handleConnection(conn) {  
    var remoteAddress = conn.remoteAddress + ':' + conn.remotePort;
    var flowRate = 0;
    var power = false;

    console.log('new client connection from %s', remoteAddress);

    conn.setEncoding('utf8');

    conn.on('data', onConnData);
    conn.once('close', onConnClose);
    conn.on('error', onConnError);

    var buffer = '';

    function onConnData (data) {
        console.log(">" + data);
        var prev = 0, next;
        data = data.toString('utf8'); // assuming utf8 data...
        while ((next = data.indexOf('\r', prev)) > -1) {
            buffer += data.substring(prev, next);

            handleMessage(buffer);

            buffer = '';
            prev = next + 1;
        }
        buffer += data.substring(prev);
    }

    function handleMessage(message) {
        if (message == "S?") {
            connWrite("S" + (power ? "0" : "\x10") + "\x00");
        } else if (message == "F?") {
            connWrite("F" + flowRate.toString() + "\r");
        } else if (message == "V?") {
            connWrite("V03.30\r");
        } else if (message == "M0") {
            power = false;
            connWrite("OK\r")
        } else if (message == "M1") {
            power = true;
            connWrite("OK\r")
        } else if (message[0] == "F") {
            flowRate = parseInt(message.slice(1));
            connWrite("OK\r")
        }
    }

    function connWrite(data) {
        console.log("<" + data);
        conn.write(data);
    }

    function onConnClose() {
        console.log('connection from %s closed', remoteAddress);
    }

    function onConnError(err) {
        console.log('Connection %s error: %s', remoteAddress, err.message);
    }
}