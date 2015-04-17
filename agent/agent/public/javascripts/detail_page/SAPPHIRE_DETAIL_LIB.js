var SAPPHIRE_DETAIL_LIB = (function () {
	var sapphire_detail_lib =  function(page_config, metric_list, metric_res_ratio_on){
			this.page_config = page_config;
			this.metric_list = metric_list;
			this.currentRangeSelection = "1 Day"

			if(metric_res_ratio_on.toLowerCase().indexOf("true") != -1 ){
				this.metricInterval = "10 Seconds"	
			}else{
				this.metricInterval = "60 Seconds"	
				
			}
			console.log("this.metricInterval: " + this.metricInterval);
			

	};
	sapphire_detail_lib.prototype = {
		init: function(){
			this.fillList();  // KT the filter
			this.fillTheChart(); // KT: the "Metrics"
			this.fillDatePicker();
		},
		
		
		fillList: function(){
						
			SAPPHIRE_LIB.initTypeAhead('#searchMetrics',  this.metric_list, "Select a metric...");
			this.initDefaultOption('#searchMetrics', this.page_config.currentmetric);

		},
		
		fillTheChart: function(){
			// console.log(cluster_name);
			
			var container = 'div#detail_chart_container';
			this.readMetricDataFromUrl();
		},
		
		/**
		 * 20130909: now init load also from EVPS 
		 * /agent/getEvpsDataAsProxy
		 */
		readMetricDataFromUrl: function(){

			var duration = "1d-ago"
			var metricName = this.page_config.currentmetric
			var fqdn = this.page_config.currentfqdn
			var aggregateMethod = "avg"

			var getEvpsFromAgentProxyUrl = "/agent/getEvpsDataAsProxy/"+ duration + "/"+metricName+"/"+fqdn+"/" + aggregateMethod;

			$("div.modal_loader").show();

			this.getDataFromAgentProxyWithTSDB(this.page_config.currentmetric, this.page_config.currentfqdn, getEvpsFromAgentProxyUrl);
		},


		/*
		 * Jeff 20130910
		 */
		getDataFromAgentProxyWithTSDB:function(currentmetric, currentfqdn, proxyUrl){
			
		
			var that = this;
			/**
			 * JSON
			 * TIMEOUT 25 SEC. 
			 */
			$.ajax({
				url: proxyUrl,
				async: true,
				dataType: 'json', 
				timeout: 60000,
				success: function(data){

					console.log("GOT DATA in getDataFromTSDB");

	
					$("div.modal_loader").hide();
					var container = 'div#detail_chart_container';

					var dataPointsPtr = null;
					// handle exception; when no data coming in.
					if(!data ){
					
						$('div#detail_chart_container').css('background', 'url(/images/error.png) no-repeat center center' )
						$('div#detail_chart_container').empty();
						$('div#detail_chart_container').html('<h6>Response Empty from EVPS for metric:  '+currentmetric 
								+ ' It is expected that some disk and network metrics are only available in certain boxes. <br/><br/> DEBUG: </h6> '
						+ ' <a href=" '+ proxyUrl + ' " target="_blank" > Proxy URL</a> '
						+ '<br/><br/> <a href="/agent/monitors" target="_blank" > Agent URL</a> '
						);
						return;
					}else if(typeof data.DataPoints =='undefined'){

						if(data[0]){
							dataPointsPtr = data[0].DataPoints	
						}else{
							$('div#detail_chart_container').css('background', 'url(/images/error.png) no-repeat center center' )
							$('div#detail_chart_container').empty();
							$('div#detail_chart_container').html('<h6>Response Empty from EVPS for metric:  '+currentmetric 
									+ ' It is expected that some disk and network metrics are only available in certain boxes. <br/><br/> DEBUG: </h6> '
							+ ' <a href=" '+ proxyUrl + ' " target="_blank"> Proxy URL</a> '
							+ '<br/><br/> <a href="/agent/monitors" target="_blank"> Agent URL</a> '
							);
							return;
						}
						
					}else{
						dataPointsPtr = data.DataPoints	
					}	

				
					SAPPHIRE_LIB.drawStockChart(container, [{data:SAPPHIRE_LIB.formatDataPointsfromTSDB(dataPointsPtr)}],  that.page_config.currentmetric, that.page_config.currentfqdn);
				
				},
				error: function(){
					$("div.modal_loader").hide();
					$('div#detail_chart_container').empty();
					$('div#detail_chart_container').html('<h4>Bad Response from TSDB</h4><p>EVPS has timeout after 60 Seconds. Agent Proxy URL to EVPS: '+proxyUrl + '</p>');
				}
			});	
		},// end func
		
		/**
		 * KT calendar. date time picker
		 */
		fillDatePicker: function(){
			var currenttime = new Date();
			var defaultstarttime = new Date();
			defaultstarttime.setHours(currenttime.getHours()-1);
			// console.log(currenttime);
			// console.log(defaultstarttime);
			var earliestDate = new Date();
			$("#start_time_input").AnyTime_picker({
				format: "%Y/%m/%d-%T",
				firstDOW: 1,
				earliest: new Date(2013,0,1,0,0,0), 
			});
			$("#end_time_input").AnyTime_picker({
				format: "%Y/%m/%d-%T", 
				firstDOW: 1 
			});
		},
		
		/**
		 * set as selected fro the choose FQDN/ choose metrics
		 */
		initDefaultOption : function(elem, match){
			var options = $(elem+' > option');
			$.each(options,function(i,v){
				if ($(v).html() == match) {
					//alert('fired');
					$(v).attr('selected', 'selected');
				}
			});
			var val = $(elem).val();
			$(elem).select2("val", val);
		},
		
		/**
		 * KT from 1 hour/ 2 day RELATIVE Time to ABSOLUTE TIME
		 */
		formatDateTimeForTSDB: function(timerange){
			var end_time = new Date();
			var start_time = new Date();
			var converter = new AnyTime.Converter({format: "%Y/%m/%d-%T"});
			if(timerange==="1 Hour"){
				start_time.setHours(start_time.getHours()-1);
			}else if(timerange==="1 Day"){
				start_time.setHours(start_time.getHours()-24);
			}else if(timerange==="1 Week"){
				start_time.setHours(start_time.getHours()-168);
			}else if(timerange==="1 Month"){
				start_time.setMonth(start_time.getMonth()-1);
			}else if(timerange==="3 Month"){
				start_time.setMonth(start_time.getMonth()-3);
			}else if(timerange==="6 Month"){
				start_time.setMonth(start_time.getMonth()-6);
			}
			start_time = converter.format(start_time);
			end_time = converter.format(end_time);
			console.log("formatDateTimeForTSDB Time start to end: " + start_time+" TO "+ end_time);
			start_time_after = start_time.replace(/\//g, '.');
			end_time_after = end_time.replace(/\//g, '.');
			return {
				starttime: start_time_after,
				endtime: end_time_after
			}
		},
		
		/**
		 * IN EVPS query; MAKE SURE use the right duration e.g For > 24H; only have 600S
		 */
		formatMetricNameForTSDB10sBasis: function(timerange, metricname){
			console.log(metricname);
			var formatname = metricname;
			if(timerange==="1 Hour"){
				if(metricname.indexOf('STATE.60s')!=-1){
					formatname = metricname.replace('STATE.60s', 'STATE.10s');
				}				
				if(metricname.indexOf('AVG.60s')!=-1){
					formatname = metricname.replace('AVG.60s', 'STATE.10s');
				}
				if(metricname.indexOf('AVG.600s')!=-1){
					formatname = metricname.replace('AVG.600s', 'STATE.10s');
				}

			}else if(timerange==="1 Day"){
				if(metricname.indexOf('STATE.10s')!=-1){
					formatname = metricname.replace('STATE.10s', 'AVG.600s');
				}
				if(metricname.indexOf('STATE.60s')!=-1){
					formatname = metricname.replace('STATE.60s', 'AVG.600s');
				}				
				if(metricname.indexOf('AVG.600s')!=-1){
					formatname = metricname.replace('AVG.600s', 'AVG.600s');
				}
			}else{
				if(metricname.indexOf('STATE.10s')!=-1){
					formatname = metricname.replace('STATE.60s', 'AVG.600s');
				}				
				if(metricname.indexOf('STATE.10s')!=-1){
					formatname=metricname.replace('STATE.10s', 'AVG.600s');
				}if(metricname.indexOf('AVG.60s')!=-1){
					formatname=metricname.replace('AVG.60s', 'AVG.600s');
				}if(metricname.indexOf('STATE.60s')!=-1){
					formatname=metricname.replace('STATE.60s', 'AVG.600s');
				}
			}
			return formatname;
		},
		formatMetricNameForTSDB60sBasis: function(timerange,metricname){
			var formatname = metricname;
			if(timerange==="1 Hour"){
				if(metricname.indexOf('STATE.10s')!=-1){
					formatname = metricname.replace('STATE.10s', 'STATE.60s');
				}				
				if(metricname.indexOf('AVG.60s')!=-1){
					formatname = metricname.replace('AVG.60s', 'STATE.60s');
				}
				if(metricname.indexOf('AVG.600s')!=-1){
					formatname = metricname.replace('AVG.600s', 'STATE.60s');
				}

			}else if(timerange==="1 Day"){
				if(metricname.indexOf('STATE.10s')!=-1){
					formatname = metricname.replace('STATE.10s', 'AVG.600s');
				}
				if(metricname.indexOf('STATE.60s')!=-1){
					formatname = metricname.replace('STATE.60s', 'AVG.600s');
				}				
				if(metricname.indexOf('AVG.600s')!=-1){
					formatname = metricname.replace('AVG.600s', 'AVG.600s');
				}
			}else{
				if(metricname.indexOf('STATE.10s')!=-1){
					formatname = metricname.replace('STATE.10s', 'AVG.600s');
				}				
				if(metricname.indexOf('STATE.10s')!=-1){
					formatname=metricname.replace('STATE.10s', 'AVG.600s');
				}if(metricname.indexOf('AVG.60s')!=-1){
					formatname=metricname.replace('AVG.60s', 'AVG.600s');
				}if(metricname.indexOf('STATE.60s')!=-1){
					formatname=metricname.replace('STATE.60s', 'AVG.600s');
				}
			}
			return formatname;
		},
		
		/**
		 * 
		 */
		formatMetricNameTimeForTSDB: function(starttime, endtime, metricname){
			var timerange = endtime.getTime()- starttime.getTime() ;
			console.log(starttime+"  "+endtime);
		 	console.log(timerange);
		 	if(timerange > 86400000){
		 		if(this.metricInterval === "10 Seconds"){
		 		return this.formatMetricNameForTSDB10sBasis('1 Week', metricname);
		 		}else{
		 			return this.formatMetricNameForTSDB60sBasis('1 Week', metricname);
		 		}


		 	}else if(timerange > 7200000){
		 		if(this.metricInterval === "10 Seconds"){
		 		return this.formatMetricNameForTSDB10sBasis('1 Day', metricname);
		 		}else{
		 		return this.formatMetricNameForTSDB60sBasis('1 Day', metricname);
		 		}
		 	}else{
		 		return metricname;
		 	}
		},
		

		
		/**
		 * KT: fetchData point from TSDB using the absolute time selection;
		 * STARTING POINT: 
		 * 
		 * GET all from the filter: fqdn, metric, start/end time/duration; to assumble the EVPS query and send out. and then draw
		 */
		fetchData: function(){
			//get the choices in the form
			var fqdn_choice = $('#searchFQDN').find(':selected').text();
			var metric_choice = $('#searchMetrics').find(':selected').text();
			
			

			var start_time_choice = $('#start_time_input').val();
			var end_time_choice = $('#end_time_input').val();
			
			/**
			 * KT. if the calendar is not filled; using the right middle bar value
			 */
			if(start_time_choice==""||end_time_choice==""||start_time_choice==null||end_time_choice==null){
				alert('Please input both the start and end time. Or click on the right shortcut for last 1hour/1day/1week quick selection.\nNote that data longer than 1 week may take extra time for loading.');
				return;
			}

			//if selected date range exceeds 15 month;
			var converter = new AnyTime.Converter({format: "%Y/%m/%d-%T"});

			var start_time_after = start_time_choice.replace(/\//g, '.');
			var end_time_after = end_time_choice.replace(/\//g, '.');

			var startDate = converter.parse(start_time_choice);
			var endDate =  converter.parse(end_time_choice);
			var currentDate = Date.now();

			if(startDate.getTime() > endDate.getTime()||startDate.getTime()>currentDate||endDate.getTime()>currentDate){
				alert('Please check your input time duration .');
				return;
			}

			//// Check the date range, 86400000 is the number of milliseconds in one day
			if(endDate.getTime()-startDate.getTime()>86400000*365){
				alert('Please specify your time range within 12 months');
				return;
			}

			metric_choice = this.formatMetricNameTimeForTSDB(startDate, endDate, metric_choice);

			// udpate metric
			this.page_config.currentmetric = metric_choice
			console.log("formatMetricNameTimeForTSDB() convert currentmetric to " + this.page_config.currentmetric);
						
			$('div#detail_chart_container').empty();
			var metricName = this.page_config.currentmetric
			var fqdn = this.page_config.currentfqdn

			console.log("fetchData() fqdn " + fqdn) ;
			var aggregateMethod = "avg"

		
			var data_url = "/agent/getEvpsDataAsProxyStartEnd/"+ start_time_after + "/"+ end_time_after+ "/"+this.page_config.currentmetric+"/"+fqdn+"/" + aggregateMethod;

			$("div.modal_loader").show();
			this.getDataFromAgentProxyWithTSDB(this.page_config.currentmetric, this.page_config.currentfqdn, data_url);		
			
		

		},
		
		/**
		 * when click on the bar(middle right) assuming all other parts (metrics/fqdn) is unchanged; call this;
		 * 
		 * COMPARE to fetch data( which assumles every
		 */
		updateData:function(timerange){
			var time = this.formatDateTimeForTSDB(timerange);
			if(this.metricInterval === "10 Seconds"){
				
				this.page_config.currentmetric = this.formatMetricNameForTSDB10sBasis(timerange, this.page_config.currentmetric);
				console.log( "updateData() : converted metrics according to interval of  " + this.page_config.currentmetric);
			}else{
				
				this.page_config.currentmetric = this.formatMetricNameForTSDB60sBasis(timerange, this.page_config.currentmetric);
				console.log( "updateData() : converted metrics according to interval of  " + this.page_config.currentmetric);
			}
			console.log("updateData() convert currentmetric to " + this.page_config.currentmetric);
						
			$('div#detail_chart_container').empty();
			var metricName = this.page_config.currentmetric
			var fqdn = this.page_config.currentfqdn
			var aggregateMethod = "avg"

		
			var data_url = "/agent/getEvpsDataAsProxyStartEnd/"+ time.starttime + "/"+ time.endtime+ "/"+metricName+"/"+fqdn+"/" + aggregateMethod;

			$("div.modal_loader").show();
			this.getDataFromAgentProxyWithTSDB(this.page_config.currentmetric, this.page_config.currentfqdn, data_url);
		},





	};
	return sapphire_detail_lib;
}());