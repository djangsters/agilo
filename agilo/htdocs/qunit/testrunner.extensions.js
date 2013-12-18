(function(){
	var testInBackground = true;

	function toggler() {
		return jQuery('#build_toggle');
	}

	// REFACT: rename to reflect that this reloads the page
	function runAllTests() {
		if (testInBackground) {
			toggler().css('text-decoration', 'none');
			toggler().text("building...");
			window.location.reload();
		};
	}
	function scheduleNextRun() {
		setTimeout(runAllTests, 3000);
	}

	function toggleBackgroundBuild() {
		if ( ! testInBackground) {
			toggler().text("Stop background testing");
		} else {
		    toggler().text("Restart background testing");
		}
		testInBackground = ! testInBackground;
		if (testInBackground)
			runAllTests();
	}
	
	function enableLinkStyle(element) {
		element.css('text-decoration', 'underline');
		element.css('cursor', 'pointer');
	}
	
	jQuery(document).ready(function() {
		toggler().click(toggleBackgroundBuild);
		QUnit.done = function(failures, total) {
			if (0 !== failures) {
				document.title = 'FAIL! ' + document.title + ' FAIL!';
				if (jQuery.browser.msie)
					// sometimes IE scrolls down but we want to see easily if there was an error
					window.scroll(0, 0);
			}
			// dwt: Safari doesn't hide them otherwise (??)
			jQuery('#tests li.pass ol').hide();
			jQuery('#tests li.fail ol').show();
			scheduleNextRun();
		};
		QUnit.noglobals(true);
		enableLinkStyle(toggler());

		window.BASE_URL = window.BASE_URL || ''; // placeholder so the tests don't complain about additional variables
		window.hasDuplicate = window.hasDuplicate; // workaround for jquery  bug #4425 http://dev.jquery.com/ticket/4425
		window.BACKLOG_INFO = window.BACKLOG_INFO || undefined;
	});
})();