$.fn.dataTableExt.oPagination.cloudStyle = {
	/**
	 * Function: oPagination.extStyle.fnInit <br>
	 * Purpose: Initalise dom elements required for pagination with a list of
	 * the pages <br>
	 * Returns: - <br>
	 * Inputs: object:oSettings - dataTables settings object <br>
	 * node:nPaging - the DIV which contains this pagination control <br>
	 * function:fnCallbackDraw - draw function which must be called on update
	 */
	"fnInit" : function(oSettings, nPaging, fnCallbackDraw) {
		// Override the text labels
		oSettings.oLanguage = {
			"sProcessing" : "Loading data in few seconds...",
			"sLengthMenu" : "Items per page _MENU_",
			"sZeroRecords" : "No matching records found",
			"sEmptyTable" : "No records available",
			"sLoadingRecords" : "Loading...",
			"sInfo" : "Showing _START_ to _END_ of _TOTAL_ records",
			"sInfoEmpty" : "Showing 0 to 0 of 0 records",
			"sInfoFiltered" : "(filtered from _MAX_ total records)",
			"sInfoPostFix" : "",
			"sSearch" : "s",
			"sUrl" : "",
			"oPaginate" : {
				"sFirst" : "",
				"sPrevious" : "",
				"sNext" : "",
				"sLast" : ""
			},
			"fnInfoCallback" : null
		};

		var lengthMenu = [[-1, 50, 100], ["All", 50, 100]];
		if (typeof oSettings.oInit.aLengthMenu !== "undefined") {
			lengthMenu = oSettings.oInit.aLengthMenu;
		}
		oSettings.aLengthMenu = lengthMenu;
		
		var oClasses = oSettings.oClasses;
		/*nTotalPages = $('<div />', {
			text : 'Total Records : ' + parseInt(oSettings.aoData.length, 10),
			'class' : 'paginate_total_records'
		});*/
		
		//By default manual refresh is false
		var manualRefresh = false;
		if ((typeof oSettings.oInit.oCloudPagination !== "undefined")
				&& (typeof oSettings.oInit.oCloudPagination.manualRefresh !== "undefined")) {
			manualRefresh = oSettings.oInit.oCloudPagination.manualRefresh;
		}
		var refreshCssClass = 'paginate_refresh_button';
		if(manualRefresh){
			refreshCssClass += ' active';
		}
		nRefreshBtn = $('<div />', {
			'class' : refreshCssClass
		});
		
		nFirst = $('<span />', {
			text : oSettings.oLanguage.oPaginate.sFirst,
			'class' : oClasses.sPageButton + " " + oClasses.sPageFirst
		});
		nPrevious = $('<span />', {
			text : oSettings.oLanguage.oPaginate.sPrevious,
			'class' : oClasses.sPageButton + " " + oClasses.sPagePrevious
		});
		nList = $('<span />', {
			text : 'List',
			'class' : 'navigationList'
		});
		nNext = $('<span />', {
			text : oSettings.oLanguage.oPaginate.sNext,
			'class' : oClasses.sPageButton + " " + oClasses.sPageNext
		});
		nLast = $('<span />', {
			text : oSettings.oLanguage.oPaginate.sLast,
			'class' : oClasses.sPageButton + " " + oClasses.sPageLast
		});

		/*
		 * nFirst.appendChild(document.createTextNode(oSettings.oLanguage.oPaginate.sFirst));
		 * nPrevious.appendChild(document.createTextNode(oSettings.oLanguage.oPaginate.sPrevious));
		 * nNext.appendChild(document.createTextNode(oSettings.oLanguage.oPaginate.sNext));
		 * nLast.appendChild(document.createTextNode(oSettings.oLanguage.oPaginate.sLast));
		 */
		$(nPaging).append(nRefreshBtn).append(nFirst)
				.append(nPrevious).append(nList).append(nNext).append(nLast);

		$(nFirst).bind('click.DT', function() {
			if (oSettings.oApi._fnPageChange(oSettings, "first")) {
				fnCallbackDraw(oSettings);
			}
		});

		$(nPrevious).bind('click.DT', function() {
			if (oSettings.oApi._fnPageChange(oSettings, "previous")) {
				fnCallbackDraw(oSettings);
			}
		});

		$(nNext).bind('click.DT', function() {
			if (oSettings.oApi._fnPageChange(oSettings, "next")) {
				fnCallbackDraw(oSettings);
			}
		});

		$(nLast).bind('click.DT', function() {
			if (oSettings.oApi._fnPageChange(oSettings, "last")) {
				fnCallbackDraw(oSettings);
			}
		});

		/* Take the brutal approach to cancelling text selection */
		$('span', nPaging).bind('mousedown.DT', function() {
			return false;
		}).bind('selectstart.DT', function() {
			return false;
		});

		/* ID the first elements only */
		/*
		 * if ( oSettings.sTableId !== '' && typeof oSettings.aanFeatures.p ==
		 * "undefined" ) { nPaging.setAttribute( 'id',
		 * oSettings.sTableId+'_paginate' ); nFirst.setAttribute( 'id',
		 * oSettings.sTableId+'_first' ); nPrevious.setAttribute( 'id',
		 * oSettings.sTableId+'_previous' ); nNext.setAttribute( 'id',
		 * oSettings.sTableId+'_next' ); nLast.setAttribute( 'id',
		 * oSettings.sTableId+'_last' ); }
		 */
	},

	/**
	 * Update the list of page buttons shows <br>
	 */
	"fnUpdate" : function(oSettings, fnCallbackDraw) {
		if (!oSettings.aanFeatures.p) {
			return;
		}

		var iPageCount = 5;
		var iPageCountHalf = Math.floor(iPageCount / 2);
		var iPages = Math.ceil((oSettings.fnRecordsDisplay())
				/ oSettings._iDisplayLength);
		var iCurrentPage = Math.ceil(oSettings._iDisplayStart
				/ oSettings._iDisplayLength) + 1;
		var sList = "";
		var iStartButton, iEndButton, i, iLen;
		var oClasses = oSettings.oClasses;

		/* Pages calculation */
		if (iPages < iPageCount) {
			iStartButton = 1;
			iEndButton = iPages;
		} else {
			if (iCurrentPage <= iPageCountHalf) {
				iStartButton = 1;
				iEndButton = iPageCount;
			} else {
				if (iCurrentPage >= (iPages - iPageCountHalf)) {
					iStartButton = iPages - iPageCount + 1;
					iEndButton = iPages;
				} else {
					iStartButton = iCurrentPage - Math.ceil(iPageCount / 2) + 1;
					iEndButton = iStartButton + iPageCount - 1;
				}
			}
		}

		/* Build the dynamic list */
		for (i = iStartButton; i <= iEndButton; i++) {
			if (iCurrentPage != i) {
				sList += '<span class="' + oClasses.sPageButton + '">' + i
						+ '</span>';
			} else {
				sList += '<span class="' + oClasses.sPageButtonActive + '">'
						+ i + '</span>';
			}
		}

		/* Loop over each instance of the pager */
		var an = oSettings.aanFeatures.p;
		var anButtons, anStatic, nPaginateList;
		var fnClick = function(e) {
			/* Use the information in the element to jump to the required page */
			var iTarget = (this.innerHTML * 1) - 1;
			oSettings._iDisplayStart = iTarget * oSettings._iDisplayLength;
			fnCallbackDraw(oSettings);
			e.preventDefault();
		};
		var fnFalse = function() {
			return false;
		};

		for (i = 0, iLen = an.length; i < iLen; i++) {
			if (an[i].childNodes.length === 0) {
				continue;
			}

			/* Build up the dynamic list forst - html and listeners */
			var qjPaginateList = $('span.navigationList', an[i]);
			qjPaginateList.html(sList);
			$('span', qjPaginateList).bind('click.DT', fnClick).bind(
					'mousedown.DT', fnFalse).bind('selectstart.DT', fnFalse);

			/* Update the 'premanent botton's classes */
			anButtons = an[i].getElementsByTagName('span');
			anStatic = [ anButtons[0], anButtons[1],
					anButtons[anButtons.length - 2],
					anButtons[anButtons.length - 1] ];
			$(anStatic).removeClass(
					oClasses.sPageButton + " " + oClasses.sPageButtonActive
							+ " " + oClasses.sPageButtonStaticDisabled);
			if (iCurrentPage == 1) {
				anStatic[0].className += " "
						+ oClasses.sPageButtonStaticDisabled;
				anStatic[1].className += " "
						+ oClasses.sPageButtonStaticDisabled;
			} else {
				anStatic[0].className += " " + oClasses.sPageButton;
				anStatic[1].className += " " + oClasses.sPageButton;
			}

			if (iPages === 0 || iCurrentPage == iPages
					|| oSettings._iDisplayLength == -1) {
				anStatic[2].className += " "
						+ oClasses.sPageButtonStaticDisabled;
				anStatic[3].className += " "
						+ oClasses.sPageButtonStaticDisabled;
			} else {
				anStatic[2].className += " " + oClasses.sPageButton;
				anStatic[3].className += " " + oClasses.sPageButton;
			}
		}
	}
};