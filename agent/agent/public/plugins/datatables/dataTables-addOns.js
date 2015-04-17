/* Client-side sort plugin */
var localSort = {
	"cFeature" : "O",
	"sFeature" : "LocalSort",
	"fnInit" : function(oSettings){
		var sClass = 'sorting';
		//$(colHeaders).unbind('click');
		$('div.dataTables_scrollHead thead th').live('click', function() {
			var colHeaders = $('div.dataTables_scrollHead thead th');
			for(var i=0; i< colHeaders.length; i++){
				var column = colHeaders[i];
				if(($(column).hasClass('sorting_asc')) || ($(column).hasClass('sorting_desc'))){
					continue;
				} else{
					$(column).removeClass("sorting_asc");
					$(column).removeClass("sorting_desc");
				}
			}
			$(colHeaders).addClass("sorting");
			fnSort(this);
		});

		// Default sort
		/*
		 * if (aDefaultSort && (aDefaultSort.length == 2)) { var elemTh =
		 * $(colHeaders)[aDefaultSort[0]]; var sortType = [aDefaultSort[1]];
		 * //fnSort(elemTh, sortType); var sClass = (sortType == '-asc') ?
		 * 'sorting_asc' : 'sorting_desc'; fnSortingClasses(aDefaultSort[0],
		 * sClass); }
		 */

		// Sorts the corresponding column
		function fnSort(elemTh, sortType) {
			var colIndex = $(elemTh).index();
			var aiOrig = [], oSort = $.fn.dataTableExt.oSort, aoColumns = oSettings.aoColumns;

			/* Current values */
			for (i = 0, iLen = oSettings.aiDisplayMaster.length; i < iLen; i++) {
				aiOrig[oSettings.aiDisplayMaster[i]] = i;
			}

			var sortTypeLocal = '-' + ((sortType) ? sortType : getSortType(elemTh));
			var sClass = (sortTypeLocal == '-asc') ? 'sorting_asc' : 'sorting_desc';
			oSettings.aiDisplayMaster.sort(function(a, b) {
				var iTest, iDataSort, sDataType;
				iDataSort = aoColumns[colIndex].iDataSort;
				sDataType = aoColumns[iDataSort].sType;
				if (sDataType == 'date') {
					return oSort[(sDataType ? sDataType : 'date')
							+ sortTypeLocal](fnGetCellData(a, iDataSort),
							fnGetCellData(b, iDataSort));
				} else {
					iTest = oSort[(sDataType ? sDataType : 'string')
							+ sortTypeLocal](fnGetCellData(a, iDataSort),
							fnGetCellData(b, iDataSort));
					if (iTest !== 0) {
						return iTest;
					}
					return oSort['string-asc'](aiOrig[a], aiOrig[b]);
				}
			});
			
			//Update the display array
			oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
			fnDrawLocal(oSettings);
			fnSortingClasses(colIndex, sClass);
			return false;
		}

		// Returns the sort type - toggles the existing type
		function getSortType(elemTh) {
			if ($(elemTh).hasClass("sorting_asc")) {
				return "desc";
			} else {
				return "asc";
			}
		}

		function fnGetCellData(iRow, iCol) {
			var sData;
			var oCol = oSettings.aoColumns[iCol];
			var oData = oSettings.aoData[iRow]._aData;
			if ((sData = oCol.fnGetData(oData)) === undefined) {
				if (oSettings.iDrawError != oSettings.iDraw
						&& oCol.sDefaultContent === null) {
					oSettings.oApi._fnLog(oSettings, 0,
							"Requested unknown parameter '" + oCol.mDataProp
									+ "' from the data source for row " + iRow);
					oSettings.iDrawError = oSettings.iDraw;
				}
				return oCol.sDefaultContent;
			}
			/* When the data source is null, we can use default column data */
			if (sData === null && oCol.sDefaultContent !== null) {
				sData = oCol.sDefaultContent;
			}
			return sData;
		}

		function fnSortingClasses(colIndex, sClass) {
			var oClasses = oSettings.oClasses;
			$(oSettings.aoColumns[colIndex].nTh).removeClass(
					oClasses.sSortable + " " + oClasses.sSortAsc + " "
							+ oClasses.sSortDesc + " "
							+ oSettings.aoColumns[colIndex].sSortingClass);
			$(oSettings.aoColumns[colIndex].nTh).addClass(sClass);
			return false;
		}
		return '';
	}	
};

