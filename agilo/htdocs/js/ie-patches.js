$(document).ready(initIePatches);

function initIePatches() {
	if($.browser.msie) {
		fixSidebar();
		fixFlickering();
	};
};

// Fix hover in the sidebar for IE
function fixSidebar() {
	$(".sidebar li").hover(
		function(){
			$(this).addClass("active");
		},
		function(){
			$(this).removeClass("active");
		}
	);
};

function fixFlickering() {
	// MH: what exactly does the div with the clear both fix?
	// It doesn't seem to fix the flickering - so maybe we should take it out?
	$(".main").append('div style="clear:both"><!-- --></div>');
};