
/**
 * KT all metadata about a page; every time go to another; will trigger the event of saving this object to browser; 
 * no size limit; simplier than sesson HTML5
 * 
 * e.g.
	$('#full_detail_btn').bind('click', function() {
		SAPPHIRE_LIB.setObjectLocalStorage('page_Config', page_config);
 */
var SAPPHIRE_Page_Config = (function(){
	/*** page_config will store all the related information and pass to the next page using local storage ***/
	var sapphire_config = function(){
		this.profile_names =  []; 		//store the profile list
		this.currentprofile = ""; 		//store the current profile
		this.currentcluster = ""; 		// store the current cluster to pass to controller
		this.currentFQDN = ""; 		//current fqdn choice
		this.update = true; 					// flag to control the auto-update
		this.view_choice = 'map';
		this.currentmetric = "";
		this.initProfile();
	};

	sapphire_config.prototype = {
		/*** parse the url to get the chosen profiles ***/
		initProfile : function(){
			var AprofileHandler = {
				getprofiles: function(){
					// this will go get browser's address bar 
					var searchString = window.location.search.substring(3),
					    hash = searchString.split(',');
						parsedString = [];
					for(var i = 0; i<hash.length;i++){
						parsedString.push(hash[i].substring(hash[i].indexOf("_") + 1, hash[i].indexOf(".")));
					}
					return parsedString; // this is the array that is return.
				}
			};
			this.profile_names = AprofileHandler.getprofiles();
		}
	};		
	return sapphire_config;
}());

// ()); this is a self call.  function()() means it is a self call;  
// var page_config = new SAPPHIRE_Page_Config(); will return the internal sapphire_config 



		