/* Client-side filter plugin */
var localSearch = {
	"cFeature" : "S",
	"sFeature" : "LocalSearch",
	"fnInit" : function(oSettings) {
		var sSearchStr = '<input type="text" />';

		var nFilter = document.createElement('div');
		nFilter.className = oSettings.oClasses.sFilter;
		nFilter.innerHTML = '<label>' + sSearchStr + '</label>';
		if (oSettings.sTableId !== ''
				&& typeof oSettings.aanFeatures.S == "undefined") {
			nFilter.setAttribute('id', oSettings.sTableId + '_filter');
		}

		var jqFilter = $("input", nFilter);
		jqFilter.val(oSettings.oPreviousSearch.sSearch.replace('"', '&quot;'));
		jqFilter.bind('keyup.DT', function(e) {
			/* Do the filter */
			if (this.value != oSettings.oPreviousSearch.sSearch) {
				$('div#fmenu-tip').addClass('hidden');
				fnFilterLocal(oSettings, this.value);
			}
		});

		jqFilter.bind('keypress.DT', function(e) {
			/* Prevent default */
			if (e.keyCode == 13) {
				return false;
			}
		});

		var clearDiv = document.createElement('div');
		clearDiv.className = 'client-search-clr';
		$(clearDiv).click(function() {
			$('div#fmenu-tip').addClass('hidden');
			fnClearAllLocalFilters(oSettings);
		});
		nFilter.appendChild(clearDiv);

		return nFilter;

	}
};

/* SearchClear plugin */
var clearSearch = {
	"cFeature" : "C",
	"sFeature" : "SearchClear",
	"fnInit" : function(oSettings) {
		var wrapperDiv = document.createElement('div');
		wrapperDiv.className = 'search-clr';
		$(wrapperDiv).click(function() {
			oSettings.oInstance.fnFilter('');
		});
		return wrapperDiv;
	}
};

/* FilterButtons plugin */
var filterButtons = {
	"cFeature" : "B",
	"sFeature" : "FilterButtons",
	"fnInit" : function(oSettings) {
		var wrapperDiv = document.createElement('div');
		wrapperDiv.id = 'view-selector-section';

		var viewSelUl = document.createElement('ul');
		viewSelUl.id = 'view-selectors';

		var leftLi = document.createElement('li');
		leftLi.id = 'left-border';
		leftLi.className = "selected";

		var rightLi = document.createElement('li');
		rightLi.id = 'right-border';

		var allLi = document.createElement('li');
		allLi.innerHTML = "All";
		allLi.className = "inner-item selected";
		$(allLi).click(function() {
			oSettings.oInstance.fnFilter('', 1, false, false, false);
			$('ul#view-selectors li').removeClass('selected');
			$(leftLi).addClass('selected');
			$(this).addClass('selected');
		});

		var prodLi = document.createElement('li');
		prodLi.innerHTML = "Production";
		prodLi.className = "inner-item";
		$(prodLi).click(function() {
			oSettings.oInstance.fnFilter('Production', 1, false, false, false);
			$('ul#view-selectors li').removeClass('selected');
			$(this).addClass('selected');
		});

		var qaLi = document.createElement('li');
		qaLi.innerHTML = "QA";
		$(qaLi).click(function() {
			oSettings.oInstance.fnFilter('QA', 1, false, false, false);
			$('ul#view-selectors li').removeClass('selected');
			$(rightLi).addClass('selected');
			$(this).addClass('selected');
		});

		viewSelUl.appendChild(leftLi);
		viewSelUl.appendChild(allLi);
		viewSelUl.appendChild(prodLi);
		viewSelUl.appendChild(qaLi);
		viewSelUl.appendChild(rightLi);
		wrapperDiv.appendChild(viewSelUl);

		return wrapperDiv;
	}
};

