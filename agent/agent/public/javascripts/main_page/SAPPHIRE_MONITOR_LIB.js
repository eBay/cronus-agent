
var SAPPHIRE_LIB = SAPPHIRE_LIB ? SAPPHIRE_LIB : {};
var _ = _ ? _ : {};
var console = console ? console : {log: function () {}, dir: function () {} };
var Highcharts = Highcharts ? Highcharts : {};


var SAPPHIRE_MONITOR_LIB = (function() {
/* [sapphire_lib] will wrap every method and variable to prevent outside changes.*/
	var sapphire_lib = function(page_config){
		this.page_config = page_config;
		this.nodes_list = [];            //nested list of profiles, clusters, fqdns; KT: array of objects; the initial one
		this.metric_list = [];			 //the list of metric_list
		this.fqdn_key_metrics_data = [];	// 
		this.cluster_level_data = [];		//
		this.fqdn_level_data = [];			// KT: actually data is here. 
		this.cluster_list = [];				//the list of all cluster; KT derived from nodes_list; array of string
		this.fqdn_list = [];				//the list of all fqdn; ; KT derived from nodes_list; array of string
		this.chart_view_choice = 'cluster';

		//**************************************************************************
 		//***************  constant for those two health metric  *******************
 		//*************************  MPDB use only  ********************************
		this.HEALTH_DEFINE_METRICS = ["loadavg1min", "connections.current"];
		this.SIZE_DEFINE_METRIC = "updays";
		this.HEALTH_DEFINE_METRICS_0_RED_LINE_CONSTANT = 30,
		this.HEALTH_DEFINE_METRICS_0_YELLOW_LINE_CONSTANT = 20,
		this.HEALTH_DEFINE_METRICS_1_RED_LINE_CONSTANT = 18000,
		this.HEALTH_DEFINE_METRICS_1_YELLOW_LINE_CONSTANT = 15000;
		this.SIZE_DEFINE_METRIC_MIN_VALUECONSTANT = 1;
		this.SIZE_DEFINE_METRIC_MAX_VALUECONSTANT = 400;
		/***************************************************************************/

		/***************************  Color Constant      *************************/
		this.GREENS = [
						'#2ca02c',
						'#98df8a',
						'#31a354',
						'#74c476',
						'#a1d99b',
						'#55AE3A',
						'#7FD76B',
						'#A2EC88',
						'#7AE845',
						'#8CDD81',
						'#7BCC70',
						'#40B640',
						'#7BBF6A'
					];  
		this.RED = '#FD1718';
		this.YELLOW = '#faba37';
		this.GREY = '#DDDDDD';
		/***************************************************************************/
	};

	sapphire_lib.prototype = {
		/*initList will fetch all the data for future use.*/
		initList: function(){
			/*the url for fetching the nodes/metrics data*/
			var nodes_list_url = "./hostlist/?profile=";
			var metrics_list_url = "/getMetricsforProfile?profile=";
			var nodes_ajax = []; /* stores all the ajax object for get the nodes */
			var metric_ajax = []; /* stores all the ajax object for get the metrics  */
			
			//for nodes_list
			for(var i = 0; i < this.page_config.profile_names.length; i++){
				//closure begins:
				var sapphire_lib_self_ptr = this; /*the workaround to get the sapphire_main_lib self_object*/
				// KT: sapphire_lib self pointer is this.
				(function(i){

					/**
					 * KT: _ is underScore.js lib as $ for jQuery lib
					 * Motivation to use "sapphire_lib_self_ptr"; because if using "this", will not mean sapphire_lib; but will point to the ajax obj.
					   Motivation of the binding: in A.do1() want to call A.do2(); cannot call; need to use this.  but this is a context variable. 
					   
					   node_list does not have metric data; only have hirachry of the nodes. 
					   
					   binding will replace the "this".nodes_list's "this"
					 */
					nodes_ajax[i] = SAPPHIRE_LIB.ajaxCall(nodes_list_url+sapphire_lib_self_ptr.page_config.profile_names[i], 'json', 
						_.bind(function(resp){
							this.nodes_list.push({profile: sapphire_lib_self_ptr.page_config.profile_names[i], nodes: resp});
						}, sapphire_lib_self_ptr));		
				})(i);		
			}
			/*When all the nodes ajax calls executed...parse the nodes list, plot heatmap/bubblechart, inittypeahead of nodes list*/
			$.when.apply(null,nodes_ajax).then(function(){
				sapphire_lib_self_ptr.parseNodesListToFQDNCluster();
				sapphire_lib_self_ptr.plotHeatMap(); // KT: may take div to append DV
				sapphire_lib_self_ptr.plotBubbleChart();

				SAPPHIRE_LIB.initTypeAhead('select#searchCluster', sapphire_lib_self_ptr.cluster_list, 'Select A Cluster...');
				SAPPHIRE_LIB.initTypeAhead('select#searchFQDN', sapphire_lib_self_ptr.fqdn_list, 'Select A FQDN...');
			},
			function(){
				console.log("Data Fetching Error...");}
			);


			//for metrics list
			for(var j = 0; j < this.page_config.profile_names.length; j++){
				var sapphire_lib_self_ptr = this;
				(function(j){				
					//get metric list
					metric_ajax[j] =  SAPPHIRE_LIB.ajaxCall(metrics_list_url+sapphire_lib_self_ptr.page_config.profile_names[j], 'json', 
						_.bind(function(resp){
							// console.log(this);
							this.metric_list.push({profile: sapphire_lib_self_ptr.page_config.profile_names[j], nodes: resp});
						}, sapphire_lib_self_ptr));
				})(j);		

			}
			/*When all the nodes ajax calls executed... init typeahead of metrics list, init metric-selection-coloring*/
			$.when.apply(null, metric_ajax).then(function(){

				SAPPHIRE_LIB.initTypeAhead('select#choose_metrics_for_color', sapphire_lib_self_ptr.metric_list, 'Select A Metric...');
				sapphire_lib_self_ptr.initColoring();
				sapphire_lib_self_ptr.appendFilterButton(sapphire_lib_self_ptr.page_config.view_choice);
			},
			function(){
				console.log("Data Fetching Error...");}
			);
		},

		/*append the button for the side bar filter section.KT:  profile selection */
		appendFilterButton : function(){
			$.each(this.page_config.profile_names, function(i,v){
				$('<button class="btn btn-mini active filter_btn">').text(v).appendTo($('div#sapph_contentchoice'));
			});
			/*bind click event listerer for filter buttons*/
			$('button.filter_btn').bind('click', function(){
				//if the btn was switched from chosen to inactive
				if($(this).hasClass('active')){
					$('section#heatmap_carrier_'+$(this).text()).hide();
				}else{
					$('section#heatmap_carrier_'+$(this).text()).show();
				}
			});
		},
		/*parse the nested nodes_list into two list: cluster_list, fqdn_list*/
		parseNodesListToFQDNCluster : function(){
			var sapphire_lib_self_ptr = this;
			// console.log(this.nodes_list);
			$.each(sapphire_lib_self_ptr.nodes_list, function(index,value){
				var tempfqdn = {};
				var tempcluster = {};
				tempfqdn.profile = value.profile;
				tempfqdn.nodes = [];
				tempcluster.profile = value.profile;
				tempcluster.nodes = [];
				$.each(value.nodes, function(i,v){
					if(v.cluster_name!=='All fqdn'){
						tempcluster.nodes.push(v.cluster_name);
					}else{
						tempfqdn.nodes = v.hostlist;
					}
				});
				sapphire_lib_self_ptr.fqdn_list.push(tempfqdn);
				sapphire_lib_self_ptr.cluster_list.push(tempcluster);
			});
		},
		/*fetch the cluster level data.   USE: Draw Bubble Chart*/
		fetchClusterLevelData : function(){
			var cluster_data_url = "/getClusterLevelData?profile=";
			$.each(this.page_config.profile_names, function(i,v){
				SAPPHIRE_LIB.ajaxCall(cluster_data_url+v, 'json', 
					_.bind(function(resp){
						// KT: resp is a array of clusters; for each cluster; 
						// v is the profile name. 
						// before [[k,v],[k,v]], now add [[k,v],[k,v],[profile, prof1]]
						$.each(resp, function(index,value){
				              value.push(["profile",v]);
				          });
				          this.cluster_level_data = this.cluster_level_data.concat(resp);
					}, this));
			});
		},
		/*fetch the key metrics data. USE: Display linechart in Modal
		 * KT: this is to fetch data only. actual processing(call back) is in another function that calls this callback.
		 * here just define another interface callback that other function call this, will need to provide the "real" call back procedure.
		 * */
		fetchFqdnKeyMetricsData : function(callback){
			if(callback===undefined){
				console.log("No CallBack Defined...");
				return;
			}
			var sapphire_lib_self_ptr = this;
			var keyMetrics_url = "./getlinechartmetrics?profile="+this.page_config.currentprofile+"&cluster=" + this.page_config.currentcluster
			+ "&fqdn=" + this.page_config.currentfqdn;
			SAPPHIRE_LIB.ajaxCall(keyMetrics_url, 'json', _.bind(function(resp){
				//ASSUMPTION: the backend will pass 6 metrics for use.
				callback(resp);
			}, this));

		},
		/*given a cluster, return its fqdn list.*/
		getHostListByCluster :  function(clustername){
			if(clustername===undefined||clustername===""){
				return 'Not Legal Cluster';
			}
			for(var j = 0; j<this.nodes_list.length; j++){
				for ( var i = 0, len = this.nodes_list[j].nodes.length; i < len; i++) {
					if (this.nodes_list[j].nodes[i].cluster_name == clustername) {
						return this.nodes_list[j].nodes[i].hostlist;
					}
				}
			}
			return 'Not Found'; 
		},
		/*given a cluster, return its profile*/
		getProfileByCluster : function(clustername){
			if(clustername===undefined||clustername===""){
				return 'Not Legal Cluster';
			}
			if(clustername===undefined||clustername===""){
				return 'Not Legal Cluster';
			}
			for(var i=0;i<this.nodes_list.length;i++){
				for(var j=0; j< this.nodes_list[i].nodes.length;j++){
					if(this.nodes_list[i].nodes[j].cluster_name===clustername){
						// console.log(this);
						return this.nodes_list[i].profile;
					}
				}
			}
			return 'Not Found';
		},
		/*given a fqdn, return its cluster*/
		/*!!!!!!!!!!!!POTENTIAL BUG: a fqdn relates multiple cluster; in this case: will return the first matching cluster*/
		/***    USE: searchFQDN dropdown. need better solution    ***/
		searchClusterforFQDN : function(fqdn){
			if(fqdn===undefined||fqdn===""){
				return 'Not Legal Cluster';
			}
			for(var i=0;i<this.nodes_list.length;i++){
				for(var j=0;j<this.nodes_list[i].nodes.length;j++){
					if(SAPPHIRE_LIB.arrayContains(this.nodes_list[i].nodes[j].hostlist, fqdn)){
						return this.nodes_list[i].nodes[j].cluster_name;
					}
				}
			}
			return 'Not Found';
		},

		/*all the layout related methods
		 * set width / length of the bubblechart a/ heatmap scope
		 * */
		setMainchartContainerSize : function(){
			var setwidth = $('body#sapphire_main').width() - $('div#sideBar_main').width() - ($('body#sapphire_main').width()*0.06);

			// console.log('width-------' + setwidth);
			$('div#mainchart_container').width(setwidth);
			var setheight = $(window).height() * 0.85;
			$('div#mainchart_container').height(setheight);
		},
		getMainchartContainerSize : function(){
			var width = $('div#mainchart_container').width();
			var height = $('div#mainchart_container').height();
			return {
				width : width,
				height : height
			}
		},
		
		/**
		 * Key metrics pop up (modal) 
		 */
		setModalDivSize : function(){
			var modalWidth = $(window).width() * 0.4;

			var modalHeight = $(window).height() * 0.2;
			return {
				width : modalWidth,
				height : modalHeight
			}
		},
		setModalChartSize : function(Container){
			var chartWidth = $('#' + Container).width() * 0.30;
			var chartHeight = $(window).height() * 0.25;

			return {
				width : chartWidth,
				height : chartHeight
			}
			
		},
		getTextWidth: function(elem){
			return $(elem).text().length*7;

		},
		getDivWidth : function(elem){
			return elem.length*20;
		},
		
		/**
		 * KT: cluster level one heatmap
		 */
		setSingleMapWidth : function(){
			var maps = $('div.heatmap_container');
			var sapphire_lib_self_ptr = this;
			$.each(maps, function(i, v) {
				var heatmap_square_units = $(this).children();
				//console.log(units);
				var textlength = sapphire_lib_self_ptr.getTextWidth(heatmap_square_units[0]);
				var divlength = sapphire_lib_self_ptr.getDivWidth(heatmap_square_units);
				if(textlength < divlength){

				 	if(heatmap_square_units.length>1000){
						$(this).width(sapphire_lib_self_ptr.getMainchartContainerSize().x - 100);
					}else  
					if(heatmap_square_units.length>500){
						$(this).width(600);
					}else 
					if(heatmap_square_units.length>24){
						$(this).width(280);
					}
					else{
						$(this).width(160);
					}
				}else{
					$(this).width(textlength);
				}

			});
		},
		/*Coloring Scheme Part:
		************************************************************************************
		*/
		/*   set up the slider and the range label/selector   */
		initColoring: function(){
			var sapphire_lib_self_ptr = this;
			$('#choose_metrics_for_color').bind('change', function(){
				
				var metrics_choice = $('select#choose_metrics_for_color').val();
				if(metrics_choice === ""){
					/*  hide the range selector/labels and re-color the map/chart  */
					$('div#metric_slider').hide();
					$('label#label_min').hide();
					$('label#label_max').hide();
					/**
					 * KT: this dataMapAndChart() will restore the default
					 */
					sapphire_lib_self_ptr.dataMapAndChart();
				}else{
					$('div#metric_slider').show().empty();
					var heatmap_square_units = $('.heatmap_unit');
					
					/**
					 * rangeArray is to get min/max
					 */
					var rangeArray = [];
					//get all applicable nodes' metric value & its range
					$.each(heatmap_square_units, function(i, v){
						var value= $(v).attr(metrics_choice);

						if(typeof value !== 'undefined'&& value !=='NO DATA'){
							rangeArray.push(parseInt(value));
						}
					});
			
					var currentrange = SAPPHIRE_LIB.getRangeArray(rangeArray);
					$('label#label_min').html(currentrange.min).show();
					$('label#label_max').html(currentrange.max).show();
					$('div#metric_slider').slider({
						/*range ture: means a range selector; so it by default will have 2 bars of the edge of the range.*/
						range: true,
						max: currentrange.max,
						min: currentrange.min,
						/*KT values: default*/
						values: [currentrange.min, currentrange.max],
						slide: function(event, ui){
							/*   the handler of slide event; adjustMapAndChartColor first 2 arguments is the edge value */
							sapphire_lib_self_ptr.adjustMapAndChartColor(ui.values[0], ui.values[1], metrics_choice);
							$('label#label_min').text(ui.values[0]);
							$('label#label_max').text(ui.values[1]);
						}
					});
					/*on select a metric to enable the color scheme (very beginning*/
					sapphire_lib_self_ptr.adjustMapAndChartColor(currentrange.min, currentrange.max, metrics_choice);
				}
			});
		},
		/***  update the data with bubble chart/heat map every refreshing interval 
		 * KT: this is called in main() last lines to refresh every 5min;
		 * ??? POTENTIAL BUG? NOT CHECKED/ VALIDATE. whether this refresh will break the color scheme.?? 
		 * 
		 * CHART: bubblechart; map: heatmap
		 * 
		 * ***/
		updateData: function(){
				this.dataMap(); // restore the heatmap redraw
				this.plotBubbleChart(); // redraw bubblechart
				this.updateRefreshed();
		},
		/*** restore the coloring/data after the metric-coloring ***/
		dataMapAndChart : function(){
			this.dataMap();
			this.dataChart(d3.select('svg'));
		},
		/*** update the lastrefreshed label ***/
		updateRefreshed : function(){
			var update_url = "/lastRefreshed?profileList="+this.page_config.profile_names;
			SAPPHIRE_LIB.ajaxCall(update_url, 'text', _.bind(function(resp){
				var now = new Date(parseFloat(resp));
				$('em#last_updated').text("Last Refreshed: "+ now.toLocaleString());
			},this));

		},
		/*** adjust the color giving the user selection ***/
		adjustMapAndChartColor : function(valuemin, valuemax, metric_choice){
			var view_choice = $("div#sapph_viewchoice > button.active").val();
			if(view_choice ==='map'){
				this.adjustMapColor(valuemin, valuemax, metric_choice);
			}else{
				this.adjustChartColor(valuemin, valuemax, metric_choice);
			}		
		},
		/*** adjust the heatmap color giving the user selection ***/
		adjustMapColor : function(valuemin, valuemax, metric_choice){
			var heatmap_square_units = $('.heatmap_unit');
			$.each(heatmap_square_units, function(i,v){
				$(v).removeClass('black green red yellow noclass');
				var value =  $(v).attr(metric_choice);

				if(typeof value !== 'undefined'){
					// console.log(value);
					if(value==='NO DATA'){
						$(v).addClass('black');
					}else{
						var val = parseInt(value);
						if(val <= valuemin){
							$(v).addClass('green');
						}else if(val>=valuemax){
							$(v).addClass('red');
						}else{
							$(v).addClass('yellow');
						}
					}
				}else{
					$(v).addClass('noclass');
				}
			});
		},	


		//LINE Chart Plotting  KEY METRICS
		plotKeyMetricChart: function(){
			fqdn_name = $('#host_list_dropdown option:selected').text();
			if (fqdn_name == null || fqdn_name == undefined || fqdn_name == "") {
				return;
			}

			this.page_config.currentfqdn = fqdn_name;
			/*KT: this is the loading GIF*/
			$("div.modal_loader").show();
 
			/**
			 * First to define the call back functon ( after the data is back how to handle it) then to call the fetchFqdnKeyMetricsData using this callback.
			 * 
			 * Will reset and then draw the line chart for each metric(should be 6 metrics total)
			 * 
			 * key_fqdn_metrics_data is an array; each element is for each metric in this 6 metrics
			 * 
			 */
			/************* passed to the data fetching, plot all the chart once the response is back **************/
			var callback = function(key_fqdn_metrics_data){
				var sapphire_lib_self_ptr = this;
				// console.log(sapphire_lib_self_ptr);
				sapphire_lib_self_ptr.fqdn_key_metrics_data = key_fqdn_metrics_data;
				// console.log(sapphire_lib_self_ptr);
				var modalname = 'theMainModal';
				var chartwidth = this.setModalChartSize(modalname).width;
				var chartheight = this.setModalChartSize(modalname).height;
				// console.log(chartwidth + "         ********      " + chartheight);
				$("div.modal_loader").hide();
				$('div#top_few_metrics_chart_container').empty();
				$('div.single_chart_container').remove();
				// console.log(key_fqdn_metrics_data);
				$.each(key_fqdn_metrics_data, function(i, value) {
					if(value!==undefined&&value.DataPoints!==undefined){
						$('<div class="single_chart_container" id="key_chart_container_'+ i + '">').appendTo($('#top_few_metrics_chart_containter'));
						// console.log('div appended.');
						
						var range = SAPPHIRE_LIB.getRangeArray(value.DataPoints);
						// console.log(resp);
						// console.log(range.min+"&&&&"+range.max);
						var maxv = range.max > 0 ? range.max : 1;
						var minv = range.min > 1 ? range.min : -1;
						
						
						SAPPHIRE_LIB.drawChart($('div#key_chart_container_' + i), [{data:value.DataPoints, name:sapphire_lib_self_ptr.page_config.currentfqdn}], value.MetricName, sapphire_lib_self_ptr.page_config.currentfqdn, chartheight, chartwidth, minv, maxv);
						// SAPPHIRE_LIB.drawLineChart($('div#key_chart_container_' + i), [{data:value.DataPoints, name:sapphire_lib_self_ptr.page_config.currentfqdn}], value.MetricName, sapphire_lib_self_ptr.page_config.currentfqdn, chartheight, chartwidth);
						
						$('div#key_chart_container_'+i+" .highcharts-title").on('click', function() {
							// page_config.currentfqdn = currentfqdn;
							// page_config.setCurrentCluster(currentcluster);
							sapphire_lib_self_ptr.page_config.currentmetric = $(this).text();
							SAPPHIRE_LIB.setObjectLocalStorage('page_Config', sapphire_lib_self_ptr.page_config);
							document.location.href = '../detail';
						});
						
						
						
					}// TODO add some message to handle cannot read. to append to this 
				});
			}
			// console.log(callback);
			/* call the data fetching, pass the ploting as the callback */
			this.fetchFqdnKeyMetricsData(_.bind(callback, this));
		},

		/*********** get the data for all the FQDNs, plot the chart ************/
		plotKeyMetricChartAllFQDN : function(){
			var charts = $('div.single_chart_container');
			// 6 charts + multiple fqdns
			var metrics = $('.highcharts-title');

			var modalname = 'theMainModal';
			var chtwidth = this.setModalChartSize(modalname).width;
			var chtheight = this.setModalChartSize(modalname).height;
			var url = "";
			var profile = this.getProfileByCluster(this.page_config.currentcluster);
			var sapphire_lib_self_ptr = this;
			$.each(charts, function(i, v) {
				$(v).empty();
				url = '/datapointsforall?profile='+sapphire_lib_self_ptr.page_config.currentprofile+'&clustername='+sapphire_lib_self_ptr.page_config.currentcluster+"&metricname="+$(metrics[i]).text();
				// sapphire_lib_self_ptr.plotAllSeriesChart(url, v, chtwidth, chtheight, $(metrics[i]).text());

				SAPPHIRE_LIB.ajaxCall(url, 'json', _.bind(function(resp){
					SAPPHIRE_LIB.drawChart(v, resp, $(metrics[i]).text(), "", chtheight, chtwidth);
				},this));
			});
		},
		/**********    use the nodes_list to map the container for the heatmap       
		 * 
		 * add div for each cell as heatmap_unit; this to fill the structure and cell without data yet. 
		 * 
		 * Teng's backend now have a "All fqdn" has an array of all fqdn list.
		 * 
		 * ***********/
		mapContainer : function(){
			// for each cluster, append a heatmap, including all the clusters.
			// console.log((new Date()).toTimeString());
			$.each(this.nodes_list, function(i, v) {
				$('<section>').attr('id', 'heatmap_carrier_'+v.profile).appendTo('#heatmap_container');
				$('<h5>').text(v.profile).prependTo($('#heatmap_carrier_'+v.profile));
				// console.log((new Date()).toTimeString());
				$.each(v.nodes, function(index,value){
				if (value.cluster_name !== 'All fqdn') {
							// append the div / title for each heatmap
							$(
								'<div id="heatmap_' + i+"_"+index
											+ '" class="heatmap_container"'
											+ '>').attr('profile', v.profile).appendTo('#heatmap_carrier_'+v.profile);

							$('<h6>').text(value.cluster_name).appendTo('#heatmap_' +  i+"_"+index);
							// console.log((new Date()).toTimeString());
							$.each(value.hostlist, function(ind, val) {
								/**
								 * KT: careful; timecomplexity; now first attr attr then append; 
								 */
								var current_div = $('<div class="heatmap_unit">').attr('unit', value.cluster_name)
														.attr('profile', v.profile).appendTo('#heatmap_' +  i+"_"+index);
							});

						}
					});	
				});
		// console.log(this.nodes_list);
		// console.log((new Date()).toTimeString());	
		},
		/**********    get the real data for each map/cluster, then append the data, init the coloring and tooltip     ***********/
		dataMap : function () {
			console.log('dataMap fired');
			var getUrl = '../../heatmap/?';
			var maps = $('.heatmap_container');
			var sapphire_lib_self_ptr = this;
			/* for each cluster_level heatmap */
			$.each(maps, function(i, v) {
	
				var clustername = $(v).text();
				var profile_name = $(v).attr('profile');
				var url = getUrl + 'profile=' + profile_name + '&clustername='
						+ clustername;

				/**
				 * why _.bind? because needs to access its member data / funciton such as .colorMap   
				 */
				SAPPHIRE_LIB.ajaxCall(url, 'json', 
						
						
				/**
				 * 3rd arg; this is the callback
				 * using the backend's "healthStatus" to color each cell
				 */		
				_.bind(function(resp){
					sapphire_lib_self_ptr.fqdn_level_data.push({profile: profile_name, nodes: resp});
					
						var heatmap_square_units = $('.heatmap_unit[unit="' + clustername + '"]');
					
						$.each(eval(resp), function(index, value) {
						
							$.each(eval(value), function(key, val) {
								if (val[0] == "healthStatus") {
									// healthStatus used to color(verb) the map line 609:  
									sapphire_lib_self_ptr.colorMap(heatmap_square_units[index], val[1]);
								} else {
									// other metrics used to form the tooltip
									$(heatmap_square_units[index]).attr(val[0], val[1]);
								}
							});
						});
						SAPPHIRE_LIB.initToolTip(heatmap_square_units);
						
				},sapphire_lib_self_ptr),
				
				/**
				 * 4th argu; This is the errorcallback
				 */
				_.bind(function(resp){
					var heatmap_square_units = $('.heatmap_unit[unit="' + clustername + '"]');
					$.each(heatmap_square_units, function(i, v) {
						$(this).removeClass('black red green yellow noclass');
						$(this).addClass('black');
					});
				},sapphire_lib_self_ptr));
			});
		},
		/*******      append the color of one element, given the health value     *********/
		colorMap : function(elem, value){
			$(elem).removeClass('green red yellow black noclass');

			if (value == 1) {
				$(elem).addClass('green');
			} else if (value == 0) {
				$(elem).addClass('red');
			} else {
				$(elem).addClass('black');
			} 
		},

		/**
		 * KT: in order to enable NONE MPDB: need to add a metric for display; currently "healthStatus" is not in Cluster level.
		 */
		//use to format the data for bubble chart plotting
		//**********************************************************************************
		//*******************  Hard coded the health for MPDB  *****************************
		//**********************************************************************************
		/*
		ASSUMPTION: data is array. The first object will be cluster/fqdn name and the last object will be profile 
		*/
		extractDataToObject : function(obj_original){
			
			//only get the updays/uptime for use only.
			/**
			 * 
			 */
			var obj_parsed= {},
			    scale = d3.scale.linear().domain([this.SIZE_DEFINE_METRIC_MIN_VALUECONSTANT,this.SIZE_DEFINE_METRIC_MAX_VALUECONSTANT]).range([10,60]);

			/**
			 * unit: the cluster/fqdn name/id
			 */
			obj_parsed.unit = obj_original[0][1];
  			obj_parsed.health = [];//default is empty
  			obj_parsed.profile = obj_original[obj_original.length-1][1];
  			obj_parsed.nodata = 0;

  			//for the bubble size and health:
  			//mpdb profiles: use "xxx.updays" metric as the size of bubble.
  			//				use "loadavg1min" & "connections.current" as the health of bubble.
  			//!!!!20130822if(obj_parsed.profile==='mpdb_cassandra'||obj_parsed.profile=== "mpdb_mongo"||obj_parsed.profile==="mpdb_mysql"){

  				var sapphire_lib_self_ptr = this,
  					shortenmetricname = "";
  				for(var i=1;i<obj_original.length-1;i++){
  					//append all the metrics as attribute of the object
  					// shortenmetricname = data[i][0];
  					shortenmetricname = SAPPHIRE_LIB.shortenMetricName(obj_original[i][0],obj_parsed.profile);
  					obj_parsed[shortenmetricname] = obj_original[i][1];

  					if(obj_original[i][0].indexOf(this.SIZE_DEFINE_METRIC)!=-1){//if this is the size define metrics
			          // obj.updays = parseInt(obj_original[i][1]);
  						
  						/**
  						 * KT: from origin to
  						 * SIZE is for the bubble size;
  						 * value is the size after scaling. so value is use to define the size(largeness) fo the map
  						 * CAREFUL DONT CHANGE NAME: some are LIB specific name; dont change it 
  						 */
  						
			          obj_parsed.value = scale(parseInt(obj_original[i][1]));
			        }else{
			        	$.each(this.HEALTH_DEFINE_METRICS, function(ind,val){
			        		if(obj_original[i][0].indexOf("."+val)!=-1){//if this is the health define metrics
			        			// obj[value] = obj_original[i][1];

			        			if(obj_original[i][1]!==undefined){	
									if(isNaN(obj_original[i][1])){
										return false;
									}
									// for (var k = 0; k < sapphire_lib_self_ptr.HEALTH_DEFINE_METRICS.length; k++) {					
										var define_health_yellow_constant_name = "HEALTH_DEFINE_METRICS_"+ind+"_YELLOW_LINE_CONSTANT",
											define_health_red_constant_name = "HEALTH_DEFINE_METRICS_"+ind+"_RED_LINE_CONSTANT";
										
										/** KT 0 1 2 is for colork*/
										if(parseInt(obj_original[i][1])>sapphire_lib_self_ptr[define_health_red_constant_name]){
											obj_parsed.health.push(2);
										}else if(parseInt(obj_original[i][1])>sapphire_lib_self_ptr[define_health_yellow_constant_name]){
											obj_parsed.health.push(1);
										}else{
											obj_parsed.health.push(0);
										}
									// }
			        			}
			        		}
			        	});
			        }

			        if(obj_original[i][1]==="NO DATA"){
			        	obj_parsed.nodata=obj_parsed.nodata+1;
			        }
  				}
  			//!!!!20130822	}else{
//  				for(var j=1;j<obj_original.length-1;j++){
//  					if(obj_original[j][1]==="NO DATA"){
//			        	obj_parsed.nodata=obj_parsed.nodata+1;
//			        }
//  				}
  			//!!!!20130822		}

  			//when other profile or "SIZE DEFINED" metrics missing. KT this if the largeness of the bubble: other is all the same as this 35.
			if(obj_parsed.value===undefined){
				obj_parsed.value = (10+60)*0.5;
			}
			if(obj_parsed.nodata===obj_original.length&&obj_parsed.health.length===0){
				obj_parsed.health = -1;
			}
			
			/**
			 * KT: TODO: for NONE MPDB: the health does not have one metrics: will  use  0 (green)
			 * 
			 * for MPDB: HEALTH_DEFINE_METRICS[] has 2;   will based on these 2 value to add the 2 values into the array of obj_parsed.health
			 * 
			 * for none MPDB this adding does not take effect( add nothing yet) so length will always be 0.
			 */
		 	if(obj_parsed.health.length < 1){
		 		obj_parsed.health = 0;
		 	}else if(obj_parsed.health.length==1){
		 		obj_parsed.health = obj_parsed.health[0];
		 	}else{
		 		obj_parsed.health = SAPPHIRE_LIB.getRangeArray(obj_parsed.health).max;
		 	}

			return obj_parsed;
		},

		//for each profile, extract the data based on different rule. 
		formatDataCluster: function(){
			var parsed_data = [];
			var sapphire_lib_self_ptr = this;
			$.each(this.cluster_level_data, function(i,v){
				// console.log(v);
				parsed_data.push(sapphire_lib_self_ptr.extractDataToObject(v));
			});

			/**
			 * KT: return an obj of key value pair; key is a string "children"  
			 * WARNING: this name should be not changed. 
			 */
			return {children:parsed_data};
		},

		//for the fqdn, merge the array according to its profile, then push to extractDataToObjct
		formatDataFQDN: function(){
			var parsed_data=[];
			var sapphire_lib_self_ptr = this;
			// console.log(this.fqdn_level_data);
			
			/**
			 * KT node level byiteslf does not have profile data; so just to push it first manually
			 * 
			 * fqdn_level_data it has hirachrachy;  now is to flatten them to only have 1 level of fqdn for bubble chart display.
			 * 
			 */
			var temp_profile = this.fqdn_level_data[0].profile;
			var temp = [];
			$.each(this.fqdn_level_data, function(i,v){
				if(v.profile===temp_profile){
					for (var i = 0; i < v.nodes.length; i++) {
						v.nodes[i].push(["profile", v.profile]);

					};
					temp= temp.concat(v.nodes);
				}else{
					temp_profile = v.profile;
					for (var i = 0; i < v.nodes.length; i++) {
						v.nodes[i].push(["profile", v.profile]);
					};
					parsed_data = parsed_data.concat(temp);
					temp = v.nodes;
				}
			});
			if(temp.length!==1){
				parsed_data = parsed_data.concat(temp);
			}
			temp = [];
			$.each(parsed_data,function(index,value){
				temp.push(sapphire_lib_self_ptr.extractDataToObject(value));

			});
			return {children:temp};
		},
			/*** map the SVG and title/text of the bubble chart 
			 * KT: create the container scope
			 * 
			 * ***/
		mapSVG : function(){
			var diameterx = this.getMainchartContainerSize().width;
		  	var diametery = this.getMainchartContainerSize().height;

		 	var svg = d3.select('#bubblechart_container').append('svg')
		            .attr('width', diameterx+10)
		            .attr('height', diametery+10)
		            .attr('class', 'bubble');
			  //append the switch menu 
			 svg.append("rect")
			    .attr("id", "switchview_fqdn")
			    .attr("class", "switchview")
			    .attr("x", diameterx - 320)
			    .attr("y", diametery - 50)
			    .attr("width", 15)
			    .attr("height", 15)
			    .style("fill", "white")
			    .style("stroke", "green");

			 svg.append("rect")
			    .attr("id", "switchview_cluster")
			    .attr("class", "switchview")
			    .attr("x", diameterx - 220)
			    .attr("y", diametery - 50)
			    .attr("width", 15)
			    .attr("height", 15)
			    .style("fill", "green")
			    .style("stroke", "green");

			 svg.append("text")
			    .attr("x", diameterx - 300)
			    .attr("y", diametery - 35)
			    .style("font-size", "11px")
			    .style("text-anchor", "left")
			    .text("View FQDN");

			svg.append("text")
			    .attr("x", diameterx - 200)
			    .attr("y", diametery - 35)
			    .style("font-size", "11px")
			    .style("text-anchor", "left")
			    .text("View Cluster/VIP/Repl_Set");

			svg.append("text")
			    .attr("id", "title")
			    .attr("x", 30)
			    .attr("y", 10)
			    .style("font-size", "14px")
			    .style("text-anchor", "left")
			    .text("Current Cluster/VIP/Repl_Set: ");

			var Y_CORDINATES_FOR_APPEND_TEXT_BASE = 30;
			var Y_CORDINATES_FOR_APPEND_TEXT_INCREMET = 20;
			/**
			 * KT TODO: HEALTH_DEFINE_METRICS has beend efined for MPDB; but not yet for others. 
			 * this only append a slot for this but actual text is empty
			 * 
			 */
			for (var i = 0; i < this.HEALTH_DEFINE_METRICS.length; i++) {
				svg.append("text")
			    .attr("id", this.HEALTH_DEFINE_METRICS[i])
			    .attr("class", "metrics")
			    .attr("x", 30)
			    .attr("y", Y_CORDINATES_FOR_APPEND_TEXT_BASE)
			    .style("font-size", "14px")
			    .style("text-anchor", "left")
			    .text("");

			    Y_CORDINATES_FOR_APPEND_TEXT_BASE = Y_CORDINATES_FOR_APPEND_TEXT_BASE+ Y_CORDINATES_FOR_APPEND_TEXT_INCREMET;
			};

			var choice_btn = d3.select("svg").selectAll(".switchview");
			var sapphire_lib_self_ptr = this;

			/**
			 * KT this is D3 selection
			 * this is to switch FQDN view or cluster view
			 * 
			 * mapChart: is to map(verb) the container out to  the bubble chart
			 * data**: is to fill the data into the container to the bubble chart 
			 * 
			 */
			choice_btn.on('click', function(){
			    var choice = $(this).attr("id").substring(11);
			    if(sapphire_lib_self_ptr.chart_view_choice!==choice){
			      sapphire_lib_self_ptr.chart_view_choice=choice;
			      console.log(choice);
			      d3.select("svg").selectAll(".node").remove();
			      
			      /**
			       * x and y is the main container ; not for individual bubble
			       */
			      sapphire_lib_self_ptr.mapChart(svg, choice, diameterx, diametery);
			      sapphire_lib_self_ptr.dataChart(svg);

			    //bind the click function to each node:
			     // click to show key metrics
				$('g.node').bind('click', function(){
				var unitname = $(this).children('title').text();
					unitname = unitname.substring(0, unitname.indexOf(":")).trim();
					//if this is a cluster/repl_set.
					if(SAPPHIRE_LIB.arrayContains(sapphire_lib_self_ptr.cluster_list, unitname)){
						sapphire_lib_self_ptr.showModal(val);
					}else{
						sapphire_lib_self_ptr.showModal(sapphire_lib_self_ptr.searchClusterforFQDN(unitname));
					}
				});
			   }
			});

    		return {svg:svg, x:diameterx, y: diametery};

		},
		/** append the bubblechart to the SVG element **/
		/**
		 * to add map(v) the container (the prevous is to fill the large container with the corner button etc; this is to fill the svc of each bubble but no data yet
		 */
		mapChart : function(container, view, diameterx, diametery){
			var bubble = d3.layout.pack()
                .sort(null)
                .size([diameterx+50, diametery+10])
                .padding(7);
			var json;
			if(view==='cluster'){

				json = this.formatDataCluster();
				container.select('#switchview_fqdn').style("fill","white");
				container.select('#switchview_cluster').style("fill", "green");
				container.select('#title').text("Current Cluster/VIP/Repl_Set: ");
			}else if(view ==='fqdn'){
		
				/**
				 * KT: fill to fill the color of the button
				 */
				json = this.formatDataFQDN();
				container.select('#switchview_fqdn').style("fill", "green");
				container.select('#switchview_cluster').style("fill","white");
				container.select('#title').text("Current FQDN: ");
			}
			/**
			 * KT this is using D3 lib to auto compute the location for each bubble to "transform" to the right coordinates. 
			 * 
			 * using D3 layout.pack
			 */
			var node = container.selectAll(".node")
			      .data(bubble.nodes(json).filter(function(d) { return !d.children; }))
			      .enter().append("g")
			      .attr("class", "node")
			      .attr("transform", function(d) { return "translate(" + d.x + "," + d.y + ")"; });

			/**
			 * KT: title is the mouse over unit 
			 */
			node.append("title")
				.text(function(d) { return d.unit+ ": "+ d.updays+"d"; });

			node.append("circle")
				.transition()
				.duration(400)
				.attr("r", function(d) { return 1;  })
				.attr("id", function(d){return d.unit;})
				.attr("health", function(d){return d.health;})
				.attr('class', view+"_node")
				.style('fill', 'white')
				.style('stroke', 'green');

			node.append("text")
				.attr("dy", ".3em")
				.style("text-anchor", "middle")
				.style("fill", "white")
				.style("font-size", "11px")
				.text(function(d) { return d.unit.substring(0, d.r / 3); });
		},
		/*** generate the color, given its health ***/
		gradiantColor: function(health){
			 var color;
			if(health=='2'){
 				color = this.RED;
			    // color = 'url(#gradient_red)';
			}else if(health=='0'){
			    // color = 'green';
			    color = this.GREENS[Math.floor(Math.random()*this.GREENS.length)];
			}else if(health=='1'){
			    // color = 'yellow';
			    color = this.YELLOW;
			    // color = 'url(#gradient_yellow)';
			}else if(health=="-1"){
			    color = this.GREY;
			}
			  return color;
		},
		/***   generate the strokerColor, given the health  (stroke is the edge of the bubble) ***/
		strokeColor: function(health){
			 var color = this.GREY;
			  if(health== '2'){
			    // color = 'red';
			    color= d3.rgb(this.RED).brighter(3);
			    // color = 'url(#gradient_red)';
			  }else if(health=='0'){
			    color = d3.rgb(this.GREENS[0]).darker(2);
			    // color = 'url(#gradient_green)';
			  }else if(health=='1'){
			    color = d3.rgb(this.YELLOW).darker(1);
			    // color = 'url(#gradient_yellow)';
			  }
			  return color;
		},

		/***     append all the metrics to the bubble, color the bubble   
		 * 
		 * KT: add animation by transition; 
		 * 
		 * when mouse over: add animation to change color ; size a little bit
		 *  
		 *  ***/
		dataChart: function(container){
			var sapphire_lib_self_ptr = this;
			 var circles = container.selectAll("g.node").selectAll('circle');
			  circles.transition()
			  		.ease("bounce")
			  		.duration(1000)
			        .attr("r", function(d){return d.r})
			        // .style("opacity", function(d) {return sapphire_lib_self_ptr.generateTrasparent(d.health)})
			        .style("fill", function(d) { return sapphire_lib_self_ptr.gradiantColor(d.health); })
			        .style("stroke", function(d){ return sapphire_lib_self_ptr.strokeColor(d.health)})
			        .style("stroke-width", "2");

			  var bubbles = container.selectAll("g.node");

			  bubbles.on('mouseenter',function(d){
			  	  // console.log(d);
			      d3.select('#title').text('Current Cluster/Repl_Set: \r\r\r'+ d.unit);

			      $.each(sapphire_lib_self_ptr.HEALTH_DEFINE_METRICS, function(i,v){
			      	if(d[v]!==undefined){ 	
			      		d3.select('text[id="'+v+'"]').text(v+": \r\r\r"+d[v]);
			      	}
			      });
			      
			      d3.select(this).selectAll('circle')
			      .transition()
			      .duration(500)
			      .attr("r", function(d){return d.r+5;})
			      .style("fill",function(d){ 
			      							var currentcolor = d3.select(this).style('fill');
			      							d.currentcolor = currentcolor;
			      							return d3.rgb(currentcolor).darker(1);
			      							})
			      .style("stroke", "black").style("stroke-width", "2px");
			     
			  });

			  bubbles.on('mouseleave',function(d){
			      d3.select(this).selectAll('circle')
			      				.transition()
			      				.duration(500)
			      				  .style("fill", function(d) { 			  			
			      							return d.currentcolor;
			      					})
			      				  .attr("r", function(d){return d.r;})
			                      .style("stroke","#557140")
			                      .style("stroke-width","2px");
			      $('text.metrics').text("");
			  });      
		},
		/****   adjust the bubblechart color given the selection   
		 * 
		 * 
		 * 
		 * ****/
		adjustChartColor : function(valuemin, valuemax, metric_choice){
			var sapphire_lib_self_ptr = this;
			var circles = d3.select("svg").selectAll('circle');
			circles.transition()
					.ease('elastic')
					.style("fill", function(d){
						// console.log(d);
						var currentmetricvalue = d[SAPPHIRE_LIB.shortenMetricName(metric_choice, d.profile)];
						var currentmetrichealth; 
						// console.log(currentmetricvalue);
						if(currentmetricvalue <= valuemin){
							currentmetrichealth = 0;
						}else if(currentmetricvalue >= valuemax){
							currentmetrichealth = 2;
						}
						else if(currentmetricvalue>valuemin&&currentmetricvalue<valuemax){
							currentmetrichealth = 1;
						}else {
							currentmetrichealth = -1;
						}
						return sapphire_lib_self_ptr.gradiantColor(currentmetrichealth); 
					})
					.style("stroke", function(d){
						var currentcolor = d3.select(this).style('fill')
						return d3.rgb(currentcolor).darker(1);
					});
		},
		redrawChart : function(){
			$('div#bubblechart_container').empty(); 
			this.drawBubbleChart();
		},
		/***  draw the bubble chart, after the data is fetched  
		 * 
		 *  KT: DRAW is the last step to actually draw add svg
		 *  
		 *  VS. plot ( is the initial step )  
		 *  
		 *  draw is a later substep for plot
		 * ***/
		drawBubbleChart : function(){
			var params = this.mapSVG();
				this.mapChart(params.svg, this.chart_view_choice, params.x, params.y);
				this.dataChart(params.svg);

				//bind the click function to each node:
				var sapphire_lib_self_ptr = this;
				$('g.node').bind('click', function(){
					var unitname = $(this).children('title').text();
					unitname = unitname.substring(0, unitname.indexOf(":")).trim();
					//if this is a cluster/repl_set.
					var isCluster = false;
					for (var i = 0; i < sapphire_lib_self_ptr.cluster_list.length; i++) {
						if(SAPPHIRE_LIB.arrayContains(sapphire_lib_self_ptr.cluster_list[i].nodes, unitname)){
							isCluster = true;
						}
					}
					if(isCluster){
						sapphire_lib_self_ptr.showModal(unitname);
					}else{
						sapphire_lib_self_ptr.showModal(sapphire_lib_self_ptr.searchClusterforFQDN(unitname));
					}
				});
		},
		/*** plot the bubble chart from the scratch, fetch the data, then call the draw chart function
		 * 
		 * plot: 1. get data
		 * 
		 * 
		 * 
		 * ***/
		plotBubbleChart : function(){
			var url = "/getClusterLevelData?profile=";
			var cluster_data_call=[];
			var sapphire_lib_self_ptr = this;
			$.each(this.page_config.profile_names, function(i,v){
				cluster_data_call[i]= SAPPHIRE_LIB.ajaxCall(url+v, 'json', _.bind(function(resp){
					$.each(resp, function(index,value){
			              value.push(["profile",v]);
			        });
			        this.cluster_level_data = this.cluster_level_data.concat(resp);
			        // console.log(resp+this.cluster_level_data);
				},sapphire_lib_self_ptr));
			});
			// console.log(cluster_data_call);
			/**
			 * KT: WHEN / THEN: DEFERRED
			 * 
			 * Normally ajax callback is by a single api rquest; then call back handle on the single one.
			 *  
			 * MOTIVATOIN: This DEFERRED: is needed when you have MULTIPLE calls; and the call back require *ALL* response to ALL come back;
			 * 
			 * thus pass the ajax call handler array to this as "cluster_data_call" 
			 * 
			 * !!!!! THIS IS the starting point; called in initlist
			 * this will first call backend; then call draw
			 * 
			 * in draw: (1)map SVG( outer container) (2) mapBubbleChart( (3) dataChart (push datain) 
			 * 
			 */
			
			$.when.apply(null, cluster_data_call).then(function(){
				sapphire_lib_self_ptr.drawBubbleChart();
			});
		},

		/*** plot the heatmap from the scratch 
		 * 
		 * KT: PLOT is the STARTING POINT.
		 * ***/
		plotHeatMap : function(){
			this.mapContainer();
			this.dataMap();
			this.setSingleMapWidth();
			var sapphire_lib_self_ptr = this;
			$('.heatmap_unit').bind('click', function() {
				var clustername = $(this).attr('unit');
				var fqdn = $(this).attr('fqdn');
			
				sapphire_lib_self_ptr.showModal(clustername);
				var options = $('#host_list_dropdown').find('option');
				//console.log(options);
				$.each(options, function(i, v) {
					if ($(v).html() == fqdn) {
						$(v).attr('selected', 'selected');
					}
				});
				sapphire_lib_self_ptr.plotKeyMetricChart();
			});
		},
		/*** adjust the main page layout
		 * 
		 *  When browser window resize. 
		 *  ***/
		adjustLayout: function(){
			this.setMainchartContainerSize();
			this.setModalDivSize();
			if(this.page_config.view_choice=='map'){
				this.setSingleMapWidth();
			}
			else if(this.page_config.view_choice=='chart'){
				this.redrawChart();//*****************************************
			}
		},

		// append the dropdownlist option, draw the chart and show the overlapping
		
		/**
		 * show the key metrics
		 */
		
		showModal: function(clustername) {
			this.page_config.currentcluster = clustername;
			$("#the_main_modal_label").html(clustername);
			$('#host_list_dropdown').empty();
			$('#all_fqdn_btn').attr('active', 'false');
			// find the host list of this cluster
			var hostlist = this.getHostListByCluster(clustername);
			// console.log(hostlist);
			window.localStorage.removeItem('host_list');
			this.page_config.currentprofile = this.getProfileByCluster(clustername);
			
			SAPPHIRE_LIB.setObjectLocalStorage('host_list', hostlist);
			// append the host list to the clustername
			$.each(hostlist, function(i, value) {
				$('<option>').text(value).appendTo($('#host_list_dropdown'));
			});
			$('#theMainModal').modal('show');
			$('#host_list_dropdown').change(this.plotKeyMetricChart());
		}
    };
	return sapphire_lib;
}());
