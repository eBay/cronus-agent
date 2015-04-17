/**
********************************************************************************
SAPPHIRE_LIB contains all the share methods used by all the page.

Index: 
1 - ajaxCall
2 - drawChart
3 - drawLineChart
4 - drawStockChart
5 - getRangeDataPoints
6 - getRangeArray
7 - arrayContains
8 - arrayRemoveByValue
9 - setObjectLocalStorage
10 - getObjectLocalStorage
11 - initTypeAhead
12 - formatDataPointsfromTSDB
13 - initToolTip
14 - getToolTip
********************************************************************************
**/
var SAPPHIRE_LIB = SAPPHIRE_LIB ? SAPPHIRE_LIB : {};
var _ = _ ? _ : {};
var console = console ? console : {log: function () {}, dir: function () {} };
var Highcharts = Highcharts ? Highcharts : {};
var $ = $ ? $ : {};

/*
	ajaxCall() is a wrap-up function for asynchronous.
	url: the API addresss
	datatype: 'json'/'jsonp'/'text'
	callback: the callback function that handles the response
	errorcallback: optional. the error callback that handles the error/exception
	
	//Jeff SAPPHIRE_LIB is a big obj; .ajaxCall is a small object inside of the SAPPHIRE_LIB
	// return a ajax object. like a constructor
	
		nodes_ajax[i] = SAPPHIRE_LIB.ajaxCall(nodes_list_url+that.page_config.profile_names[i], 'json', 
						_.bind(function(resp){
							this.nodes_list.push({profile: that.page_config.profile_names[i], nodes: resp});
						}, that));		
	
	
*/
SAPPHIRE_LIB.ajaxCall = function(url, datatype, callback, errorcallback){
	if(url==undefined||url==""||datatype==""||datatype==undefined||callback==undefined){
		return {};
	}



	if(datatype === 'jsonp'){
		url = url+"?callback=?";
	}
	return $.ajax({
		url: url,
		dataType : datatype,
		success: function(response){
			callback(response);
		},
		error: function(resp){
			if(errorcallback!==undefined){
				console.log('error reading from'+ url);
				errorcallback(resp);
			}else{
				console.log('error reading from'+ url);
				console.log(resp);
				console.dir(resp);
				
			}
		}
	});
};

/*
	drawChart() is used to draw the line chart for key metrics page.
	container: the container of the chart
	data: the data for the chart. {name: THENAME, data: THEDATA}
	// All fqdn is multi seires KT the data is actually the one up level: data should not be the array; but should be  {name: THENAME, data: THEDATA}
	chtheight, chtwidth: the height and width of the chart
	minvalue, maxvalue: the minvalue of the data, the maxvalue of the data
*/
SAPPHIRE_LIB.drawChart = function(container, data, title, subtitle, chtheight, chtwidth, minvalue, maxvalue){
		$(container).highcharts({
		chart : {
			type : 'spline',
			height : chtheight,
			width : chtwidth,
			borderWidth : 2,
		},
		title : {
			text : title
		},
		subtitle : {
			text : subtitle
		},
		xAxis : {
			type : 'datetime',
			title : {
				text : null
			},
			dateTimeLabelFormats : {
				second : '%H:%M:%S'
			}
		},
		yAxis : {
			title : {
				text : ""
			},
			min: minvalue,
			max: maxvalue
		},
		tooltip : {
			shared : true
		},
		plotOptions : {
			spline: {
				marker: {
					enabled : false
				}
			}
		},
		exporting : {
			enabled : false
		},
		credits : {
			enabled : false
		},

		legend : {
			enabled : false
		},

		tooltip: {
			formatter: function() {
			return ''+
			Highcharts.dateFormat('%a.%d.%b %H:%M:%S', this.x) +': '+ 
			Highcharts.numberFormat(this.y, 3);
			}
		},     


		series : data
	});

};

