/**
 * @module CLOUD.UTILS
 * @description Utility methods to be used in the Cloud Portal JS code
 * @public
 */
(function($){
	// Create a namespace
	$.CLOUD = $.sub();
	
	// Definition of the UTILS namespace.
	// To be used as follows:  $.CLOUD.UTILS.<methodName>();
	$.CLOUD.UTILS =  {	
		/**
		 * @method generateLink
		 * @description Given a source URL and an object with attributes, generates a clickable URL link
		 * @param {String} sSource String with a URL
		 * @param {Object} oAttributes Attributes to be added to the URL
		 * @param {Number} nUrlLength Length of the Link, if any
		 * @public
		 * @return {String} A string with the clickable link OR the original string
		 */
		generateLink : function (sSource, oAttributes, nUrlLength) {
			var scope = this;
			var attributes = oAttributes || {},  attrs = "";

			var reg = new RegExp("(\\s?)((http|https|ftp)://[^\\s<]+[^\\s<\.)])", "gim");
			// Check if the string has a url	
			if (!sSource.match(reg)) {
				return sSource;
			}
			// Add the attributes
			for(var name in attributes) {
				attrs += " "+ name +'="'+ attributes[name] +'"';
			}
			
			// Truncate the length of the displayed string if necessary		
			if (!nUrlLength) {
				sSource = sSource.replace(reg, '$1<a href="$2"'+ attrs +'>$2</a>');
			} else {
				var urlStr = sSource;
				urlStr = scope.truncateString(urlStr, nUrlLength);
				sSource = sSource.replace(reg, '$1<a title="$2" href="$2"'+ attrs +'>' + 
						urlStr + '</a>');				
			}

			return sSource;
		},
		
		/**
		 * @method truncateString
		 * @description Truncates a string to a given length
		 * @param {String} sSource String with a URL
		 * @param {Number} nLength Length of the String
		 * @public
		 * @return {String} A truncated string of length: nLength
		 */		
		truncateString : function (sSource, nLength) {
			return sSource.substr(0, nLength - 1) + (sSource.length > nLength ? '...' : '');
		},
		
		/**
		 * @method formatStringDate
		 * @description Transforms a date in string  to the specified format.
		 * @param {String} sSource The date in string format
		 * @param {String} newFormat New format for the date
		 * @public
		 * @return {String} The date in the new format.
		 */		
		formatStringDate : function (sSource, newFormat) {
			if (!sSource || sSource == "") {
				return "";
			}

			try {
				var dObj = new Date(sSource);
				if (!dObj) {
					// Could not convert to date, return original
					return sSource;
				}
				return dObj.format(newFormat);
			} catch (exc) {
				// Let's check the format passed by Statehub in some instances
				try {
					var parts = sSource.match(/(\d+)\.(\d+)\.(\d+)\s*\@\s*(\d+)\:(\d+)\:(\d+)\s+(\w+)/);
					if (parts) {
						var sDate = [parts[3], "/",parts[2], "/" ,parts[1]," ",parts[4],":",
						             parts[5], ":",parts[6], " ", parts[7]].join("");
						var dObj = new Date(sDate);
						if (!dObj) {
							return sSource;
						}
						return dObj.format(newFormat);
				}
				} catch (exc2) {
					// Could not convert to date, return original
					return sSource;
				}
				
			}
		}	
		
	}
})(jQuery);


$.CLOUD.OVERLAYS = {};

/**
 * @module CLOUD.PACKAGE_DETAILS
 * @description Class to be used to interact with the Package Details Datatable 
 *     inside the Package Details Overlay.
 * @public
 */
