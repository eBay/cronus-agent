
var groupIds = []

$(function() {
	var data;
	$.ajax({
		type : 'GET',
		url : '/agent/ValidateInternals2',
		data : {},
		crossDomain : true,
		dataType : 'json',
		success : function(json) {
			buildAgentConsole(json);
		},
		error : function(x, error) {
			buildAgentErrorMessage(x, error);
		}
	});

});

function buildAgentConsole(agentData) {

	var groupName;
	var groupIdBase;
	var groupUID;
	var groupIndexUID;
	var dtUID;
	var children;
	var tableData = [];
	var agentDetails = [];

	$
			.each(
					agentData,
					function(index, itemData) {

						groupName = index;
						groupIdBase = groupName.replace(/\s+/g, '-')
								.toLowerCase();
						groupUID = "id-" + groupIdBase;
						groupIndexUID = "index-" + groupIdBase;
						dtUID = "dt-" + groupIdBase;
						children = agentData[index];

						groupIds.push([ groupIdBase, groupName ]);

						$.each(children, function(index, itemData) {

							var displayName = itemData["display-name"];
							var name = itemData["name"];
							var value = itemData["value"];

							agentDetails.push([ displayName, name, value ]);
							agentDetails.push('Display Name: ' + displayName
									+ 'Name: ' + name + ', Value: ' + value);

							if (displayName == undefined
									|| displayName.length == 0) {
								displayName = name;

							}
							// uncomment this line to add tooltip text with
							// original metric field name.
							// displayName = '<span onmouseout="hideTooltip()"
							// onmouseover="showTooltip(event,\'Name: '+ name
							// +'\');return false">' + displayName +'</span>';
							tableData.push([ displayName, value ]);

						});

						$(
								'<div id="index-'
										+ groupIdBase
										+ '" class="cat-header"><div id="index-icon-'
										+ groupIdBase
										+ '" class="icon-open"/><div style="display: inline-block;">'
										+ groupName + '<div></div>').appendTo(
								"#ac-data");
						$('<div id="' + groupUID + '" class="dt_cloud" ></div>')
								.appendTo("#ac-data");
						$(
								'<table id="'
										+ dtUID
										+ '" cellpadding="0" cellspacing="0" border="0" class="dt_cloud"></table>')
								.appendTo("#" + groupUID);

						$("#" + dtUID)
								.dataTable(
										{
											"sDom" : 'R<"dt_cloud_filter"S<"dt_import_excel">>'
													+ 'rt<"dt_cloud_footer"ipl>O',
											"bPaginate" : false,
											"aaData" : tableData,
											"aoColumns" : [ {
												"sTitle" : "Name"
											}, {
												"sTitle" : "Value"
											} ]
										});

						tableData = [];

					});

	// add click binding for toggle panel
	$.each(groupIds, function(index, itemData) {
		$("#" + "index-" + itemData[0]).click(function() {
			location.href = "#index-" + itemData[0];
		});
	});

	// build quick links

	$('<ul id="quick-link-list">').appendTo("#ac-quick-links");
	$.each(groupIds, function(index, itemData) {
		$(
				'<li>&nbsp;-&nbsp;<a id="#ql' + itemData[0] + '" href="#index-'
						+ itemData[0] + '" class="cat-index-link">'
						+ itemData[1] + '</a></li>').appendTo(
				"#quick-link-list");

	});
	$('</ul>').appendTo("#ac-quick-links");

	// bind show/hide events
	$.each(groupIds, function(index, itemData) {
		$("#index-" + itemData[0]).click(
				function() {

					$("#id-" + itemData[0]).slideToggle(
							'slow',
							function() {
								console.log("icon state: "
										+ $("#index-icon-" + itemData[0])
												.hasClass("icon-open"));
								if ($("#index-icon-" + itemData[0]).hasClass(
										"icon-open")) {
									$("#index-icon-" + itemData[0])
											.removeClass("icon-open");
									$("#index-icon-" + itemData[0]).addClass(
											"icon-close");
								} else {
									$("#index-icon-" + itemData[0])
											.removeClass("icon-close");
									$("#index-icon-" + itemData[0]).addClass(
											"icon-open");
								}
							});

				});
	});

}

function buildAgentErrorMessage(x, error) {

	$("<br>").appendTo("#ac-error-message");
	$(
			"<div class=\"error-message\">There was an error while trying to retrieve data for this server instance."
					+ x + " ERROR" + error + "</div>").appendTo(
			"#ac-error-message");
	$("<br>").appendTo("#ac-error-message");
	$("#ac-error-message").show();

}