/*
	drawLineChart() is used for plot the line chart at full page/ detail page.
	parameters: refer to the drawChart method parameters
	KT not interchangable with drawChart. Weird
*/
SAPPHIRE_LIB.drawLineChart = function(container, data, title, subtitle, chtheight, chtwidth, minvalue, maxvalue){
	var options = {
			chart: {
				renderTo: container,
				type : 'spline',
			},
			title : {
				text : title,
			},
			subtitle : {
				text : subtitle,
			},
			xAxis: {
				title: {
					text: " "
				},
				type: "datetime",
			},
			yAxis: {
				title: {
					text: " "
				}
			},
			plotOptions: {
				series : {
					lineWidth : 2
				},
				spline : {
					marker : {
						enabled : false
					},
				},
			},
			tooltip : {
				shared : true
			},
			exporting : {
				enabled : false
			},
			credits : {
				enabled : false
			},
			legend : {
				enabled : false
			},
			series: data
		};

		if(chtheight!=undefined&&chtwidth!=undefined){
				options.chart.height = chtheight;
				options.chart.width = chtwidth;
		}
		if(minvalue!=undefined&&maxvalue!=undefined){
			options.yAxis.min = minvalue;
			options.yAxis.max = maxvalue;
		}
		// console.dir(options);
		var chart = new Highcharts.Chart(options);
};
/*
	drawStockChart() is used to draw the stock chart with zoom.
	
	data: the data series for the chart. {name: THENAME, data: THEDATA}
	KT for detail chart.
*/
SAPPHIRE_LIB.drawStockChart = function(container, data, title, subtitle){

	console.log(title+subtitle);
	var thechart = 
		$(container).highcharts('StockChart', {
			rangeSelector : {
				enabled : false
			},
			credits : {
				enabled : false
			},
			title : {
				text : title,
			},
			subtitle : {
				text: subtitle,
			},
			tooltip: {
				formatter: function() {
				return ''+
				Highcharts.dateFormat('%a.%d.%b %H:%M:%S', this.x) +': '+ 
				Highcharts.numberFormat(this.y, 3);
				}
			},    			
			series : data
		});
};
/*
	getRangeArray() is the helper method to get the min value and max value of one array/2d array
	return {max: maxvalue, min: minvalue}
	
	
*/
SAPPHIRE_LIB.getRangeArray = function(array){
	if(array.length===0){
		return {
			max : undefined,
			min : undefined
		}
	}

	// get Range Array for 2-D array, used for datapoints
	// asssuming [i][0] is the time stamp
	if(array[0][1]!==undefined){
		var newarray = [];
		for(var i in array){
			newarray.push(array[i][1]);
			// console.log(typeof array[i]);
		}
	}else{
		newarray = array;
	}
	
	var maxv = Math.max.apply(Math, newarray);
	var minv = Math.min.apply(Math, newarray);
	// console.log("max: "+maxv+"--- min: "+minv);
	return {
		max : maxv,
		min : minv
	}
};
/*
	arrayContains() is the helper method to get if the array contains a certain element.
*/
SAPPHIRE_LIB.arrayContains = function(sourceArray, target){
	if(target===undefined||target===null||target===""||sourceArray.length===0||sourceArray===undefined){
		return false;
	}
		for(var i = 0; i<sourceArray.length;i++){
			// console.log(sourceArray[i]+"*****"+target+"***"+(sourceArray[i] === target)+(sourceArray[i] == target));
			if (sourceArray[i] === target) {
				console.log(sourceArray[i]+" ****** "+target);
				return true;
			}
	}
	return false;
};
/*
	arrayRemoveByValue() is the helper method to remove a certain element in a array, given it's value.
*/
SAPPHIRE_LIB.arrayRemoveByValue = function(sourceArray, target){

	if(target===undefined||target===""||sourceArray.length===0||sourceArray==="undefined"){
		return false;
	}
		for(var i=0; i<sourcearray.length; i++) {
	        if(sourcearray[i] == val) {
	            sourcearray.splice(i, 1);
	            break;
	        }
    }
};

/*
	setObjectLocalStorage() is a wrapper for window.LocalStorage.setItem().
	it saves the object as a JSON format.
	
	KT in localStore, save as <string,string>
*/
SAPPHIRE_LIB.setObjectLocalStorage = function(key, object){
	window.localStorage.setItem(key, JSON.stringify(object));
};

