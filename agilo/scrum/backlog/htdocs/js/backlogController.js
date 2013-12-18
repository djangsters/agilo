// REFACT: This should be setup globally!
//$.ajaxSetup({cache: false});


$(document).ready(function() {
	if (window.RUNNING_UNIT_TESTS)
		return;
	
	window.controller = new BacklogController();
	// REFACT: move the loader out of the model class and into the controller
	// REFACT: the backlog_info should already be set, so what does this line do?
	controller.model.loader.setInfo(window.BACKLOG_INFO);
	controller.loadBacklog(controller.disableSelectionOfSummaryField);
});

// if you change this class name, remember to adapt agilo.PersistentBacklogFilters as well
function BacklogController() {
	this.model = new Backlog();
	this.model.registerErrorSink(this.showError.bind(this));
	this.model.loader.registerErrorSink(this.showError.bind(this));
	this.contingents = new Contingents(this.model.loader);
	this.contingents.registerErrorSink(this.showError.bind(this));
	this.contingentsView = new ContingentsView(this.contingents);
	this.burndownView = new Burndown(this.model.loader);
	this.burndownView.rewirePlotBurndown();
	this.toggleView = new ToggleView(this.model.loader);
};

$.extend(BacklogController, {
	
	callbacksForDidLoad: [],
	
	registerForCallbackAfterLoad: function(aCallback) {
		this.callbacksForDidLoad.push(aCallback);
	},
	
	callbacksForAfterRendering: [],
	
	registerForCallbackAfterRendering: function(aCallback) {
		this.callbacksForAfterRendering.push(aCallback);
	}
});


// TODO: show message when no team is assigned to the sprint
$.extend(BacklogController.prototype, {
	
	// CONTROLLER .......................................
	
	// REFACT: consider to allow to hand in the fixture as the last parameter or remove this method all together
	loadBacklog: function(optionalCallback) {
		
		this.model.loadContingentsFromServer(function(json){
			this.didLoadBacklog();
			this.contingentsView.addContingentsView();
			this.enableOrDisableBacklog(BACKLOG_INFO.content.access_control);
			this.toggleView.initialize();
			if (optionalCallback)
				optionalCallback();
		}.bind(this));
		
		this.displayBurndownIfInSprintBacklog();
	},
	
	
	didLoadBacklog: function() {
		$.each(BacklogController.callbacksForDidLoad, function(index, callback){
			callback(this);
		}.bind(this));
	},
	
	setMessage: function(aMessage) {
		if (0 === $('#notice').length)
			// somehow h1:first doesn't work in webkit right now?
			$('#backlog h1:eq(0)').after('<span id="notice"></span>');
		
		$('#notice').text(aMessage);
	},
	
	enableOrDisableBacklog: function(accessControl) {
		var shouldDisable = accessControl.is_read_only;
		if (shouldDisable)
			this.setMessage(accessControl.reason);
		
		this.contingentsView.setIsEditable( ! shouldDisable);
	},
	
	displayBurndownIfInSprintBacklog: function() {
		if ( ! this.model.loader.isLoadingSprint())
			return;
		
		this.burndownView.addToDOM();
	},
	
	showError: function(anErrorString) {
		this.setMessage(anErrorString);
	},
	
	// Filtering the backlog ........................................
	
	filterBacklog: function() {
		// TODO: Insert filter input via js, now it is in the HTML
		// TODO: Disable sorting while filtering
		$("#filter").keyup(function () {
			var filter = $(this).val();
			var count = 0;
			$(".backlog dl dt, .backlog dl dd").each(function() {
				if ($(this).text().search(new RegExp(filter, "i")) < 0) {
					$(this).hide();
				} else {
					$(this).show();
					count++;
				}
			});
			$("#filter-count").text(count);
		});
	},
	
	// Adding Tickets ..................................................
	
	addTicketFromJSON: function(someJSON) {
		var ticket = this.model.addTicketFromJSON(someJSON);
		this.view.didAddOrRemoveTicketFromBacklog(this.model, ticket);
		this.positionsDidChange();
		return ticket;
	},
	
	// Callbacks from the view ............................................
	
	// REFACT: move this to notifications too
	positionsDidChange: function() {
		var order = this.view.orderOfTickets();
		this.model.setOrderOfTickets(order);
		this.model.loader.sendPositionsUpdateToServer(order);
	},
	
	disableSelectionOfSummaryField: function() {
		// Firefox bug: https://bugzilla.mozilla.org/show_bug.cgi?id=614187
		// if content is unselecteable, its not highlighted when searching for it (with ctrl-f)
		if ($.browser.firefox)
			return;
		
		$(".backlog .summary").disableSelection();
	},
	
	missingCommaErrorPreventer:''
});

