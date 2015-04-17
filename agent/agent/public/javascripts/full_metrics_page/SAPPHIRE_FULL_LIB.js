var SAPPHIRE_LIB = SAPPHIRE_LIB ? SAPPHIRE_LIB: {};

var SAPPHIRE_FULL_LIB = (function(){
	var sapphire_full_lib = function(page_config, metric_list, metric_label_list){
			this.page_config = page_config;
			this.metric_list = metric_list;
			this.metric_label_list = metric_label_list;
			
	};
	sapphire_full_lib.prototype= {
		/***     get the hostlist from the localstorage      ***/
		/***     !!!!!!!! enable parse from url as well      ***/
		init: function(){

			console.log("in init");
			/**
			 * KT: getObjectLocalStorage: local storage is browser level (similar to session) not page level.
			 */

			this.hostlist = [this.page_config.currentfqdn];

			
			this.page_config.currentmetric = this.metric_list[0]
		
		},
		/***call the data fetching, passing the plotting function
		 * 
		 * THIS IS LIKE MVC:
		 * plotFullMetricsChart is like a Controller;
		 * define a callback is like VIEW: (when data is ready how to handle it)
		 * call the readMetricsListFromUrl(MODEL) to pass the VIEW to to the MODEL
		 * 
		 * ***/
		plotFullMetricsChart: function(){
			$('#full_metrics_container').empty();
			//	var datalength = window.localStorage.getItem('datalength');
			
			

			
			//get the data for each metric, draw the chart
			// this inside of a loop in javascript is referring the to current one in the loop. so juse that
			that = this;

			metric_length = this.metric_label_list.length;

			console.log("in plotFullMetricsChart metric_length " + metric_length);

			this.mapOutContainerForAgent(metric_length);
			$.each(this.metric_list, function(index,metric_name){

				
				metric_label_name = that.metric_label_list[index];
				console.log("metric_label_name:" + metric_label_name)
				$('#full_chart_container_' + index).attr('metric_name',
					metric_name);
				$('#full_chart_container_' + index).attr('fqdn_name',
					that.page_config.currentfqdn);
				$('#full_chart_container_' + index).attr('cluster_name',
					that.page_config.currentcluster);
				console.log("in plotFullMetricsChart FOR LOOP for index  " + index + " with total length: " +  metric_length);
				that.plotMetricDataFromAgentProxyUrl(metric_name,metric_label_name,index);

			});

		},
		/***  fetching data for full metrics chart plotting 
		 * 
		 * this will load all the metrics's data; each as an element in the json array. .
		 * resp is the json array of all 
		 * this API is to get all available metrics's data for a fqdn.
		 *
		 * ***/
		readMetricsListFromUrl:function(callback){
			var metric_list_url = "/metriclist?profile="+this.page_config.currentprofile+"&clustername="+this.page_config.currentcluster+"&fqdn="+this.page_config.currentfqdn;		
			SAPPHIRE_LIB.ajaxCall(metric_list_url, 'json', _.bind(function(resp){
				
				metric_length = resp.length;
				this.mapOutContainer(metric_length);
				metric_list = resp;
				callback(metric_list);
			},this));
		},
		appendDropDownList : function(){
			// hostlist = SAPPHIRE_LIB.getObjectLocalStorage('host_list');
			// format the host list into an array:
			var that = this;
			$.each(this.hostlist, function(i, value) {
				$('<option>').text(value).appendTo($('#full_host_list_dropdown'));
			});
			var options = $('#full_host_list_dropdown > option');
			$.each(options, function(i, v) {
				if ($(v).html() == that.page_config.currentfqdn) {
					$(v).attr('selected', 'selected');
				}
			});
		},


		
		// * Jeff 20130910: for agent. 
		// * timeout 20 second
		
		plotMetricDataFromAgentProxyUrl: function(metric_name, metrics_lable_name, index){
			//var metric_data_url="/datapoints?profile="+this.page_config.currentprofile+"&clustername="+this.page_config.currentcluster+"&fqdn="+this.page_config.currentfqdn+ "&metricname="+ metric_name;
			

			var duration = "1d-ago"
			var metricName = metric_name
			var fqdn = this.page_config.currentfqdn
			var aggregateMethod = "avg"

			var getEvpsFromAgentProxyUrl = "/agent/getEvpsDataAsProxy/"+ duration + "/"+metricName+"/"+fqdn+"/" + aggregateMethod;
			console.log("in plotMetricDataFromAgentProxyUrl to send with metricName "+ metricName);
			// this is for showing the error. 
			var evpsTrueUrlText = "http://xyz.com/q?start=" + duration +"&m=" +aggregateMethod+ ":"+metricName+"%7Bfqdn="+fqdn+"%7D&format=json";

			var evpsTrueUrlGraph = "http://xyz.com/q?start=" + duration +"&m=" +aggregateMethod+ ":"+metricName+"%7Bfqdn="+fqdn+"%7D&format=png";
			var that = this;
			$.ajax({
						url: getEvpsFromAgentProxyUrl,
						async: true,
						dataType: 'json', 
						timeout: 60000,
						success: function(resp){

						console.log("GOT DATA in getDataFromTSDB");
						var chartwidth = that.setSingleChartSize().width;
						var chartheight = that.setSingleChartSize().height;
						console.log("Got response (not sure whether empty or not) from plotMetricDataFromAgentProxyUrl ");
								

						var dataPointsPtr = null;
						// handle exception; when no data coming in.
						if(!resp){
							
							$('#full_chart_container_' + index).css('background', 'url(/images/error.png) no-repeat center center' )
							$('#full_chart_container_'+index).empty();
							$('#full_chart_container_'+index).html('<h6>Response Empty from EVPS for metric:  '+metricName 
										+ ' It is expected that some disk and network metrics are only available in certain boxes. <br/><br/> DEBUG: </h6> '
								+ ' <a href=" '+ evpsTrueUrlGraph + ' " target="_blank" > EVPS URL</a> '
								+ '<br/><br/> <a href="/agent/monitors" target="_blank" > Agent URL</a> '
								);
							return

	
						}else if(typeof resp.DataPoints =='undefined'){
							

							if(resp[0]){
								dataPointsPtr = resp[0].DataPoints	
							}else{
								$('#full_chart_container_' + index).css('background', 'url(/images/error.png) no-repeat center center' )
								$('#full_chart_container_'+index).empty();
								$('#full_chart_container_'+index).html('<h6>Response Empty from EVPS for metric:  '+metricName 
										+ ' It is expected that some disk and network metrics are only available in certain boxes. <br/><br/> DEBUG: </h6> '
								+ ' <a href=" '+ evpsTrueUrlGraph + ' " target="_blank" > EVPS URL</a> '
								+ '<br/><br/> <a href="/agent/monitors" target="_blank" > Agent URL</a> '
								);
								return
							}

						}else{
							dataPointsPtr = resp.DataPoints	

						}	
						var range = SAPPHIRE_LIB.getRangeArray(dataPointsPtr);
						//console.log(resp);
						//console.log(range.min+"&&&&"+range.max);
						var maxv = range.max > 0 ? range.max : 1;
						var minv = range.min > 1 ? range.min : -1;
					
						SAPPHIRE_LIB.drawChart($('#full_chart_container_'+index), [{data:SAPPHIRE_LIB.formatDataPointsfromTSDB(dataPointsPtr), name:that.page_config.currentfqdn}], metrics_lable_name, metric_name, chartheight, chartwidth, minv, maxv);
						// $('#chart_img_' + index).hide();
						
						$('#full_chart_container_' + index).css('background', 'none' )

						//console.log($(this));
						$('#full_chart_container_'+index+" .highcharts-title").on('click', function() {
							// page_config.currentfqdn = currentfqdn;
							// page_config.setCurrentCluster(currentcluster);
							that.page_config.currentmetric = metric_name;
							SAPPHIRE_LIB.setObjectLocalStorage('page_Config', that.page_config);
							document.location.href = '/healthAdvanced/' + metric_name;
						});
				
						},
						//<a href="/agents/cassiniTopologyTagPushWholeJob?nodeGroupType=CASSINI_QE1" target="_blank" class="btn btn-primary">Execute</a>
						error: function(jqXHR, textStatus, errorThrown){
							
							$('#full_chart_container_' + index).css('background', 'url(/images/error.png) no-repeat center center' )
							$('#full_chart_container_'+index).empty();
							$('#full_chart_container_'+index).html('<h6>Response Timeout or Error from EVPS (Thru agent proxy) after 60 Sec for metric:  '+metricName 
											+ "Error:" + errorThrown + ' It is expected that some disk and network metrics are only available in certain boxes. <br/><br/> DEBUG: </h6> '
								+ ' <a href=" '+ evpsTrueUrlGraph + ' " target="_blank" > EVPS URL</a> '
								+ '<br/><br/> <a href="/agent/monitors" target="_blank" > Agent URL</a> '
								);
							
						}
					});	
				},

			

		plotMetricDataFromUrlAllFQDN : function(url, container, metric_name){
			SAPPHIRE_LIB.ajaxCall(url, 'json', _.bind(function(resp){
				var chartwidth = this.setSingleChartSize().width;
				var chartheight = this.setSingleChartSize().height;
				SAPPHIRE_LIB.drawChart(container, resp, metric_name, this.page_config.currentfqdn, chartheight,chartwidth);
			},this));
				
		},

		mapOutContainerForAgent: function(datalength){
			
			var row_num = 2;
			
			console.log('row_num:' + row_num);
			for ( var i = 0; i < row_num; i++) {
				$('<article class="row">').appendTo('div#full_metrics_container');
			}

			/**
			 * KT add an invisible row container; to make sure 6 metrics are in one row
			 */
			var containers = $('.row');
			//console.log(containers);

			rowIndex = 0;
			$('<h4>&nbsp;&nbsp;&nbsp;CPU Metrics</h4>')
			
				.appendTo(containers[rowIndex]);	
			$('<section class="metrics_unit" id="full_chart_container_' + 0 + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[rowIndex]);	
			$('<section class="metrics_unit" id="full_chart_container_' + 1 + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[rowIndex]);	
			$('<section class="metrics_unit" id="full_chart_container_' + 2 + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[rowIndex]);	
			$('<section class="metrics_unit" id="full_chart_container_' + 3 + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[rowIndex]);				


			rowIndex = 1;
			$('<div class="row-fluid"><div class="span3"><h4>&nbsp;&nbsp;&nbsp;Memory Metrics</h4></div><div class="span6" ><h4>Network Metrics</h4></div><div class="span3" class="chartLabel"><h4  style="margin-left:-45px">Disk Metrics</h4></div></div>')
				.appendTo(containers[rowIndex]);	
			$('<section class="metrics_unit" id="full_chart_container_' + 4 + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[1]);	
			$('<section class="metrics_unit" id="full_chart_container_' + 5 + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[1]);	
			$('<section class="metrics_unit" id="full_chart_container_' + 6 + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[1]);	
			$('<section class="metrics_unit" id="full_chart_container_' + 7 + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[1]);	
		
		

		
			this.setSingleDivSize();
			// console.log($(this));
			
		},

		mapOutContainer: function(datalength){
			var chartDisplaySizePerRow = 5;
			var row_num = datalength / chartDisplaySizePerRow;
			row_num = Math.ceil(row_num);
			console.log('row_num:' + row_num);
			for ( var i = 0; i < row_num; i++) {
				$('<article class="metrics_row">').appendTo('div#full_metrics_container');
			}

			/**
			 * KT add an invisible row container; to make sure 6 metrics are in one row
			 */
			var containers = $('.metrics_row');
			//console.log(containers);


			// append each section to the article with the loader img.
			var index = -1;
			var flag = 0;
			for ( var i = 0; i < datalength; i++) {
				if (flag % chartDisplaySizePerRow === 0) {
					flag = 0;
					index++;
				}
				$('<section class="metrics_unit" id="full_chart_container_' + i + '" style="background: url(/images/ajax_loader_blue_128.gif) no-repeat center center;">')
				.appendTo(containers[index]);	

					flag++;
				console.log("in mapOutContainer to add GIF loader " + index)
			}// end for
			this.setSingleDivSize();
			// console.log($(this));
			
		},
		setSingleChartSize: function(){

			var chartDisplaySizePerRow = 4;
			var chartWidth =  $(window).width()/chartDisplaySizePerRow-20;
			var chartHeight = chartWidth* 0.7;
			return {
				width: chartWidth,
				height: chartHeight
			}
		},
		setSingleDivSize:function(){
			var width = this.setSingleChartSize().width ;
			var height = this.setSingleChartSize().height +10;
			$('.metrics_unit').width(width);
			$('.metrics_unit').height(height);
		}
	};

	return sapphire_full_lib;
}());