$.CLOUD.OVERLAYS.PACKAGE_DETAILS =  {

	/**
	 * @property PACKAGE_TYPES
	 * @description List of packages available
	 * @public
	 * @type JSON
	 * @final
	 */
	PACKAGE_TYPES : {
		'system' : 'SYSTEM',
		'configuration' : 'CONFIGURATION',
		'application' : 'APPLICATION'
	},
	
	/**
	 * @property CONST
	 * @description Set of constants to be used in this object
	 * @public
	 * @type JSON
	 * @final
	 */	
	CONST : {
		'MAX_LENGTH_URL' : 20,
		'MAX_LENGTH_OVERRIDEN_FILE' : 80,
	},
	
	/**
	 * @property ERRORS
	 * @description Set of constants for Error messages
	 * @public
	 * @type JSON
	 * @final
	 */		
	ERRORS : {
		'NO_DATA' : 'No Data Available',
		'NO_RECORDS_FOUND' : 'No Records Found'
	},
	
	/**
	 * @property openIconURL
	 * @description Stores the Open icon URL
	 * @public
	 * @type String
	 */	
	openIconURL : '',
	
	/**
	 * @property closedIconURL
	 * @description Stores the Closed icon URL
	 * @public
	 * @type String
	 */	
	closedIconURL : '',
	
	/**
	 * @method setDefaultIcons
	 * @description Sets the URLS for the open/closed Icon URLs
	 * @param {String} sOpenIconURL URL for the Open icon
	 * @param {String} sOpenIconURL URL for the Closed icon
	 * @public
	 */	
	setDefaultIcons : function(sOpenIconURL, sClosedIconURL) {
		this.openIconURL = sOpenIconURL;
		this.closedIconURL = sClosedIconURL;		
	},
	
	/**
	 * @method displayTableErrorMessage
	 * @description Displays an error message in the table contents.
	 * @param {Object} oTable Table Object
	 * @param {String} errorMsg Error message to be displayed
	 * @public
	 */
	displayTableErrorMessage : function(oTable, sMessage) {
		if (!oTable) {
			return;
		}
		
		// Convert the message to a String if needed.
		sMessage = sMessage + "";
		// Remove the word "Error:" from the message
		var regExp = new RegExp("^Error\:", "gim");
		if (sMessage.match(regExp)) {
			sMessage = sMessage.replace(regExp, "");
		}

		// If the table has settings...
		if (oTable.fnSettings) {
			oTable.fnSettings().oLanguage.sInfoEmpty = sMessage;
			oTable.fnSettings().oLanguage.sEmptyTable = sMessage;
			oTable.aaData = [];
			oTable.fnDraw();
		} else { // Otherwise just display the error in a cell
			var inner = ['<tr><td class="errorMessage">', sMessage, '</td></tr>'];
			$('tbody', oTable).html(inner.join(""));
		}
	},
	
	/**
	 * @method processValueCell
	 * @description Formats the value if it is a URL or a Date
	 * @param {String} key Key associated to this value
	 * @param {String} value Data to be processed
	 * @public
	 * @return {String} processed value
	 */
	processValueCell : function(key, value) {
		if (!value || value == "") {
			return "";
		}
		// Determine if the value is a URL
		value = $.CLOUD.UTILS.generateLink(value, {},
				$.CLOUD.OVERLAYS.PACKAGE_DETAILS.CONST.MAX_LENGTH_URL);

		// If there is no key, just return the value
		if (!key) {
			return value;
		}

		// If we have a date/time, convert it to the right format.
		if (key.match(/time/i)) {
			value = $.CLOUD.UTILS.formatStringDate(value, 'mm/dd/yyyy HH:MM:ss');		 
		}

		return value;
	},
	
	/**
	 * @method fnFormatDetails
	 * @description Formats the Datatable structure for the Package Details overlay.
	 * @param {String} packageType Type of Package for this row.
	 * @public
	 * @return {String} HTML for the detailed datatable(s)
	 */
	fnFormatDetails : function(packageType) {	
		var arrOut = []; // To store the html elements.
		
		switch (packageType) {
			case  'system' : 		
				arrOut.push('<table id="system-package-view" class="package-detail-view-summary">');
				arrOut.push('<thead></thead>');
				arrOut.push('<tbody></tbody>');
				arrOut.push('</table>');				
				break;
				
			case 'application' :
				// Add the navigation links for Application Package
				arrOut.push('<div id="package-bundle-links"><span>');
				arrOut.push('<a class="links activeLink" href="#">Top Level Bundle</a>');
				arrOut.push('<span>&nbsp;|&nbsp;</span>');		
				arrOut.push('<a class="links" href="#">Fixed Plan Bundle</a>');	
				arrOut.push('</span></div>');
				
				// Add the Top Level Bundle Table
				arrOut.push('<table id="top-level-bundle" class="package-detail-view">');
				arrOut.push('<thead></thead>');
				arrOut.push('<tbody></tbody>');
				arrOut.push('</table>');
				
				// Add the Fixed Plan Bundle Table		
				arrOut.push('<table id="fixed-plan-bundle" class="package-detail-view">');
				arrOut.push('<thead></thead>');
				arrOut.push('<tbody></tbody>');
				arrOut.push('</table>');				
				break;
				
			case 'configuration' : 		
				arrOut.push('<table id="config-package-view" class="package-detail-view-summary">');
				arrOut.push('<thead></thead>');
				arrOut.push('<tbody></tbody>');
				arrOut.push('</table>');				
				break;				
		}
		
		return arrOut.join("");
	},
		
	/**
	 * @method getMetadataFromJSON
	 * @description Retrieves the Metadata object from the passed JSON object.
	 *     This metadata will be used to populate the datatables associated with the
	 *     package details information views.
	 * @param {Object} oJSON JSON object to be parsed
	 * @param {Object} sVersion Version of the Package to look for or ""	 
	 * @public
	 * @return {Object} Metadata object
	 */	
	getMetadataFromJSON : function(oJSON, sVersion) {
		var metaDataObj = {}, metaDataStr = null, versionsObj = {};
		if (typeof oJSON == "string") {
			oJSON = JSON.parse(oJSON);
		}		

		if (!typeof oJSON == "object") {
			return metaDataObj;
		}
		
		// Check if the versions object is found within the JSON
		try {
			versionsObj = oJSON['result']['result'][0]['versions'];
		} catch (exception) {
			return metaDataObj;
		}

		// If there is a version specified, fetch the metadata
		// from that sub-json
		if (sVersion && sVersion != "") {
			if (versionsObj[sVersion]) {
				return JSON.parse(versionsObj[sVersion]);
			}
		}
		
		// Otherwise, find the first version object, and get the metadata from it.
		for (var key in versionsObj) {
			metaDataStr = versionsObj[key]['metaData'];
			if (!metaDataStr) break;
			
			// Convert the metadata string to JSON
			metaDataObj = JSON.parse(metaDataStr);
			break;
		}

		return metaDataObj;
	},
	
	/**
	 * @method makeAjaxRequest
	 * @description Makes the Ajax request to Statehub to get the metadata JSON to build the
	 *     Package Details Datatables
	 * @param {Object} packagesDt Parent DataTable Object containing the row to be expanded
	 * @param {Object} nTr Row Object to be expanded
	 * @param {String} sRequestURL URL for the request to get the package details data
	 * @param {Object} oParams Parameters needed for the AJAX request	 
	 * @public
	 */
	makeAjaxRequest : function(packagesDt, nTr, sRequestURL, oParams) {
		var methodScope = this; // Reference to the current scope.
		$.post(sRequestURL, oParams, function processResponse (jsonObj) {
			// Make sure we have a JSON object and not a string
			if (typeof jsonObj == "string") {
				jsonObj = JSON.parse(jsonObj);
			}

			// Validations...
			if (!jsonObj || !typeof jsonObj == "object") {
				return jsonObj;
			}

			// Get the filtered JSON (metadata)
			jsonObj = methodScope.getMetadataFromJSON(jsonObj, oParams.version);

			// Build the datatable, given the metadata
			methodScope.setUpPkgDetailDataTables(packagesDt, nTr, oParams, jsonObj);
		});
	 },
	
	/**
	 * @method populateSystemPackageTable
	 * @description Populates the Fixed Plan Bundle Datatable from the JSON Object.
	 * @param {Object} oPkgDetailsSummaryTable Reference to the Datatable object to place the data in
	 * @param {Object} jsonObj JSON object with the data to be rendered
	 * @public
	 */
	populateSystemPackageTable : function(oPkgDetailsSummaryTable, jsonObj) {
		var methodScope = this; // Reference to the current scope.

		try {
			var inner = [], // Aux. array to be used to place the html contents of the table
			value = '',
			packageDetails = null;

			// Validations...
			if (!jsonObj || !typeof jsonObj == "object") {
				throw new Error(methodScope.ERRORS.NO_DATA);
			}

			// Get the package details JSON
			packageDetails = jsonObj["packageDetails"] || {};				 
			if (!packageDetails || $.isEmptyObject(packageDetails)) {
				throw new Error(methodScope.ERRORS.NO_DATA);
			}

			// Store the number of package detail items in the JSON
			var itemsProcessed = 0;

			// Convert the data from the JSON structure to an array that
			// the datatable object can consume.
			inner = ['<tr>'];		 
			for (var key in packageDetails) {
				value =  packageDetails[key];
				++itemsProcessed;

				// Transform the value if it is a data or a URL
				value = methodScope.processValueCell(key, value);

				// Add a column
				inner.push(['<td class="label">' , key , ':</td>'].join(""));
				inner.push(['<td>' , value , '</td>'].join(""));

				// Show a new row for every 3 items
				if ((itemsProcessed % 3) == 0) {
					inner.push('</tr><tr>');
				}
			}

			// Close the last row tag
			if ((itemsProcessed % 3) != 0) {
				inner.push('</tr>');
			} else {
				inner.pop(); // Remove the last </tr>, since it was added before.
			}

			// Set the body of the table contents
			$('tbody', oPkgDetailsSummaryTable).html(inner.join(""));
		} catch (exception) {
			// This will show the error message
			methodScope.displayTableErrorMessage(oPkgDetailsSummaryTable, exception);				 
		}
		return true;
	 },
	 
	/**
	 * @method populateConfigPackageTable
	 * @description Populates the Configuration PackageDatatable from the JSON Object.
	 * @param {Object} oPkgConfigTable Reference to the Datatable object to place the data in
	 * @param {Object} jsonObj JSON object with the data to be rendered	 
	 * @public
	 */
	populateConfigPackageTable : function(oPkgConfigTable, jsonObj) {
		var methodScope = this; // Reference to the current scope.

		try {
			var inner = [], // Aux. array to be used to place the html contents of the table
			value = '',
			packageDetails = null;

			// Validations...
			if (!jsonObj || !typeof jsonObj == "object") {
				throw new Error(methodScope.ERRORS.NO_DATA);
			}

			// Get the package details JSON
			packageDetails = jsonObj["packageDetails"] || {};				 
			if (!packageDetails || $.isEmptyObject(packageDetails)) {
				throw new Error(methodScope.ERRORS.NO_DATA);
			}

			// Store the number of package detail items in the JSON
			var itemsProcessed = 0;

			// Convert the data from the JSON structure to an array that
			// the datatable object can consume.
			inner = ['<tr>'];		 
			for (var key in packageDetails) {
				value =  packageDetails[key];
				++itemsProcessed;

				// Transform the value if it is a data or a URL
				value = methodScope.processValueCell(key, value);

				// Add a column
				inner.push(['<td class="label">' , key , ':</td>'].join(""));
				inner.push(['<td>' , value , '</td>'].join(""));

				// Show a new row for every 3 items
				if ((itemsProcessed % 3) == 0) {
					inner.push('</tr><tr>');
				}
			}

			// Close the last row tag
			if ((itemsProcessed % 3) != 0) {
				inner.push('</tr>');
			} else {
				inner.pop(); // Remove the last </tr>, since it was added before.
			}

			// Now let's read the overriden files, if any
			var pkgAdditionalDet = jsonObj["packageAdditionalDetails"] || {};				 
			if (pkgAdditionalDet && pkgAdditionalDet["Overridden Files"]) {
				var overridenFiles = pkgAdditionalDet["Overridden Files"];
				var numOverridenFiles = overridenFiles.length || 0;
				var fileName, numColSpans;

				// Create a row with a list with the filenames
				if (numOverridenFiles > 0) {
					numColSpans = ((itemsProcessed % 3) > 0) ? 6 : (itemsProcessed * 2);
					inner.push('<tr><td class="label">Overriden Files:</td></tr>');
					inner.push('<tr><td colspan=" ' + numColSpans + '"><ul>');

					for (var idx = 0; idx < overridenFiles.length; ++idx) {
						fileName = overridenFiles[idx];
						fileName = $.CLOUD.UTILS.truncateString(fileName,
								$.CLOUD.OVERLAYS.PACKAGE_DETAILS.CONST.MAX_LENGTH_OVERRIDEN_FILE);
						inner.push(['<li>', fileName, '</li>'].join(""));
					}
					inner.push('</ul></td></tr>');							
				}
			}

			// Set the body of the table contents
			$('tbody', oPkgConfigTable).html(inner.join(""));

		} catch (exception) {
			// This will show the error message
			methodScope.displayTableErrorMessage(oPkgConfigTable, exception);				 
		}
		return true;
	 },
	 
	/**
	 * @method getDefaultTitlesForDataTable
	 * @description Retrieves an array with the default title names, given a JSON object
	 * @param {Object} jsonObj Object with the JSON data
	 * @param {String} keyToLookFor Key to be used to search the subset we are looking for
	 *     in the JSON structure.
	 * @public
	 * @return Array with the Default Title Objects to be used to create the datatable
	 */	 
	getDefaultTitlesForDataTable : function(jsonObj, keyToLookFor) {
		var defTitles = [];

		// Check if the data that we need is in the JSON object
		if (!jsonObj || $.isEmptyObject(jsonObj) || !typeof jsonObj == "object" 
			|| !jsonObj["packageAdditionalDetails"] || !jsonObj["packageAdditionalDetails"][keyToLookFor]) {
			return defTitles;
		}

		// Get the application bundles object (JSON) from the main JSON.
		var bundleArr = jsonObj["packageAdditionalDetails"][keyToLookFor];

		// Check that the array of bundles exist
		if (!bundleArr || bundleArr.length < 1) {
			return defTitles;
		}
		
		// Get the first row
		var firstRow = bundleArr[0];
		// Find the number of columns
		for (var k in firstRow) {
			 defTitles.push({ "sTitle": "" });
		}		
		return defTitles;
	},
	 
	/**
	 * @method populateTableFromBundle
	 * @description Populates the actual datatable from the data passed in the bundle array
	 * @param {Object} oTable Reference to the Datatable object to place the data in
	 * @param {Array} bundleArr Array with the data to place in the datatable.
	 * @public
	 */	 
	populateTableFromBundle : function(oTable, bundleArr) {
		var methodScope = this; // Reference to the current scope.	
		var oSettings = oTable.fnSettings(); // Get the table settings 
		var colTitles = [], // Store column titles
		aData = [],  // Store the whole data for this table settings
		inner = [],  // Aux. arr to store col. data	
		item, value;		

		// Check that the array of bundles exist
		if (!bundleArr || bundleArr.length < 1) {
			return true;
		}

		// Get the list of columns titles and place them in an array
		var firstRow = bundleArr[0];
		var numTotalColumns = 0, numTdCells = 0;
		for (var k in firstRow) {				 
			colTitles.push(k);
			++numTotalColumns;
		}	 

		// Create the rows for the table
		// 'item' is an array with the JSON data for this row.
		for (var index in bundleArr) {
			item = bundleArr[index];
			aData = [];
			inner = []; // aux. array to place the column data.

			// Create a table row with the data provided in item (row)
			numTdCells = 0;
			for (var key in item) {
				++numTdCells;
				
				// Transform the value if it is a data or a URL
				value = methodScope.processValueCell(key, item[key]);

				// Create the columns
				inner.push(["<td>" , value , "</td>"].join(""));

				// Add this column to the Data
				aData.push(value);
			}
			
			// In case the number of processed cells does not match the total
			// number of columns, add empty TD cells.
			if (numTdCells < numTotalColumns) {
				for (var count = numTdCells+1; count <= numTotalColumns; ++count) {
					inner.push("<td></td>");
					// Add this column to the Data table
					aData.push("");					
				}
			}

			// Add the data and then replace DataTable's generated <tr>			
			var iIndex = oTable.oApi._fnAddData( oSettings, aData );

			// Create the HTML row
			var row = ["<tr>" , inner.join("") , "</tr>"].join("");	
			// Create the row Object and get a hold of the columns
			var nTr = $(row)[0];

			// We need the row to be assigned to the settings of the datatable.
			oSettings.aoData[ iIndex ].nTr = nTr;
		}

		// Update the table settings
		oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();

		// Update the table column titles
		for (var idx in colTitles) {
			// Reset the column title
			oSettings.aoColumns[idx].nTh.innerHTML = colTitles[idx];			 
		}

		return true;
	}, 
	 
	/**
	 * @method populateTopLevelBundleTable
	 * @description Populates the Top Level Bundle Datatable
	 *     The JSON object with the data to be used to populate the datatable
	 *     will be retrieved via AJAX call.
	 * @param {Object} oTopLevelBundle Obj referring to the Top Level Bundle TABLE
	 * @param {Object} oFixedPlanBundleTable Obj referring to the Fixed Plan DATATABLE
	 * @param {Object} jsonObj JSON object with the data to be rendered	 
	 * @public
	 */
	 populateTopLevelBundleTable : function(oTopLevelBundle, oFixedPlanBundleTable, jsonObj) {
		 var methodScope = this; // Reference to the current scope.

		 try {
			 // Get a hold of the Top level bundle Datatable.
			 // (dataTable object itself  cannot be passed directly as an argument of this method from the datatable
			 // builder)
			 var oTable = oTopLevelBundle.dataTable();

			 // Check if the data that we need is in the JSON object
			 if (!jsonObj || $.isEmptyObject(jsonObj) || !typeof jsonObj == "object" 
				 || !jsonObj["packageAdditionalDetails"]) {
				 throw new Error(methodScope.ERRORS.NO_DATA);
			 }

			 // Get the application bundles object (JSON) from the main JSON.
			 var applicationBundles = jsonObj["packageAdditionalDetails"]["applicationBundles"] || [];
			 if (!applicationBundles || $.isEmptyObject(applicationBundles)) {
				 throw new Error(methodScope.ERRORS.NO_DATA);
			 }

			 // Populate the datatable from the application bundles.
			 methodScope.populateTableFromBundle(oTable, applicationBundles);
			 
			 // Now populate the other datatable (Fixed Bundle table) using the 
			 // same JSON object, to avoid doing another AJAX request
			 methodScope.populateFixedPlanBlundeTable(jsonObj, oFixedPlanBundleTable);

			 // Draw the table.
			 oTable.fnDraw();
			 
		 } catch (exception) {
			 // This will show the default empty table message.
			 methodScope.displayTableErrorMessage(oTopLevelBundle, 
			 	methodScope.ERRORS.NO_RECORDS_FOUND);
		 }

		 return true;
	 },
	
	/**
	 * @method populateFixedPlanBlundeTable
	 * @description Populates the Fixed Plan Bundle Datatable from the JSON Object.
	 * @param {Object} jsonObj JSON Object containing the data to be placed in the datatable
	 * @param {Object} oTable Reference to the Datatable object to place the data in
	 * @public
	 */
	 populateFixedPlanBlundeTable : function(jsonObj, oTable) {
		 var methodScope = this; // Reference to the current scope.
		 try {
			 // Check if there is data
			 if (!jsonObj || $.isEmptyObject(jsonObj) || !jsonObj["packageAdditionalDetails"]) {
				 throw  new Error(methodScope.ERRORS.NO_DATA);
			 }
			 
			 // Get the list of column titles
			 var dependentBundles = jsonObj["packageAdditionalDetails"]["dependentBundles"] || [];
			 if (!dependentBundles || $.isEmptyObject(dependentBundles)) {
				 throw  new Error(methodScope.ERRORS.NO_DATA);
			 }
			 
			 // Populate the datatable from the dependent bundles.			 
			 methodScope.populateTableFromBundle(oTable, dependentBundles);
		 } catch (ex) {
			// This will show an empty table message
			 methodScope.displayTableErrorMessage(oTable, methodScope.ERRORS.NO_RECORDS_FOUND);
		 }
	 },
	 
	/**
	 * @method setUpPkgDetailDataTables
	 * @description Initializes the Package Details Datatables.
	 *     that are inside the current row.
	 * @param {Object} packagesDt Parent DataTable Object containing the row to be expanded
	 * @param {Object} nTr Row Object to be expanded
	 * @param {Object} oParams Parameters needed for the AJAX request
	 * @param {Object} jsonObj JSON with the data to be rendered in the datatable
	 * @public
	 */
	setUpPkgDetailDataTables : function(packagesDt, nTr, oParams, jsonObj) {
		var methodScope = this; // Reference to the current scope.
		var sPackageType = 'system';

		// Determine the packageType
		// Check if there is data. If there is no data, let the system package routine take care of it
		if (!jsonObj || $.isEmptyObject(jsonObj)) {
			sPackageType = 'system';
		} else if (jsonObj['packageType'] && typeof jsonObj['packageType'] == "string") {
			sPackageType = jsonObj['packageType'].toLowerCase();			 
		} else {
			sPackageType = 'system';
		}
		
		// Get the opened row of class type: 'details'
		var openedRow = packagesDt.fnOpen( nTr, methodScope.fnFormatDetails(sPackageType), 'details');
		
		// Aliases:
		pkgDetailViewRowsObj = $('table.package-detail-view tr');		
		
		// Logic to decide how to render the datatable inside the row
		switch (sPackageType) {
			case 'system' :
	
				// Set the datatable properties for the inner table inside the opened row
				var oPkgDetailsSummaryTable = $('#system-package-view', openedRow);
				methodScope.populateSystemPackageTable(oPkgDetailsSummaryTable, jsonObj);	

				// Prevent highlighting the whole table.
				pkgDetailViewRowsObj.live('hover', function(){
					$(this).removeClass('row_highlighted');
				});		
	
				break;
	
			case 'application' :
				// Set the datatable properties for the inner table inside the opened row
				var topLevelBundleObj = $('#top-level-bundle', openedRow);
	
				// Set the datatable properties for the inner table inside the opened row
				// Create the Fixed Plan Bundle Datatable
				var fixedPlanBundleDt = $('#fixed-plan-bundle', openedRow).dataTable({		
					"bFilter" : false,
					"bSort" : false,
					"sPaginationType" : "cloudStyle", 
					"bLengthChange" : false,						
					"iDisplayLength" : 5, 
					"bScrollCollapse" : false,
					"aoColumns": methodScope.getDefaultTitlesForDataTable(jsonObj, 'dependentBundles'),
					"sScrollY" : "160px"
				});		
	
				// Create the Top Level Bundle Plan Datatable				
				topLevelBundleObj.dataTable({
					"bFilter" : false,
					"bSort" : false,
					"bPaginate": true,					
					"sPaginationType" : "cloudStyle", 
					"bLengthChange" : false,
					"iDisplayLength" : 5, 
					"bScrollCollapse" : false,
					"sScrollY" : "160px",
					"fnDrawCallback" : function(){
						$('td').bind('mouseenter', function () { $(this).parent().children().each(
								function(){$(this).removeClass('row_highlighted');}); });
					},				
					"aoColumns":  methodScope.getDefaultTitlesForDataTable(jsonObj, 'applicationBundles'),				
				});
				
				// Fill the JSON data in the datatables.
				// methodScope.populateTopLevelBundleTable(topLevelBundleObj, fixedPlanBundleDt, jsonObj);		
	
				// Prevent highlighting the whole table.
				pkgDetailViewRowsObj.live('hover', function(){
					$(this).removeClass('row_highlighted');
				});
	
				// Remove the min-height value set by the datatable.
				$('div.dataTables_wrapper', openedRow).addClass('removeMinHeight');
				$('div.dataTables_scrollBody', openedRow).addClass('removeMinHeight');		
	
				// Hide the 2nd data table by default.
				$('#fixed-plan-bundle_wrapper', openedRow).hide();
	
				// Toggle functionality for the links on top of the inner datatables.
				var packageBundleLinks = $("#package-bundle-links a.links");
				packageBundleLinks.click(function() {
	
					// Remove all the activeLink classes for all links.
					packageBundleLinks.removeClass('activeLink');
	
					// Hide all the tables. JQuery Datatables wraps them in an id ending in _wrapper.
					$("div[id$='-bundle_wrapper']", openedRow).hide();						
	
					// Add the activeLink for the item just clicked (i.e., make it bold, selected)
					$(this).addClass('activeLink');
	
					// Show the corresponding active table by finding the position of the selected link,
					// then associating the corresponding table based on that position.			
					// Find the position of the selected link
					var selectedPos = $(this).prevAll(".links").length;
	
					// Get the datatable for that position
					var dT = $("div[id$='-bundle_wrapper']:eq(" + selectedPos + ")", openedRow);
	
					// Show and redraw the datatable.
					dT.show();
					$("table[id$='-bundle']", dT).dataTable().fnDraw();
	
					return false;
				});
				
				// Fill the JSON data in the datatables.
				methodScope.populateTopLevelBundleTable(topLevelBundleObj, fixedPlanBundleDt, jsonObj);	
				
				break;
				
			case 'configuration' :
				// Set the datatable properties for the inner table inside the opened row
				var oPkgConfigTable = $('#config-package-view', openedRow);
				methodScope.populateConfigPackageTable(oPkgConfigTable, jsonObj);
				
				// Prevent highlighting the whole table.
				pkgDetailViewRowsObj.live('hover', function(){
					$(this).removeClass('row_highlighted');
				});		
	
				break;			
				
		} // switch
	},
	
	/**
	 * @method addPackageDetailsRow
	 * @description Adds the Package Details Row in the Datatable specified inside paramsObj	 
	 * @param {Object|JSON} paramsObj JSON with the parameters needed
	 * @public
	 */
	addPackageDetailsRow : function(paramsObj) {
		var methodScope = this; // Reference to the current scope.
		var aData, packageName = '', packageVersion = '', tempRequestURL = '';		
		var tableId = paramsObj.tableId;
		var packagesDt = paramsObj.oTable;
		var iconsObj = paramsObj.icons;
		var requestURL = paramsObj.url;

		// Validations...
		if (!tableId || !packagesDt || !requestURL) {
			return;
		}
		var DOMTrTable = $('#' +  tableId + ' tbody tr');
		var trIconsExpr = ['#' , tableId , ' tbody td img'].join('');
		
		// Set the icon URLs
		if (iconsObj) {
			methodScope.openIconURL = iconsObj.open || scope.openIconURL;
			methodScope.closedIconURL = iconsObj.closed || scope.closedIconURL;
		}
		
		// For each row in the package details table, 
		// add the open image icon
		DOMTrTable.each(function () {
			var imgObj = document.createElement('img');
			imgObj.src = methodScope.openIconURL;
			$(this).children(":first").prepend(imgObj);
			$(imgObj).css('cursor', 'pointer');
		});

		// Add event listener for opening and closing details.
		$(trIconsExpr).click(function () {
			// Get a reference to the row that was opened in the datatable
			var nTr = this.parentNode.parentNode;

			if (this.src.match(methodScope.closedIconURL)) {
				// Un-select the row
				$(nTr).removeClass('row_selected');
				
				// This row is already open, now close it
				this.src = methodScope.openIconURL;
				packagesDt.fnClose (nTr);					
			} else {
		        // Get the data array for this row 
		        aData = packagesDt.fnGetData(nTr);
		        
		        // Get the package information 
		        packageName = (aData[1] ? $.trim(aData[1]) : "");
		        packageVersion = (aData[2] ? $.trim(aData[2]) : "");
		        tempRequestURL = (requestURL ? $.trim(requestURL) : "");
		        
				// Select the row
				$(nTr).addClass('row_selected');
			
				// Show the closed icon
				this.src = methodScope.closedIconURL;
				
				// Sets up the Package Details Data Table(s)
				oParams = {"packageName" : packageName, "packageVersion" : packageVersion};
				
				// Build the datatables
				methodScope.makeAjaxRequest(packagesDt, nTr, tempRequestURL, oParams);			
			}
			
		} );
		
	}
};
	
