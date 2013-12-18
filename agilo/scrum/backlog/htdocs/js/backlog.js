function Backlog() {
	this._tickets = [];
	this._errors = [];
	this.loader = new BacklogServerCommunicator(window.BACKLOG_INFO);
	this._accessibleTypes = []; // no filter set initially
};


$.extend(Backlog.prototype, {
	
	// Loading backlog data .....................................
	
	loadFromServer: function(optionalCallback) {
		this.loader.loadBacklog(function(loader) {
			this.accessibleTypes(this.loader.accessibleTypes());
			this.setJSONForTickets(loader.backlogLoader.json);
			
			if (optionalCallback)
				optionalCallback();
		}.bind(this));
	},
	
	loadContingentsFromServer: function(optionalCallback) {
		
		this.loader.loadContingents(function(loader) {
			this.accessibleTypes(this.loader.accessibleTypes());
			if (optionalCallback)
				optionalCallback();
		}.bind(this));
	},
	
	triggerUpdateFromServer: function() {
		this.loader.startLoadingBacklog(this.mergeUpdatedBacklogJSON.bind(this));
	},
	
	setJSONForTickets: function(ticketsJSON) {
		this._tickets = [];
		$(ticketsJSON).each(function(index, json) {
			// REFACT fs: Why not use 'addTicketFromJSON' here?
			this.tickets().push(this.ticketFromJSON(json));
		}.bind(this));
	},
	
	checkJSONForBoardConstraints: function() {
		var checker = new JSONIntegrityChecker(this.loader.backlogLoader.json);
		return checker.checkAllTicketsHaveAnID()
			.concat(checker.checkTasklikesHaveNoChildren());
	},
	
	ticketFromJSON: function(someJSON) {
		if (this._ticketCreationCallback)
			return this._ticketCreationCallback(someJSON, this);
		else
			return new Ticket(someJSON, this);
	},
	
	setTicketCreationCallback: function(aCallback) {
		if (aCallback)
			this._ticketCreationCallback = aCallback;
	},
	
	reloadTicket: function(aTicketID) {
		this.ticketWithID(aTicketID).reloadJSON();
	},
	
	tickets: function() {
		return this._tickets;
	},
	
	addTicketFromJSON: function(someJSON) {
		var ticket = this.ticketFromJSON(someJSON);
		this._tickets.push(ticket);
		this.linkTicketToParentsIfNecessary(ticket);
		return ticket;
	},
	
	linkTicketToParentsIfNecessary: function(aTicket) {
		if ( ! aTicket.hasParents())
			return;
		
		$.map(aTicket.parents(), function(parent) {
			if (parent.hasChild(aTicket))
				return;
			
			parent.linkToChild(aTicket);
		});
	},
	
	updateTicketFromJSON: function(someJSON) {
		var ticket = this.ticketWithID(someJSON.id);
		ticket.setJSON(someJSON);
		return ticket;
	},
	
	mergeUpdatedBacklogJSON: function(backlogJSON) {
		var otherBacklog = new Backlog();
		otherBacklog.loader.setInfo({ content: this.loader.info() });
		otherBacklog.setJSONForTickets(backlogJSON);
		// or the fake story will be marked as removed...
		otherBacklog.addFakeStoryIfNecessary();
		this.mergeExistingTicketsFromBacklog(otherBacklog);
		var toPostprocess = {
			added: this.addAllMissingTicketsFromBacklog(otherBacklog),
			removed: this.removeAllTicketsNotInBacklog(otherBacklog)
		};
		
		// this.addFakeStoryIfNecessary();
		this.notifyRemovedTickets(toPostprocess.removed);
		this.notifyAddedTickets(toPostprocess.added);
		this.updatePositionsFromBacklog(otherBacklog);
		this.notifyTicketOrderChanged();
		return toPostprocess;
	},
	
	mergeExistingTicketsFromBacklog: function(aBacklog) {
		$.each(aBacklog.tickets(), function(index, ticket) {
			var currentTicket = this.ticketWithID(ticket.id());
			if ( ! currentTicket)
			 	return;
			
			currentTicket.setJSON(ticket.json);
		}.bind(this));
	},
	
	addAllMissingTicketsFromBacklog: function(aBacklog) {
		var addedTickets = [];
		$.each(aBacklog.tickets(), function(index, ticket) {
			var currentTicket = this.ticketWithID(ticket.id());
			if (currentTicket)
				return; // already there
			
			var newTicket = this.addTicketFromJSON(ticket.json);
			addedTickets.push(newTicket);
		}.bind(this));
		return addedTickets;
	},
	
	removeAllTicketsNotInBacklog: function(aBacklog) {
		var indexesToRemove = [];
		var ticketsToRemove = [];
		$.each(this.tickets(), function(index, ticket) {
			var newTicket = aBacklog.ticketWithID(ticket.id());
			if (newTicket)
				return; // still exists
			
			indexesToRemove.push(index);
			ticketsToRemove.push(ticket);
		});
		this.removeTicketsAtIndexes(indexesToRemove);
		return ticketsToRemove;
	},
	
	removeTicketsAtIndexes: function(indexes) {
		$.each(indexes.reverse(), function(unused, index) {
			this.tickets().splice(index, 1);
		}.bind(this));
	},
	
	updatePositionsFromBacklog: function(otherBacklog) {
		$.each(otherBacklog.tickets(), function(index, ticket) {
			this.moveTicketToPosition(ticket.id(), index);
		}.bind(this));
	},
	
	notifyRemovedTickets: function(removedTickets) {
		// REFACT: switch to notification on backlog instead of on ticket
		// that way the BacklogView can get these notifications directly
		$.each(removedTickets, function(index, ticket) {
			$.observer.postNotification(this.ticketAddedOrRemoveNotificationName, this, ticket, true);
			ticket.postNotification(true);
		}.bind(this));
	},
	
	ticketAddedOrRemoveNotificationName: 'BacklogTicketAddedOrRemovedNotification',
	
	addTicketAddingOrRemovingObserver: function(aCallbackSpecification) {
		var callback = $.extractCallbackFromArguments(aCallbackSpecification, arguments);
		$.observer.addObserver(this.ticketAddedOrRemoveNotificationName, callback);
	},
	
	notifyAddedTickets: function(someTickets) {
		$.each(someTickets, function(index, ticket) {
			$.observer.postNotification(this.ticketAddedOrRemoveNotificationName, this, ticket, false);
		}.bind(this));
	},
	
	ticketOrderChangedNotificationName: 'BacklogTicketOrderChangedNotificationName',
	
	addSortingChangedObserver: function(aCallbackSpecification) {
		var callback = $.extractCallbackFromArguments(aCallbackSpecification, arguments);
		$.observer.addObserver(this.ticketOrderChangedNotificationName, callback);
	},
	
	notifyTicketOrderChanged: function() {
		$.observer.postNotification(this.ticketOrderChangedNotificationName, this);
	},
	
	// Validate json ......................................................
	
	validateBacklogIntegrity: function() {
		return this.hasIDOnEveryTicket()
			&& this.hasNoChildsOnAllTasklikes();
	},
	
	hasTicketsWithCriteria: function(aMatcher) {
		return 0 === $.grep(this.tickets(), aMatcher).length;
	},
	
	hasIDOnEveryTicket: function() {
		return this.hasTicketsWithCriteria(function(ticket) {
			return undefined === ticket.json.id;
		});
	},
	
	hasNoChildsOnAllTasklikes: function() {
		return this.hasTicketsWithCriteria(function(ticket) {
			return ticket.isTaskLike() 
				&& 0 !== ticket.children().length;
		});
	},
	
	// Handling ticket positions and ordering ................................
	
	orderOfTickets: function() {
		return $.map(this.tickets(), function(element, index){
			return element.json.id;
		});
	},
	
	/// @param aTicketOrder - array of ints (ticketIDs), needs not have all ids.
	setOrderOfTickets: function(aTicketOrder) {
		$(aTicketOrder).each(function(index, ticketID){
			this.moveTicketToPosition(ticketID, index);
		}.bind(this));
	},
	
	moveTicketToPosition: function(aTicketID, anIndex) {
		var oldIndex = this.indexOfTicketWithID(aTicketID);
		if (-1 === oldIndex)
			return;
		
		if (oldIndex === anIndex)
			return;
		
		var ticket = this._tickets[oldIndex];
		this._tickets.splice(oldIndex, 1);
		this._tickets.splice(anIndex, 0, ticket);
	},
	
	/// performance critical method, called very often during rendering
	indexOfTicketWithID: function(aTicketID) {
		var tickets = this.tickets();
		for (var i = 0; i < tickets.length; i++) {
			if (aTicketID === tickets[i].json.id)
				return i;
		}
		return -1;
	},
	
	sortTicketsAccordingToBoardOrder: function(aTicketArray) {
		return aTicketArray.sort(function(first, second) {
			return this.indexOfTicketWithID(first.json.id) - this.indexOfTicketWithID(second.json.id);
		}.bind(this));
	},
	
	// Handling errors ...................................................
	
	showError: function(someErrorText) {
		// TODO: find a better way to deal with errors
		// Consider to port the message module from the whiteboard
		if (this._errorSink)
			this._errorSink(someErrorText);
		else
			alert(someErrorText);
	},
	
	registerErrorSink: function(someCallback) {
		this._errorSink = someCallback;
	},
	
	// Navigate ticket relationships ....................................
	
	// REFACT: wanted: separate a low level api that just navigates the real model
	// from the filtered and fakestoried api that navigates the model how the view needs it
	
	unreferencedTasks: function() {
		return $.grep(this.tickets(), function(ticket, index) {
			return ticket.isAccessible()
			 	&& ticket.isTaskLike()
			 	&& ticket.isUnreferenced();
		});
	},
	
	hasUnreferencedTasks: function() {
		return this.unreferencedTasks().length > 0;
	},
	
	addFakeStoryIfNecessary: function() {
		if ( ! this.hasUnreferencedTasks())
			return;
			
		if (! this.fakeStory())
			this.addFakeStory();
	},
	
	// REFACT: get rid of the direct references to -1 and instead replace it with some constant that explains it better
	addFakeStory: function() {
		var fakeJSON = {
				id: -1, type: 'story', summary: 'Tasks without Stories', 
				sprint: this.loader.info().sprint_or_release,
				story_priority: 'storyless', 
				outgoing_links: [], incoming_links: []
		};
		// FIXME fs: this parameter is not used?
		this.tickets().push(this.ticketFromJSON(fakeJSON, this));
	},
	
	fakeStory: function() {
		return this.containerWithID(-1);
	},
	
	// REFACT: these don't actually need to be containers
	// i.e. if I don't configure any children to them, they should still be shown.
	topLevelContainers: function() {
		this.addFakeStoryIfNecessary();
		// REFACT: send patch to jquery so that filter gets a second argument "iterated element"
		var containers = $.grep(this.tickets(), function(ticket) {
			// REFACT: this is kind of a hack - even though stories were filtered, we allow the fake story, 
			// so that tasks have a host to be shown in. To really fix this, we need to be able to show tasks
			// as top level types, which probably means that we need to change the way we render (by using the
			// topLevelContainers() as entry points. Also the html would probably need to change as we currently
			// use definition lists where tasks are the explanation of the definition - which are containers.
			return (ticket.isAccessible() || -1 === ticket.json.id)
				&& ticket.isTopLevelContainer();
		});
		return containers;
	},
	
	containerWithID: function(containerID) {
		// TODO: we should check here that this is actually a container
		return this.ticketWithID(containerID);
	},
	
	/// performance critical method - is called millions (!) of times during rendering
	ticketWithID: function(taskID) {
		var tickets = this.tickets();
		var length = tickets.length;
		for (var i = 0; i < length; i++) {
			if (taskID === tickets[i].json.id)
				return tickets[i];
		}
		return null;
	},
	
	hasTicketWithID: function(aTicketID) {
		return !! this.ticketWithID(aTicketID);
	},
	
	hasTicket: function(aTicket) {
		return this.hasTicketWithID(aTicket.id());
	},
	
	childrenForContainer: function(aContainer) {
		if (-1 === aContainer.json.id)
			return this.unreferencedTasks();
		
		var children = $.map(aContainer.childrenIDs(), function(ticketID){
			var ticket = this.ticketWithID(ticketID);
			if (ticket && ticket.isAccessible())
				return ticket;
		}.bind(this));
		return this.sortTicketsAccordingToBoardOrder(children);
	},
	
	childrenForContainerWithoutMultilink: function(aContainer) {
		return $.map(this.childrenForContainer(aContainer), function(aChild) {
			var parent = this.containerForChildWithoutMultilink(aChild);
			if (parent && parent.json.id !== aContainer.json.id)
				return undefined;
			return aChild;
		}.bind(this));
	},
	
	containersForChild: function(aChild) {
		var parents = $.map(aChild.parentIDs(), function(ticketID){
			var ticket = this.ticketWithID(ticketID);
			if (ticket && ticket.isAccessible())
				return ticket;
		}.bind(this));
		
		if (aChild.isTaskLike() 
			&& 0 === parents.length 
			&& this.fakeStory())
			return [this.fakeStory()];

		return parents;
	},
	
	containerForChildWithoutMultilink: function(aChild) {
		var parents = this.containersForChild(aChild);
		if (0 === parents.length)
			return null; // no container found...
		
		// When multilink support is disabled, we display each child as if it belonged to the first parent
		// Using the most important parent (i.e. most at the top) would make a lot of sense
		// but that would mean the returned parent would differn when reordering stories with drag'n'drop
		return parents[0];
	},

    numberOfTicketsWithParentsMatchingFilter: function(optionalTicketFilter) {
        return this.ticketsWithParentsMatchingFilter(optionalTicketFilter, true).length;
    },

    ticketsMatchingFilter: function(optionalTicketFilter, shouldExcludeFakeTickets) {
        var tickets = this.tickets();

        var ticketsToShow = _(tickets).select(function(aTicket) {
            if ( shouldExcludeFakeTickets && aTicket.isFakeTicket())
                return false;
            if (optionalTicketFilter)
                return optionalTicketFilter.shouldShow(aTicket);
            return true;
        });

        return ticketsToShow;
    },

    parentsOfTickets: function(tickets, shouldExcludeFakeTickets) {
        var parents = [];
        $.each(tickets, function(index, ticket) {
            $.merge(parents, ticket.allParents());
        });
        parents = _(parents).reject(function(item){
            return item.isFakeTicket();
        });
        return parents;
    },

    ticketsWithParentsMatchingFilter: function(optionalTicketFilter, shouldExcludeFakeTickets) {
        var ticketsToShow = this.ticketsMatchingFilter(optionalTicketFilter, shouldExcludeFakeTickets);
        var parents = this.parentsOfTickets(ticketsToShow, shouldExcludeFakeTickets);
        return _($.merge(ticketsToShow, parents)).uniq();
    },

	computeTotal: function(anAttributeName, optionalTicketFilter) {
		var total = "";
		
		var tickets = this.ticketsWithParentsMatchingFilter(optionalTicketFilter);
		for (var i = 0; i < tickets.length; i++) {
			var ticket = tickets[i];
			var value = parseFloat(ticket.json[anAttributeName]);
			if (isNaN(value))
				continue;
			total = (total || 0) + value;
		}
		return total;
	},
	
	/// Set this before accessing any tickets. If that ticket is filtered after this
	/// call, relationships from / to it might not work otherwise
	// REFACT: rename set* and access via direct access as this is not accessible from the outside
	accessibleTypes: function(someTypes) {
		if (someTypes) {
			this._accessibleTypes = someTypes;
		}
		return this._accessibleTypes;
	},
	
	isFilteredType: function(aType) {
		// if there is no filter, everything is allowed
		return 0 !== this.accessibleTypes().length
			&& -1 === $.inArray(aType, this.accessibleTypes());
	},
	
	isAccessibleType: function(aType) {
		return ! this.isFilteredType(aType);
	},
	
	// Handling filtering of the backlog
	
	// REFACT: it may be beneficial to move this into the BacklogFilter object
	possibleFilterCriteriaForAttribute: function(aTicketAttributeName) {
		var criteriaWithDuplicates = $.map(this.tickets(), function(ticket){
			if (ticket.hasKey(aTicketAttributeName)
				&& '' !== ticket.valueForKey(aTicketAttributeName))
				return ticket.valueForKey(aTicketAttributeName);
		});
		return uniquedArrayFromArray(criteriaWithDuplicates);
	},
	
	missingLastCommaErrorPreventer:''
});


