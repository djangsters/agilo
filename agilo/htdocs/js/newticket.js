/* New ticket - jQuery script to add inline ticket form to the backlog */

// REFACT: Is this code used somewhere?
function newticket() {
	$("#backlog tr.requirement").each(function() {
		// Get requirement id
		var id;
		id = $(this).attr("id");
		
		// Build link
		var src = window.BASE_URL + "/newticket?owner=&src="+id+"&type=story";
		var link = '<a href="'+src+'" class="addticket">+</a>';
		
		$(this).children("#summary").append(link);
	});
}