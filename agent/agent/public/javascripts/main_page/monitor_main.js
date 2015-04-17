var SAPPHIRE_LIB = SAPPHIRE_LIB||{};
var _ = _ ? _ : {};

$(document).ready(function() {
	window.localStorage.clear();
	var page_config = new SAPPHIRE_Page_Config();
	console.log(page_config);
	var lib = new SAPPHIRE_MONITOR_LIB(page_config);

	Highcharts.setOptions({
		global : {
			useUTC : false
		}
	});


	lib.adjustLayout();
	
	/**
	 * KT. STARTING POINT: This is the key: will 
	 * initList will fetch all the data for future use
	 * 
	 * How to decide when to add . some DOM/DIV are predefined. some are generated on the fly. For those pre exist; can do here.
	 * Otherwise have to do after the DOM is generated in the JS. 
	 * 
	 * 
	 */
	lib.initList();

	if(lib.page_config.view_choice==='map'){
		$('#map_view_btn').addClass('active');
		$('#bubblechart_container').hide();
		$('#heatmap_container').show();

	}else{
		$('#chart_view_btn').addClass('active');
		$('#heatmap_container').hide();
		$('#bubblechart_container').show();
	}
	
	lib.updateRefreshed();
	// console.log(lib);
	$('.heatmap_unit').bind('click', function() {
		var clustername = $(this).attr('unit');
		var fqdn = $(this).attr('fqdn');
		console.log(clustername);
		lib.showModal(clustername);
		var options = $('#host_list_dropdown > option');
		//console.log(options);
		$.each(options, function(i, v) {
			if ($(v).html() == fqdn) {
				$(v).attr('selected', 'selected');
			}
		});
		lib.plotKeyMetricChart();

	});

	$('#sapph_viewchoice > .view_choice_btn').bind('click', function(){
		var choice = $(this).attr('value')
		if( choice !== lib.page_config.view_choice){
			if(choice =='map'){
				$('#bubblechart_container').hide();
				$('#heatmap_container').show();
				lib.page_config.view_choice = 'map';
				$("div#sapph_contentchoice").show();
			}else{
				$('#heatmap_container').hide();
				$('#bubblechart_container').show();
				lib.page_config.view_choice = 'chart';
				$("div#sapph_contentchoice").hide();
			}
		}
	});

	$('#searchCluster').change(function(){
		var cluster_name = $('#searchCluster').val();
		if (cluster_name == "" || cluster_name == null || cluster_name == undefined) {
			return;
		}
		lib.page_config.currentcluster = cluster_name;
		lib.showModal(cluster_name);
	});

	/**
	 * KT: this is the right bar
	 */
	$('#searchFQDN').change(function(){
		
			var fqdn_name = $('#searchFQDN').val();
			if (fqdn_name == "" || fqdn_name == null || fqdn_name == undefined) {
			return;
			}
			lib.page_config.currentfqdn = fqdn_name;
			var cluster = lib.searchClusterforFQDN(fqdn_name);
			lib.page_config.currentcluster = cluster;
			console.log(cluster);
			lib.showModal(cluster);
			
			var options = $('#host_list_dropdown > option');
			//console.log(options);
			$.each(options, function(i, v) {
				if ($(v).html() == fqdn_name) {
					$(v).attr('selected', 'selected');
				}
			});
			lib.plotKeyMetricChart();
	
	});

	/**
	 * KT: this is the key metrics chart
	 */
	$('#host_list_dropdown').change(function() {
		var fqdn_name = $('#host_list_dropdown option:selected').text();
		if (fqdn_name == "" || fqdn_name == null || fqdn_name == undefined) {
			return;
		}
		lib.page_config.currentfqdn = fqdn_name;
		lib.plotKeyMetricChart();
	});

	/**
	 * When click again to disable the all fqdn
	 */
	$('#all_fqdn_btn').bind('click', function(){
		if($(this).attr('active')=='true'){
			$(this).attr('active','false');
			$('#host_list_dropdown').removeAttr('disabled');

			lib.plotKeyMetricChart();
		}else{
			$('#host_list_dropdown').attr('disabled', 'disabled');
			$(this).attr('active','true');

			lib.plotKeyMetricChartAllFQDN();
		}
	});

	
	/**
	 * KT: this is the key metrics chart "MORE"
	 */
	$('#full_detail_btn').bind('click', function() {
		SAPPHIRE_LIB.setObjectLocalStorage('page_Config', page_config);
		// window.localStorage.removeItem('profile', $('#the_main_modal_label').html());
		document.location.href = '../fullmetrics';
	});

	
	/**
	 * THE TOP LEFT ICON:
	 */
	$('#sapphire_nav').bind('click',function(){

		document.location.href = '../../listprofile/';
	});
	//
	/**
	 * !!! CRON UPDATE KEY update every 5min ;
	 */
	 
	setInterval(_.bind(lib.updateData ,lib), 300000);

	 console.log(lib);

	$(window).resize(function() {
		console.log("resize fired");
		lib.adjustLayout();
	});
});