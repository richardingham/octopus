
window.Graphset = function ($, graphs) {
	return function (el, trace, width, height) {
	
		//var colours = [];
		//for (var i in streams) {
		//	colours[i] = streams[i].colour;
		//};
		
		var graph = this;
		var gutter = 40;
		var data = trace.data;
		
		// Make sure the graph starts at zero.
		data.valuesy.push([0]);
		
		var opts = {
			axis:      ["0 0 1 1"],
			//axisxstep: Math.floor((width - 2 * gutter) / 20),
			//axisystep: Math.min(Math.floor((height - 2 * gutter) / 20)),
			//colors:    colours,
			gutter:    gutter
		};
		
		graphs.push({
			graph: graph,
			streams: trace.streams.map(function (s) { return s.name; })
		});
		
		function draw () {
			var r = Raphael(el, width, height);
			var chart = r.linechart(0, 0, width, height, data.valuesx, data.valuesy, opts);
			
			var labels = chart.axis[0].text.items;      
			for (var i in labels){
				var d = new Date(parseInt(labels[i].attr('text')));
				labels[i].attr({text: d.toTimeString().substr(0, 8)});
			};
			
			/* var last_x = data.valuesx[data.valuesx.length - 1];
			for (var i in trace.streams) {
				var stream = trace.streams[i];
				var value  = data.valuesy[i][data.valuesx.length - 1];
				
				r.popup(last_x, value, stream.title + ": " + value + " " + trace.unit);
				r.label(last_x, 100, stream.title + ": " + value + " " + trace.unit);
			} */
		}
		
		this.append = function (stream_data, start, step) {
			var count;
		
			if (stream_data[0]) {
				count = stream_data[0].length;

				for (var i = 0; i < count; i++)
					data.valuesx[data.valuesx.length] = start + (step * i);

				data.valuesx.splice(0, count);
			}

			for (var i in stream_data) {
				for (var j in stream_data[i])
					data.valuesy[i][data.valuesy[i].length] = stream_data[i][j];

				data.valuesy[i].splice(0, count);
			}

			$(el).empty();

			draw();
		};
		
		draw();
	};
};
