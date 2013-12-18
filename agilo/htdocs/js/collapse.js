$(document).ready(initCollapse);

// REFACT: Move this code in the ticket specific folder

function initCollapse() {
	// Collapse ticket history if there
	enable_collapse(jQuery("div.change"), jQuery("div#ticket ~ h2:contains(History)"), 5);
};



function replace_text(elem, text_pair) {
	if ($(elem).html().search(text_pair[0]) != -1) {
		$(elem).html($(elem).html().replace(text_pair[0], text_pair[1]));
	} else {
		$(elem).html($(elem).html().replace(text_pair[1], text_pair[0]));	
	}
}

function expand_collapse(list, source) {
	if ($(list).length > 0) {
		var hide_show = Array('Hide', 'Show');
		$(list).slideToggle();
		replace_text(source, hide_show);
	}
}

/**
 * Enables the collapse expand on the given element list, setting the
 * Collapse event trigger on trigger. Size is the number of items after
 * which the collapse should appear.
 * @param elem: The element type list to collapse and expand
 * @param trigger: The event trigger for collapse and expand
 * @param size: The number of records to show
 */
function enable_collapse(elem, trigger, size) {
	var list = $(elem).filter(':lt(' + ($(elem).length - size) + ')');
	if ($(list).length > 0 && $(trigger).length > 0) {
		$(list).hide();
		// Attach event to the trigger
		$(trigger).append(' &nbsp; <span class="trigger change"><a href="#">Show old (' + $(list).length + ')</a></span>');
		$("span.trigger > a").click(function(evt) {
			// Stop normal link event
			evt.preventDefault();
			expand_collapse(list, evt.target);
		});
	}
}