/**
 * @method main
 * @description Creates the main package datatable and calls a routine
 *     to initialize the Package Details tables for each of the rows in the
 *     package datatable.
 * @public
 */
$(document).ready(function() {
	// If the table has less then 'numRowsNoScroll' then inactive vertical scrolling
	var numRowsNoScroll = 10;
	var packagesDt; // Will hold the main datatable
	var bodyHeight = $('body').height();
	//var dtHeightY = Math.floor((0.29 * bodyHeight)); // For the DT scrolling
	var dtHeightY = Math.floor((0.60 * bodyHeight)); // For the DT scrolling	
	var tableId = "dt_packages";
	// DOM Id for the main datatable
	var DOMTableId = '#' + tableId;
	// DOM id JQuery expression for all the columns in the table
	var DOMTableTds = DOMTableId + ' > tbody > tr > td';
	
	// Build the main datatable
	packagesDt = $(DOMTableId).dataTable({
		"sDom" : '<"dt_cloud_filter"f<"dt_filter_dropdown"><"dt_import_excel">>'
			+ 't<"dt_cloud_footer"ipl>',
		"sPaginationType" : "cloudStyle",
		"iDisplayLength" : -1,
		"bRetrieve" : true,
		"sScrollY" : (numPackagesInPage > numRowsNoScroll) ? (dtHeightY + 'px') : '' ,
		"aoColumnDefs": [
							{ "bSortable": false, "aTargets": [ 0 ] }
						],
		"aaSorting" : [ [ 2, "desc" ] ]
	});
	
	// Remove the big gap between the footer and the last row if the datatable
	// has less than 'numRowsNoScroll' rows.
	if (numPackagesInPage < numRowsNoScroll) {
		$(DOMTableId + '_wrapper').attr('style', 'min-height: 0 !important');
	}	

	// Highlight the rows on hover
	packagesDt.fnOnRowHover(tableId);
	
	// Force to render the wrapper table lines properly (in FF).
	$(DOMTableTds).addClass("verEdge");
	
	// Add the package details row subtables.
	$.CLOUD.OVERLAYS.PACKAGE_DETAILS.addPackageDetailsRow({ tableId: tableId, 
															oTable : packagesDt,
															icons : {
																'open' : baseURLForImages + '/down_icon.png',
																'closed' :  baseURLForImages + '/up_icon.png'
																},
															 url : packageDetailsURL
															});
	
});

