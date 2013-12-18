$(document).ready(function(){
	loadSideBarContent();
	
	// Append show hide thing for sidebar
	addSidebarHandle(function () {
		if ($.fn.disableSelection)
			$(".sidebar").disableSelection();
	});
	activateSidebarHandle();
	setSidebarState(readCookie("agilo-sidebar"));
});

function loadSideBarContent() {
	var url = window.BASE_URL;
	// With Firefox 3.0.7 we need to strip the url if it ends with a '/' because
	// Firefox will try to load http://report/ if we call load('//...') which
	// triggers the 'Same Origin' protection.
	// Opera+Safari work fine without this fix though...
	var lastCharacterInURL = url.charAt(url.length - 1);
	if (lastCharacterInURL === '/') {
		url = url.substr(0, url.length-1);
	}
    // reports
	$(".tree.tickets").load(url + "/report .reports h3 a[title='View report']:lt(10)", function() {
		$(".tree.tickets a").wrap("<li></li>").find('em').remove();
        // fallback for the Trac 0.12.x case
        if ($(".tree.tickets a").length == 0) {
            $(".tree.tickets").load(url + "/report .listing.reports td.title a:lt(10)", function() {
                $(".tree.tickets a").wrap("<li></li>");
            });
        }
	});
	// last wiki changes
	$(".tree.wiki").load(url + "/wiki/RecentChanges .wikipage.searchable div:not(.trac-modifiedby) a:lt(10)", function() {
		$(".tree.wiki a").each(function() {
			if ($(this).text() == 'diff')
				$(this).remove();
			else
				$(this).wrap("<li></li>");
		});
	});
};

function addSidebarHandle(callback) {
	$("body").append('<div class="sidebarHandle"></div>');
	sidebarPosition();
	callback();
};

function sidebarPosition() {
	var left = $(".sidebar").width();
	$(".sidebarHandle").css("left", left+"px");
}

function activateSidebarHandle() {
	$(".sidebarHandle").click(function(){
		toggleSidebar();
	});
};

function toggleSidebar(state) {
	var anchor = $(".main").css("left").slice(0,-2);
	
	/*jsl:ignore*/
	if (anchor == 0) {
	/*jsl:end*/
		openSidebar();
	} else {
		closeSidebar();
	};
};

function openSidebar() {
	var width = $(".sidebar").width();
	// open the panel
	$(".sidebar").animate({marginLeft: "0px"}, {queue: false});
	$(".main, .sidebarHandle").css("width", "").animate({left: width+"px"}, {queue: false});
    $(".main, .sidebarHandle").addClass('opened');
	$(".sidebarHandle").css("cursor", "w-resize");
	// set the cookie to open
	createCookie("agilo-sidebar","open",365);
};

function closeSidebar() {
	var width = $(".sidebar").width();
	// close the panel
	$(".sidebar").animate({marginLeft: "-"+width+"px"}, {queue: false});
	$(".main, .sidebarHandle").css("width", "").animate({left: "0"}, {queue: false});
    $(".main, .sidebarHandle").removeClass('opened');
	$(".sidebarHandle").css("cursor", "e-resize");
	// set the cookie to closed
	createCookie("agilo-sidebar","closed",365);
};

function setSidebarState(state) {
	var width = $(".sidebar").width();
	
	if (state == 'closed') {
		$(".sidebar").css({marginLeft: "-"+width+"px"});
		$(".main, .sidebarHandle").css({left: "0"});
        $(".main, .sidebarHandle").removeClass('opened');
	};
	if (state == 'open') {
		$(".sidebar").css({marginLeft: "0px"});
		$(".main, .sidebarHandle").css({left: width+"px"});
        $(".main, .sidebarHandle").addClass('opened');
	};
};


(function(){
	var isBacklog = (undefined !== window.BacklogController);
	if (isBacklog) {
		BacklogController.registerForCallbackAfterLoad(function() {
			$.cookie('agilo-sprint-backlog-view', 'backlog', {path: window.BASE_URL, expires: 30});
		});
	}
	
	$(document).ready(function(){
		var goToSelectedSprintBacklogView = function(e) {
			if ('whiteboard' !== $.cookie('agilo-sprint-backlog-view')) {
				return true;
			}
			e.preventDefault();
			var form = e.target;
			if (undefined !== e.target.form)
				// with MSIE 7+8, e.target is not the actual form but the select
				// field (if this method is triggered by onChange on the select
				// field) so let's get the form.
				form = e.target.form;
			var sprintName = $(form.bscope).val();
			var url = encodedURLFromComponents('agilo-pro', 'sprints', sprintName, 'whiteboard');
			window.location.href = url;
			return false;
		};
		$('.sidebar .backlogs form[name="sprint_view"]').submit(goToSelectedSprintBacklogView);
	});
})();

