var SAPPHIRE_LIB = SAPPHIRE_LIB ? SAPPHIRE_LIB: {};
var _ = _ ? _ : {};

$(document).ready(function(){
	Highcharts.setOptions({
	global: {
		useUTC: false
	}
	});

	window.localStorage.clear();
	var page_config = new SAPPHIRE_Page_Config();
	console.log(page_config);
	var lib = new SAPPHIRE_DETAIL_LIB(page_config);
	lib.init();
	
	var btns = $('.timerange');
	$.each(btns, function(i,v){

		if($(this).text()==lib.currentrangeselection){

		lib.fillDatePicker();
			$(this).addClass("active");
		}
	});

	$("#sapphire_nav").bind('click',function(){
		var profile_name = lib.page_config.profile_name;
		// var profile_name = SAPPHIRE_LIB.getObjectLocalStorage('profile_name');
		console.log(profile_name);
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
	
	$('#submit_btn').bind('click', function(){
		lib.fetchData();
	});
	$('.timerange').bind('click', function(){
		console.log(lib.currentselection);
		if(lib.currentselection==$(this).text()){
			return;
		}
		lib.updateData($(this).text());
		lib.currentrangeselection = ($(this).text());

	});

});