/* Filter Menu plugin */
var filterMenu = {
	"cFeature" : "F",
	"sFeature" : "Filter",
	oSettings : null,
	"fnInit" : function(oSettings) {
		this.oSettings = oSettings;

		var filter = document.createElement('div');
		filter.id = 'fmenu';

		// Head
		var menuHead = document.createElement('div');
		menuHead.id = 'fmenu-head';
		filter.appendChild(menuHead);

		// Tooltip
		var menuTip = document.createElement('div');
		menuTip.id = 'fmenu-tip';
		menuTip.className = 'hidden';

		var tipPointer = document.createElement('div');
		tipPointer.id = 'fmenu-tip-ptr';
		menuTip.appendChild(tipPointer);

		var tipText = document.createElement('span');
		tipText.id = 'fmenu-text';
		tipText.innerHTML = 'View is Filtered.';
		menuTip.appendChild(tipText);

		var tipClear = document.createElement('span');
		tipClear.id = 'fmenu-clear';
		tipClear.innerHTML = 'Show all';
		menuTip.appendChild(tipClear);
		filter.appendChild(menuTip);
		$(tipClear).click(function() {
			fnClearAllLocalFilters(oSettings);
			// Hide the tip
			$('div#fmenu-tip').addClass('hidden');
		});

		// Body
		var menuBody = document.createElement('div');
		menuBody.id = 'fmenu-body';

		if (typeof oSettings.oInit.filterMenu.cols !== "undefined") {
			for ( var idx = 0; idx < oSettings.oInit.filterMenu.cols.length; idx++) {
				var column = document.createElement('div');
				column.id = 'fmenu-col' + idx;
				column.className = 'fmenu-col';
				column.innerHTML = oSettings.oInit.filterMenu.cols[idx].caption;

				var dottedHr = document.createElement('hr');
				dottedHr.className = 'fmenu-hr';
				column.appendChild(dottedHr);

				var menuUl = document.createElement('ul');
				menuUl.id = 'fmenu-list' + idx;
				menuUl.className = 'fmenu-list';
				var colIndex = oSettings.oInit.filterMenu.cols[idx].colIndex;
				for ( var jdx = 0; jdx < oSettings.oInit.filterMenu.cols[idx].items.length; jdx++) {
					var menuLiItem = document.createElement('li');
					menuLiItem.id = 'fmenu-item' + idx + '' + jdx;
					menuLiItem.className = "fmenu-item link";

					var item = oSettings.oInit.filterMenu.cols[idx].items[jdx];
					var iconSpan = document.createElement('span');
					iconSpan.className = 'item-icon '
							+ item.trim().toLowerCase();
					menuLiItem.appendChild(iconSpan);

					var textSpan = document.createElement('span');
					textSpan.className = 'item-text';
					textSpan.innerHTML = item;
					menuLiItem.appendChild(textSpan);
					menuUl.appendChild(menuLiItem);

					$(menuLiItem).click(function() {
						filterMenu.fMenuFilter(this, colIndex);
					});
				}
				column.appendChild(menuUl);
				menuBody.appendChild(column);
			}
		}
		filter.appendChild(menuBody);

		// Set up the listener to display the menu on click
		$(menuHead).click(function() {
			filterMenu.fMenuClick(this);
		});
		// Hide the menu when the user hovers outside the drop down menu
		$(menuBody).hover(function() {
		}, function() {
			filterMenu.fMenuClose();
		});

		return filter;
	},
	fMenuClick : function(element) {
		if ($('div#fmenu-head').hasClass('pressed')) {
			filterMenu.fMenuClose();
		} else {
			filterMenu.fMenuOpen();
		}
		return false;
	},
	fMenuOpen : function() {
		$('div#fmenu-head').addClass('pressed');
		$('div#fmenu-body').addClass('subhover');
		return false;
	},
	fMenuClose : function() {
		$('div#fmenu-head').removeClass('pressed');
		$('div#fmenu-body').removeClass('subhover');
		return false;
	},
	fMenuFilter : function(element, colIndex) {
		fnClearAllLocalFilters(this.oSettings);
		
		var filterStr = $(element).text().trim();
		// Handle string 'all' - need not display tooltip
		if (filterStr.toLowerCase() == 'all') {
			$('div#fmenu-tip').addClass('hidden');
			return false;
		} else {
			$('div#fmenu-tip').removeClass('hidden');
		}
		if (filterStr.toLowerCase() == 'running') {
			filterStr = '(prep)|(stage)';
			fnFilterLocal(this.oSettings, filterStr, true, false);
		} else {
			fnFilterLocal(this.oSettings, filterStr, false, false);
		}
		filterMenu.fMenuClose();
		return false;
	}
};

/**
 * Additional plugin api
 */
