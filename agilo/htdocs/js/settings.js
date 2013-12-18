/*jsl:ignoreall*/
$(document).ready(initSettings);

function initSettings() {
	addPreferenceLinkBehaviour();
	allowBacklogSubmitWithEnterKey();
};

function settings(base_url, id) {
  id = id+"panel";
	var diag = dialog(id);
	var div = $(diag).children('#' + id);
	var lock = $(".lock");
  
  $(div).load(base_url + " #content", function(){ 
    links(base_url, div);
  });
	$(diag).fadeIn();
	$(lock).fadeIn();
}

function set_message(text_message, status) {
	var tab_content = $("div#tabcontent");
	var message = tab_content.find("#message_status");
	if (message.length == 0) {
		message = $('<div id="message_status"></div>');
		tab_content.prepend(message);
	}
	if (status == 'success') {
		message.attr('class', 'system-message notice');
	} else {
		message.attr('class', 'system-message warning');
	}
	message.html("<strong>Result:</strong> " + text_message).show().fadeOut(2000);
}

function links(base_url, div) {
	// Global variable for panel_url
	var panel_url = base_url;
	
	// Make the link load in the correct div
	$(div).find("a").each(function() {
		$(this).click(function(evt) {
			evt.preventDefault();
			var url = $(this).attr("href");
			panel_url = evt.target.href;
			$(div).load(url + " #content", function() { links(panel_url, div); });
		});
	});
	
	// Attaching submit form event
	$(div).find("div#tabcontent > form#userprefs").submit(function() {
		$(this).ajaxSubmit({
			url: panel_url, 
			success: function(responseText, statusText) {
				set_message("Preferences saved!", status=statusText);
			}
		});
		// avoid posting and redirection
		return false;
	});	
}

function dialog(id) {
	var diag = $('#dialog');
	var lock = $(".lock");
  var div = $("#" + id);
	
	if (diag.length == 0) {
		// Build the dialog
		diag = $('<div id="dialog"></div>');
		$(diag).hide();
		$(diag).append('<div class="buttons"><input type="button" id="cancel" value="Close settings" /></div>');
		lock = $('<div class="lock"></div>');
		$(lock).hide();
		$("body").append(lock);
		$("body").append(diag);
		// Hide button
		$("#cancel").click(function() {
			$(lock).fadeOut();
			$(diag).fadeOut();
		});
	}
	if (div.length == 0) {
    div = $('<div id="' + id + '"></div>');
    // div = $('<div id="prefpanel"></div>');
		$(diag).append(div);
	}
	return diag;
}

function addPreferenceLinkBehaviour() {
	// Utility for the Preferences pop up
	$("ul.metanav a:contains(Preferences)").click(function(evt) {
		evt.preventDefault();
		settings(evt.target.href, "prefs");
	});
};

function allowBacklogSubmitWithEnterKey() {
	// Allow the backlog to be submitted by hitting the enter key
	$("#backlog_form").keydown(function(event){
		switch (event.keyCode) {
			case 13:
				$(this).submit("save");
			break;
		}
	});
};