/*
	getObjectLocalStorage() is a wrapper for window.LocalStorage.getItem().
	it read the JSON/string to a Object/string.
*/
SAPPHIRE_LIB.getObjectLocalStorage = function(key){	
	var value = window.localStorage.getItem(key);
	console.log(value);
	console.log(key);
    return value && JSON.parse(value);
};
/*
	initTypeAhead() is used to init the select using SELECT2.
	passtext: the default place holder
*/
SAPPHIRE_LIB.initTypeAhead = function(elem, dataarray, passtext){
	// console.log(dataarray);
	//nested array...
	if( dataarray[0].profile!=undefined){
		//2 nested for loop cluster-> node level
		$.each(dataarray, function(i, v) {
			var a = $('<optgroup>').attr('label', v.profile).appendTo($(elem));
			$.each(v.nodes, function(index, value){
				$('<option>').text(value).appendTo($(a));
			});
			
		})
	}else{
		// console.log("array");
		$.each(dataarray, function(i,v){
			$('<option>').text(v).appendTo(elem);
		});
	}
	//console.log('text:' + text);
	$(elem).select2({
		placeholder : passtext,
		allowClear : true
	});
};

/*
	formatDataPointsfromTSDB() is used to format the datapoints(timestamp) for the highchart/highstock plotting.
	111111111  ->  111111111000
	TSDB is SEC; highchart is MS. need to convert to highchart way
*/
SAPPHIRE_LIB.formatDataPointsfromTSDB = function(data){
		$.each(data, function(i,v){
		v[0] = v[0]*1000;
	});
	return data;
};
/*
	initToolTip() will init the tooltip for the elem by calling the getToolTip() to get the text.
	
	KT: elem is the DOM; which already have the metadata appeneded; now is to generate the tool tip with content of HTML string "result"
*/
SAPPHIRE_LIB.initToolTip = function(elem) {
	var that = this;
	$(elem).qtip({
		style : {
			classes : 'qtip-bootstrap qtip-shadow qtip-rounded',
		},
		show : {
			delay : 0
		},
		position : {
			my : 'top left',
			at : 'bottom right'
		},
		content : {
			text : function(api) {

				return that.getToolTip($(this));
			}
		}
	});
};
/*
	getToolTip() is used to get the attribute of one element to format the text for tooltip.
*/
SAPPHIRE_LIB.getToolTip = function(elem){
	var arr = [];
	var dom = elem.get(0);
	for ( var i = 0, attrs = dom.attributes, l = attrs.length; i < l; i++) {
		var n = attrs.item(i).nodeName;
		if (n != "hostname" && n != "class" && n.indexOf("aria") != 0)
			arr.push(attrs.item(i).nodeName);
	}
	var result = new String();
	for ( var i in arr) {
		if (arr[i] !== "data-hasqtip" && arr[i] !== 'unit')
			result += "<b>" + arr[i] + " : </b>" + elem.attr(arr[i]) + "<br/>";
	}
	return result;
};

/*
	remove the non-number/non-letter element
*/
SAPPHIRE_LIB.cleanNameWithOnlyLettersNumbers = function(name){
	if(name===null||name===undefined||name===""){
		return null;
	}
	var regex = new RegExp('[^A-Za-z0-9]', 'g');
	return name.replace(regex,"");
}
/*
	ASSUMPTION: Metric Format: "mpdb.mysq.XXX.STATE.10s" or "stratus.XXXXXX.STATE.60s"
*/
SAPPHIRE_LIB.shortenMetricName = function(metricname, profilename){

	if(metricname===null||metricname===""||metricname==="undefined"||profilename==='undefined'||profilename===""){

		return "undefined";
	}else{
		/*if the profilename include "_", such as mpdb_cassandra, transfer to mpdb.cassandra*/
		if(profilename.indexOf("_")!=-1){ 
			profilename = profilename.split('_');
			$.each(profilename, function(i,v){
				if(metricname.indexOf(v)!=-1){
					/*if the metricname open with the profilename. "mpdb.mysql.XXXX.STATE.10s"*/
					metricname = metricname.substring(metricname.indexOf(v)+1+v.length);
				}
			});
		}else{
			if(metricname.indexOf(profilename)!=-1){
				/*if the metricname open with the profilename. "mpdb.mysql.XXXX.STATE.10s"*/
				metricname = metricname.substring(metricname.indexOf(profilename)+1+profilename.length);
			}
		}
		//if passing in metrics name with ".STATE.XXs"
		if(metricname.indexOf(".STATE.")!=-1){
			metricname = metricname.substring(0, metricname.indexOf('.STATE.'));
		}
		// console.log(metricname);
		// console.log("************************************");
		return metricname;
	}
}