/* Highlight a row on click */
$.fn.dataTableExt.oApi.fnOnRowClick = function(oSettings) {
	/*
	 * Usage: $('#example').dataTable().fnOnRowClick();
	 */
	var tBodyDiv = oSettings.sTableId + " tbody";
	$("#" + tBodyDiv).click(function(event) {
		$(oSettings.aoData).each(function() {
			$(this.nTr).removeClass('row_selected');
		});

		// If the onhover element is 'TR'
		if (event.target.parentNode.tagName == 'TR') {
			$(event.target.parentNode).addClass('row_selected');
		} else {
			$(event.target).parents("tr:first").addClass('row_selected');
		}
	});
};

/* Highlight a row on hover */
$.fn.dataTableExt.oApi.fnOnRowHover = function(oSettings) {
	/*
	 * Usage: $('#example').dataTable().fnOnRowClick();
	 */
	var trDiv = oSettings.sTableId + " tr";
	$("#" + trDiv).live("mouseover", function(event) {
		// If the onhover element is 'TR'
		if (event.target.parentNode.tagName == 'TR') {
			$(event.target.parentNode).addClass('row_highlighted');
		} else {
			$(event.target).parents("tr:first").addClass('row_highlighted');
		}
	});

	$("#" + trDiv).live("mouseout", function(event) {
		$(oSettings.aoData).each(function() {
			$(this.nTr).removeClass('row_highlighted');
		});
	});
};
$.fn.dataTableExt.oApi.fnOnRowHoverExclusive = function(oSettings) {
	/*
	 * Usage: $('#example').dataTable().fnOnRowClick();
	 */
	var trDiv = oSettings.sTableId + " tr";

	$("#" + trDiv).hover(function(event) {
		$(oSettings.aoData).each(function() {
			$(this.nTr).removeClass('row_selected');
			$(this.nTr).removeClass('row_highlighted');
		});

		// If the onhover element is 'TR'
		if (event.target.parentNode.tagName == 'TR') {
			$(event.target.parentNode).addClass('row_highlighted');
		} else {
			$(event.target).parents("tr:first").addClass('row_highlighted');
		}
	});
};

/**
 * oExt functions
 * 
 * @param dtable
 * @param column
 * @returns
 */
var dtClientSideSorter = function(dtable, aDefaultSort) {
	// var dtable = this;
	var oSettings = dtable.fnSettings();
	var sClass = 'sorting';

	var colHeaders = $("div.dataTables_scrollHead thead th");
	$(colHeaders).removeClass("sorting_disabled");
	$(colHeaders).addClass("sorting");
	$(colHeaders).unbind('click');
	$(colHeaders).click(function() {
		fnSort(this);
	});

	// Default sort
	/*
	 * if (aDefaultSort && (aDefaultSort.length == 2)) { var elemTh =
	 * $(colHeaders)[aDefaultSort[0]]; var sortType = [aDefaultSort[1]];
	 * //fnSort(elemTh, sortType); var sClass = (sortType == '-asc') ?
	 * 'sorting_asc' : 'sorting_desc'; fnSortingClasses(aDefaultSort[0],
	 * sClass); }
	 */

	// Sorts the corresponding column
	function fnSort(elemTh, sortType) {
		var colIndex = $(elemTh).index();
		var aiOrig = [], oSort = $.fn.dataTableExt.oSort, aoColumns = oSettings.aoColumns;

		/* Current values */
		for (i = 0, iLen = oSettings.aiDisplayMaster.length; i < iLen; i++) {
			aiOrig[oSettings.aiDisplayMaster[i]] = i;
		}

		var sortTypeLocal = '-' + ((sortType) ? sortType : getSortType(elemTh));
		var sClass = (sortTypeLocal == '-asc') ? 'sorting_asc' : 'sorting_desc';
		oSettings.aiDisplayMaster.sort(function(a, b) {
			var iTest, iDataSort, sDataType;
			iDataSort = aoColumns[colIndex].iDataSort;
			sDataType = aoColumns[iDataSort].sType;
			if (sDataType == 'date') {
				return oSort[(sDataType ? sDataType : 'date')
						+ sortTypeLocal](fnGetCellData(a, iDataSort),
						fnGetCellData(b, iDataSort));
			} else {
				iTest = oSort[(sDataType ? sDataType : 'string')
						+ sortTypeLocal](fnGetCellData(a, iDataSort),
						fnGetCellData(b, iDataSort));
				if (iTest !== 0) {
					return iTest;
				}
				return oSort['string-asc'](aiOrig[a], aiOrig[b]);
			}
		});

		oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
		oSettings.bAjaxDataGet = false;
		dtable.fnDraw(false);
		fnSortingClasses(colIndex, sClass);
		oSettings.bAjaxDataGet = true;
		return false;
	}

	// Returns the sort type - toggles the existing type
	function getSortType(elemTh) {
		if ($(elemTh).hasClass("sorting_asc")) {
			return "desc";
		} else {
			return "asc";
		}
	}

	function fnGetCellData(iRow, iCol) {
		var sData;
		var oCol = oSettings.aoColumns[iCol];
		var oData = oSettings.aoData[iRow]._aData;
		if ((sData = oCol.fnGetData(oData)) === undefined) {
			if (oSettings.iDrawError != oSettings.iDraw
					&& oCol.sDefaultContent === null) {
				oSettings.oApi._fnLog(oSettings, 0,
						"Requested unknown parameter '" + oCol.mDataProp
								+ "' from the data source for row " + iRow);
				oSettings.iDrawError = oSettings.iDraw;
			}
			return oCol.sDefaultContent;
		}
		/* When the data source is null, we can use default column data */
		if (sData === null && oCol.sDefaultContent !== null) {
			sData = oCol.sDefaultContent;
		}
		return sData;
	}

	function fnSortingClasses(colIndex, sClass) {
		var oClasses = oSettings.oClasses;
		$(oSettings.aoColumns[colIndex].nTh).removeClass(
				oClasses.sSortable + " " + oClasses.sSortAsc + " "
						+ oClasses.sSortDesc + " "
						+ oSettings.aoColumns[colIndex].sSortingClass);
		$(oSettings.aoColumns[colIndex].nTh).addClass(sClass);
		return false;
	}
	
	return false;
};
(function($) {
	$.fn.dtClientSideSorter = dtClientSideSorter;
})(jQuery);
	