window.agilo = window.agilo || {};
agilo.CommitmentConfirmation = function(aBacklogLoader) {
	this.loader = aBacklogLoader;
	this.message = new Message();
};
// REFACT: move into the Burndown class?
agilo.DID_CHANGE_BURNDOWN_DATA = 'DID_CHANGE_BURNDOWN_DATA';

$.extend(agilo.CommitmentConfirmation.prototype, {
	addToDOM: function() {
		var confirmCommitmentButtonOptions = {
				id : 'commit-button',
				tooltip : this.tooltip(),
				isPushButton: true,
				isEnabled: this.canConfirmCommitment(),
				clickCallback: function(){
					this.confirmCommitment();
				 }.bind(this)
			 };
		
		agilo.createToolbarButtons([confirmCommitmentButtonOptions], {
			id: 'commit-button-container'
		});
	},
	
	didConfirmCommitmentCallback: function() {
		$.observer.postNotification(agilo.DID_CHANGE_BURNDOWN_DATA);
		this.message.notify("You have confirmed the commitment for this sprint.");
	},
	
	confirmCommitment: function() {
		this.loader.postConfirmCommitment(this.didConfirmCommitmentCallback.bind(this));
	},
	
	canConfirmCommitment: function() {
		return this.loader.canConfirmCommitment();
	},
	
	tooltip: function() {
		if (this.canConfirmCommitment())
			return 'Confirm Commitment';
		return 'You cannot confirm the Commitment (did the sprint start more than 24h ago?)';
	},
	
	missingCommaErrorPreventer:''
});
