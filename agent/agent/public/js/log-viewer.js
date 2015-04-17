// change this to point to the log file key. Default is "Log Files".
var logFilesKey = "Log Files";

$(function() {

	var data;

	$.ajax({
		url : '/agent/logs2',
		data : {},
		dataType : 'json',
		success : function(json) {
			buildAgentLogConsole(json);
		},
		error : function(x, error) {
			buildLogErrorMessage(x, error);
		}
	});

});

function buildAgentLogConsole(agentData) {

	var tableData = [];

	$.each(agentData[logFilesKey], function(index, itemData) {

		var link = itemData["file-url"];
		var name = itemData["file-name"];

		tableData.push([ '<img class="icon-log-file"/>&nbsp;<a href="' + link
				+ '" >' + name + '</a>' ]);

	});

	$("<div class=\"cat-header\">Log Files</div>").appendTo("#ac-log-view");
	$(
			'<table cellpadding="0" cellspacing="0" border="0" class="dt_cloud" id="log-dt"></table>')
			.appendTo("#ac-log-view");
	$("#log-dt").dataTable(
			{
				"sDom" : 'R<"dt_cloud_filter"S<"dt_import_excel">>'
						+ 'rt<"dt_cloud_footer"ipl>O',
				"bPaginate" : false,
				"aaData" : tableData,
				"aoColumns" : [ {
					"sTitle" : "File Name"
				}, ]
			});

}

function buildLogErrorMessage(x, error) {

	$("<br>").appendTo("#ac-log-error-message");
	$(
			"<div class=\"error-message\">There was an error while trying to retrieve data for this server instance."
					+ x + " ERROR" + error + "</div>").appendTo(
			"#ac-log-error-message");
	$("<br>").appendTo("#ac-log-error-message");
	$("#ac-log-error-message").show();

}