/* Clears all filtering on client side */
var fnClearAllLocalFilters = function(oSettings) {
	// Clear all the table filter
	for (iCol = 0; iCol < oSettings.aoPreSearchCols.length; iCol++) {
		oSettings.aoPreSearchCols[iCol].sSearch = '';
	}
	oSettings.oPreviousSearch.sSearch = '';
	$('input', 'div.dataTables_filter').val('');

	oSettings.aiDisplay.splice(0, oSettings.aiDisplay.length);
	oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
	oSettings.oInstance.fnDrawLocal();
};

/* Tweak to do enable filtering on client side */
var fnFilterLocal = function (oSettings, sInput, bRegex, bSmart) {
	var i;
	var rpSearch = oSettings.oApi._fnFilterCreateSearch(sInput, bRegex, bSmart);

	/* Check if we are forcing or not - optional parameter */
	if (typeof iForce == 'undefined' || iForce === null) {
		iForce = 0;
	}

	/*
	 * If the input is blank - we want the full data set
	 */
	if (sInput.length <= 0) {
		oSettings.aiDisplay.splice(0, oSettings.aiDisplay.length);
		oSettings.aiDisplay = oSettings.aiDisplayMaster.slice();
	} else {
		oSettings.aiDisplay.splice(0, oSettings.aiDisplay.length);

		/* Force a rebuild of the search array */
		oSettings.oApi._fnBuildSearchArray(oSettings, 1);

		/*
		 * Search through all records to populate the search array The the
		 * oSettings.aiDisplayMaster and asDataSearch arrays have 1 to 1 mapping
		 */
		for (i = 0; i < oSettings.aiDisplayMaster.length; i++) {
			if (rpSearch.test(oSettings.asDataSearch[i])) {
				oSettings.aiDisplay.push(oSettings.aiDisplayMaster[i]);
			}
		}
	}
	oSettings.oInstance.fnDrawLocal();
};

