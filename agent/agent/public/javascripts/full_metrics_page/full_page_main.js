var SAPPHIRE_LIB = SAPPHIRE_LIB ? SAPPHIRE_LIB: {};

var _ = _ ? _ : {};

$(document).ready(function() {
	
	
	/**
	 * UTC when false will only use the SERVER timezone; rather than local time zone.
	 */
	Highcharts.setOptions({
		global : {
			useUTC : false
		}
	});
	
	/**
	 * KT: when all fqdn is activated; this buttone is disabled. so need to be removed
	 */
	$('#full_host_list_dropdown').removeAttr('disabled');
	var page_config = SAPPHIRE_LIB.getObjectLocalStorage("page_Config");
	var lib = new SAPPHIRE_FULL_LIB(page_config);
	lib.init();
	
	/**
	 * drop down of fqdn in the right top corner.
	 */
	lib.appendDropDownList();

	$('#currentclusterfqdn').html("<strong>"+lib.page_config.currentcluster+"</strong>"+"  :     "+lib.page_config.currentfqdn);
	
	lib.plotFullMetricsChart(lib.page_config.currentfqdn);

	$('#full_host_list_dropdown').change(function() {
		$('#full_metrics_container').empty();
		fqdn_name = $('#full_host_list_dropdown option:selected').text();
		$('#currentclusterfqdn').html("<strong>"+lib.page_config.currentcluster+"</strong>"+"  :     "+fqdn_name);
		lib.plotFullMetricsChart(fqdn_name);
		lib.page_config.currentfqdn = fqdn_name;
	});

	$("#sapphire_nav").bind('click',function(){
		var profile_name = lib.page_config.profile_name;
		// var profile_name = window.localStorage.getItem('profile_name').split(',');
		if(profile_name==undefined){
			document.location.href = '../../listprofile/';
		}
		var url = '../../?p=';
		$.each(profile_name, function(i,v){
			url = url +'queryprofile_'+v+'.json'+',';
		});
		url = url.substring(0,url.length-1);
		document.location.href = url;
	});

	$('#all_fqdn_btn').bind('click', function(){
		if($(this).attr('active')=='true'){
			$(this).attr('active','false');
			$('#full_host_list_dropdown').removeAttr('disabled');

			lib.plotFullMetricsChart($('#full_host_list_dropdown').val());
		}else{
			$('#full_host_list_dropdown').attr('disabled', 'disabled');
			$(this).attr('active','true');


			var charts = $('.metrics_unit');
			var metrics = $('.highcharts-title');
			$.each(charts, function(i,v){
				$(v).empty();
				var url = '/datapointsforall?profile='+lib.page_config.currentprofile+'&clustername='+lib.page_config.currentcluster+"&metricname="+$(metrics[i]).text();
				lib.plotMetricDataFromUrlAllFQDN(url, v, $(metrics[i]).text());
			});
		}
	});
});