/* Tweak to redraw the rendered records on local */
var fnDrawLocal = function(oSettings) {
	var i, iLen;
	var anRows = [];
	var iRowCount = 0;
	var bRowError = false;
	var iStrips = oSettings.asStripClasses.length;

	if (oSettings.aiDisplay.length !== 0) {
		for ( var j = 0; j < oSettings.aiDisplay.length; j++) {
			var aoData = oSettings.aoData[oSettings.aiDisplay[j]];
			if (aoData.nTr === null) {
				oSettings.oApi._fnCreateTr(oSettings, oSettings.aiDisplay[j]);
			}

			var nRow = aoData.nTr;

			/* Remove the old stripping classes and then add the new one */
			if (iStrips !== 0) {
				var sStrip = oSettings.asStripClasses[iRowCount % iStrips];
				if (aoData._sRowStripe != sStrip) {
					$(nRow).removeClass(aoData._sRowStripe).addClass(sStrip);
					aoData._sRowStripe = sStrip;
				}
			}

			/* Custom row callback function - might want to manipule the row */
			if (typeof oSettings.fnRowCallback == "function") {
				nRow = oSettings.fnRowCallback.call(oSettings.oInstance, nRow,
						oSettings.aoData[oSettings.aiDisplay[j]]._aData,
						iRowCount, j);
				if (!nRow && !bRowError) {
					oSettings.oApi._fnLog(oSettings, 0,
							"A node was not returned by fnRowCallback");
					bRowError = true;
				}
			}

			anRows.push(nRow);
			iRowCount++;
		}
	} else {
		/* Table is empty - create a row with an empty message in it */
		anRows[0] = document.createElement('tr');

		if (typeof oSettings.asStripClasses[0] != 'undefined') {
			anRows[0].className = oSettings.asStripClasses[0];
		}

		var sZero = oSettings.oLanguage.sZeroRecords.replace('_MAX_', oSettings
				.fnFormatNumber(oSettings.fnRecordsTotal()));
		if (oSettings.iDraw == 1 && oSettings.sAjaxSource !== null
				&& !oSettings.oFeatures.bServerSide) {
			sZero = oSettings.oLanguage.sLoadingRecords;
		} else if (typeof oSettings.oLanguage.sEmptyTable != 'undefined'
				&& oSettings.fnRecordsTotal() === 0) {
			sZero = oSettings.oLanguage.sEmptyTable;
		}

		var nTd = document.createElement('td');
		nTd.setAttribute('valign', "top");
		nTd.colSpan = oSettings.oApi._fnVisbleColumns(oSettings);
		nTd.className = oSettings.oClasses.sRowEmpty;
		nTd.innerHTML = sZero;

		anRows[iRowCount].appendChild(nTd);
	}

	/*
	 * Need to remove any old row from the display - note we can't just empty
	 * the tbody using $().html('') since this will unbind the jQuery event
	 * handlers (even although the node still exists!) - equally we can't use
	 * innerHTML, since IE throws an exception.
	 */
	var nAddFrag = document.createDocumentFragment(), nRemoveFrag = document
			.createDocumentFragment(), nBodyPar, nTrs;

	if (oSettings.nTBody) {
		nBodyPar = oSettings.nTBody.parentNode;
		nRemoveFrag.appendChild(oSettings.nTBody);

		/*
		 * When doing infinite scrolling, only remove child rows when sorting,
		 * filtering or start up. When not infinite scroll, always do it.
		 */
		if (!oSettings.oScroll.bInfinite || !oSettings._bInitComplete
				|| oSettings.bSorted || oSettings.bFiltered) {
			nTrs = oSettings.nTBody.childNodes;
			for (i = nTrs.length - 1; i >= 0; i--) {
				nTrs[i].parentNode.removeChild(nTrs[i]);
			}
		}

		/* Put the draw table into the dom */
		for (i = 0, iLen = anRows.length; i < iLen; i++) {
			nAddFrag.appendChild(anRows[i]);
		}

		oSettings.nTBody.appendChild(nAddFrag);
		if (nBodyPar !== null) {
			nBodyPar.appendChild(oSettings.nTBody);
		}
	}

	/* Call all required callback functions for the end of a draw */
	/*
	 * for (i = oSettings.aoDrawCallback.length - 1; i >= 0; i--) {
	 * oSettings.aoDrawCallback[i].fn.call(oSettings.oInstance, oSettings); }
	 */
};

/**
 * oExt aoFeatures - Plugins
 */
$.fn.dataTableExt.aoFeatures.push(localSort);
$.fn.dataTableExt.aoFeatures.push(localSearch);
$.fn.dataTableExt.aoFeatures.push(clearSearch);
$.fn.dataTableExt.aoFeatures.push(filterButtons);
$.fn.dataTableExt.aoFeatures.push(filterMenu);

/**
 * oExt oApi - Plugins 
 */
$.fn.dataTableExt.oApi.fnLocalSort = dtClientSideSorter;
$.fn.dataTableExt.oApi.fnClearAllLocalFilters = fnClearAllLocalFilters;
$.fn.dataTableExt.oApi.fnFilterLocal = fnFilterLocal;
$.fn.dataTableExt.oApi.fnDrawLocal = fnDrawLocal;