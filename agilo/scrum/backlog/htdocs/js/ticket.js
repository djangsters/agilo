//
// BE EXTRA CAREFULL WITH MUTABLE STATE HERE!!!!
// This prototype is reused for _ALL_ other tickets - everything set here, will be shared by all tickets
//

/// Never write to .json. fields directly from outside this object 
//  - use setValueForKey() if you don't want to break the notification api
Ticket = function(optionalJSON, optionalBacklog) {
	if (this === window)
		throw new TypeError('Tried to call constructor method without new!');
	
	this.setJSON(optionalJSON);
	this.setBacklog(optionalBacklog);
};

$.extend(Ticket, {
	
	notificationObserverID: 0,
	
	notificationName: function() {
		return 'ticketChanges';
	},
	
	serverDidChangeNotificationName: function() {
		return this.notificationName() + '.server';
	},
	
	registerCallbackAfterEachServerReturn: function(aCallback) {
		$.observer.addObserver(this.serverDidChangeNotificationName(), aCallback);
	},
	
	didChangeTicketFromServer: function(aTicket) {
		$.observer.postNotification(this.serverDidChangeNotificationName(), aTicket);
	}
});

$.extend(Ticket.prototype, {
	
	// Getters / Setters .................................
	
	// REFACT: I would like to get the numbers as numbers from the backend instead of as strings
	setJSON: function(ticketJSON) {
		if (_.isEqual(ticketJSON, this.json))
			return this; // nothing to see, really
		
		// if this is the first set, we don't want to send the notification
		// Otherwise the backlog merging would always relead each ticket as the new json is loaded into it's own backlog
		// A better fix would be to bind notifications to their source object, but since we don't have that yet...
		var shouldSendNotification = !! this.json;
		
		this.json = ticketJSON;
		if (shouldSendNotification)
			this.postNotification();
		return this;
	},
	
	updateJSON: function(ticketJSON) {
		this.setJSON(ticketJSON);
		return this;
	},
	
	copyJSON: function(){
		return JSON.parse(JSON.stringify(this.json));
	},
	
	setBacklog: function(aBacklog) {
		this.backlog = aBacklog;
		return this;
	},
	
	// Querying ticket information .............................
	
	id: function() {
		// REFACT: consider to throw if no id is present to detect errors earlier?
		return this.valueForKey('id');
	},

    isFakeTicket: function() {
        return this.id() < 0;
    },
	
	humanReadableTypeName: function() {
		var loader = new BacklogServerCommunicator(window.BACKLOG_INFO);
		return loader.humanizeTypeName(this.valueForKey('type'));
	},
	
	hasKey: function(aKey) {
		return undefined !== this.json[aKey] && null !== this.json[aKey];
	},
	
	/// @return empty string if aKey is not defined
	valueForKey: function(aKey) {
		if (this.hasKey(aKey))
			return this.json[aKey];
		return '';
	},
	
	setValueForKey: function(aValue, aKey) {
		this.json[aKey] = aValue;
		this.postNotification();
		return aValue;
	},
	
	/// allows numbers and strings to be compared equal, but knows that  0 != ''
	wouldChangeValueForKey: function(aNewValue, aKey) {
		return String(this.valueForKey(aKey)) !== String(aNewValue);
	},
	
	isSameValueForKey: function(aNewValue, aKey) {
		return ! this.wouldChangeValueForKey(aNewValue, aKey);
	},
	
	doesExistOnServer: function() {
		return this.json.id !== undefined
			&& this.json.id !== null
			&& this.json.id > 0;
	},
	
	// REFACT: consider changing this to return ! this.isContainer() 
	// but only after isContainer returns the real dependencies
	isTaskLike: function() {
		// Should also checked this way in python code
		var isTaskLike =  undefined !== this.json.remaining_time;
		
		if (isTaskLike && 0 !== this.childrenIDs().length)
			throw "Contradiction: Ticket #" + this.id() + " is tasklike as it has 'remaining_time' configured but also has children.";
		
		return isTaskLike;
	},
	
	isContainer: function() {
		return -1 !== $.inArray(this.json.type, this.backlog.loader.containerTypes());
	},
	
	canContainTasks: function(){
		// TODO: use the inheritance infrastructure in the backlog for this
		// REFACT: use the linkage information in the backlog-loader for this
		return false;
	},
	
	tracTicketLinkBaseURL: function(){
		return window.BASE_URL + '/ticket/';
	},
	
	tracTicketLink: function(){
		return this.tracTicketLinkBaseURL() + this.json.id;
	},
	
	// Interacting with the environment ............................
	
	/// Override this method if you want to use a different error reporting scheme
	showError: function(someError) {
		if (0 === $('#notice').length)
			$('#backlog h1:eq(0)').after('<span id="notice"></span>');
		
		$('#notice').text(someError);

	},
	
	// Navigating ticket relationships .............................
	
	hasChildren: function() {
		return 0 !== this.children().length;
	},
	
	children: function() {
		return this.backlog.childrenForContainer(this);
	},
	
	childrenWithoutMultiLink: function() {
		return this.backlog.childrenForContainerWithoutMultilink(this);
	},
	
	hasChildrenWithoutMultiLink: function() {
		return 0 !== this.childrenWithoutMultiLink().length;
	},
	
	hasChild: function(aTicket) {
		return aTicket.isChildOf(this);
	},
	
	isChildOf: function(possibleParent) {
		return -1 !== $.inArray(this.json.id, possibleParent.json.outgoing_links);
	},
	
	childrenIDs: function() {
		return this.json.outgoing_links || [];
	},
	
	isParentOf: function(possibleChild) {
		return -1 !== $.inArray(this.json.outgoing_links, possibleChild.json.id);
	},
	
	parentIDs: function() {
		return this.json.incoming_links;
	},
	
	/// Only use this if multilinks are not supported!
	parentWithoutMultilink: function() {
		return this.backlog.containerForChildWithoutMultilink(this);
	},
	
	/// Only use this if multilinks are not supported!
	hasParentWithoutMultilink: function() {
		return null !== this.parentWithoutMultilink();
	},
	
	parents: function() {
		return this.backlog.containersForChild(this);
	},
	
	hasParents: function() {
		return this.parents().length > 0;
	},

    allParents: function() {
        var result = [];
        $.each(this.parents(), function(index, parent){
            result.push(parent);
            var ancestors = parent.allParents();
            $.merge(result, ancestors);
        });
        return _(result).uniq();
    },

	hasMultipleParentLinks: function() {
		return this.parentIDs().length > 1;
	},

	indexOfParent: function(aParent) {
		var index = $.inArray(aParent, this.parents());
		if (-1 === index)
			throw "Ticket #" + aParent.id() + " is not a child of ticket #" + this.id();
		return index;
	},
	
	isTopLevelContainer: function() {
		return this.isContainer()
			&& ! this.hasParents();
	},
	
	hasIncomingLinks: function() {
		return 0 !== this.json.incoming_links.length;
	},
	
	isUnreferenced: function() {
		return ! this.hasIncomingLinks()
			|| ! this.hasParents() // parents may be filtered
			|| this.hasFakeStoryAsOnlyParent();
	},
	
	hasFakeStoryAsOnlyParent: function() {
		return 1 === this.parents().length
			&& -1 === this.parents()[0].id();
	},
	
	isAccessible: function() {
		return this.backlog.isAccessibleType(this.json.type);
	},
	
	// Modifying the ticket .........................................
	
	linkToChild: function(aTicket) {
		// json returned from server already contains the correct incoming_links
		// so we just need to fix up the outgoing link from the parent
		this.json.outgoing_links.push(aTicket.json.id);
		
		if (-1 === this.json.id)
			return; // links from the fake-story are computed dynamically
		
		if (-1 === $.inArray(this.json.id, aTicket.json.incoming_links))
			throw "You tried to link a task to a container without it having the correct backlink. Backlinks are: " + aTicket.json.incoming_links;
	},
	
	
	// Communicating with the server ......................................
	// REFACT: move all the server communication over to the backlogServerCommunicator
	
	isBadJSONTaskStructure: function(someTaskJSON){
		return ! someTaskJSON.id
			|| ! someTaskJSON.status;
			// REFACT: also check summary
	},
	
	// REFACT: rename - this checks very carefully that this is a json error structure
	isBadJSONStructure: function(someJSON){
		return ! someJSON
			|| 'object' !== typeof someJSON
			|| ! someJSON.errors
			|| Array !== someJSON.errors.constructor
			|| ! someJSON.current_data;
	},
	
	/*
		REFACT: error takes text, success takes parsed json - this lead to me using it 
		wrongly in my testsuite, so it should be unified. Since I can't really change 
		the success part, the error part should get pre-parsed json as well. (not sure how to do it yet)
		Problem is: I don't really know that the text is parseable json yet - 
		so it cannot be done before it is actually checked...
	*/
	handleErrorFromServer: function(responseText, errorCode){
		if (0 === responseText.length) {
			this.showError("The server didn't answer at all and is probably down. Still you can try to reload the page and if that doesn't help contact your system administrator.");
			return;
		}
		
		var responseJSON = null;
		try {
			responseJSON = JSON.parse(responseText);
		}
		catch (exception) {
			this.showError("Server sent back unparseable data - try reloading the page!");
			// console.log(responseText);
			return;
		}
		if (this.isBadJSONStructure(responseJSON)) {
			this.showError("Server sent back bad structured data - try reloading the page!");
			return;
		}
		
		var errorMessage = responseJSON.errors.join('\n');
		this.showError(errorMessage);
		
		if (this.isBadJSONTaskStructure(responseJSON.current_data))
			return; // can't update the ticket, as the server didn't give us one...
		
		// Finally, the data looks good...
		this.updateJSON(responseJSON.current_data);
		// REFACT: change this api to allow one to be registered for one callback or to receive a callback after each change
		this.callbackIfCallbackIsPresent(false);
		Ticket.didChangeTicketFromServer(this);
	},
	
	handleSuccessFromServer: function(responseJSON, textStatus){
		this.updateJSON(responseJSON);
		this.callbackIfCallbackIsPresent(true);
		Ticket.didChangeTicketFromServer(this);
	},
	
	callbackIfCallbackIsPresent: function(wasSuccess) {
		// REFACT: migrate to notification api
		if (this._callbackWhenRequestIsDone) {
			this._callbackWhenRequestIsDone(this, wasSuccess);
			this._callbackWhenRequestIsDone = undefined;
		}
	},
	
	// REFACT: rename, this now does more than storing
	sendRequestToServer: function(httpMethod, url) {
		var shouldSubmitDataToServer = 'GET' !== httpMethod;
		var self = this;
		return $.ajax({
			error: function (XMLHttpRequest, textStatus, errorThrown) {
				// typically only one of textStatus or errorThrown will have info
				// this; // the options for this ajax request
				// XMLHttpRequest.responseText contains what was delivered
				self.handleErrorFromServer(XMLHttpRequest.responseText, XMLHttpRequest.status);
			},
			success: function(data, textStatus) {
				self.handleSuccessFromServer(data, textStatus);
			},
			url:         url,
			contentType: 'application/json', // what I'm sending
			dataType:    'json',             // what I'm expecting
			type:        httpMethod,
			processData: false,
			data:        (shouldSubmitDataToServer) ? JSON.stringify(this.json) : undefined
		});
	},
	
	submitToServer: function(optionalCallbackWhenDone){
		this._callbackWhenRequestIsDone = optionalCallbackWhenDone;
		this.json['submit'] = true;
		
		if (this.doesExistOnServer()) {
			var url1 = encodedURLFromComponents('json', 'tickets', this.json.id);
			this.sendRequestToServer('POST', url1);
		} else {
			var url2 = encodedURLFromComponents('json', 'tickets');
			this.sendRequestToServer('PUT', url2);
		}
	},
	
	reloadFromServer: function(optionalCallbackWhenDone) {
		this._callbackWhenRequestIsDone = optionalCallbackWhenDone;
		
		if ( ! this.doesExistOnServer())
			throw "Can't get a ticket that does not yet exist on the server";
		
		var url = encodedURLFromComponents('json', 'tickets', this.json.id);
		this.sendRequestToServer('GET', url);
	},
	
	// Getting notifications on ticket changes ............................
	
	notificationName: function() {
		return Ticket.notificationName() + '-ticketID-' + this.json.id;
	},
	
	notificationNameForObserver: function(anObserver) {
		if ( ! (this.notificationName() in anObserver)) {
			anObserver[this.notificationName()] = Ticket.notificationObserverID;
			Ticket.notificationObserverID++;
		}
		
		return this.notificationName() + '.' + anObserver[this.notificationName()];
	},
	
	/// can actually accept the same arguments as $.observer.addObserver
	addObserver: function(anObserver, aCallbackSpecification) {
		var callback = $.extractCallbackFromArguments(aCallbackSpecification, arguments);
		$.observer.addObserver(this.notificationNameForObserver(anObserver), callback);
	},
	
	removeObserver: function(anObserver) {
		$.observer.removeObserver(this.notificationNameForObserver(anObserver));
	},
	
	postNotification: function(wasRemoval) {
		if ( ! this.json || undefined == this.json.id)
			return; // not yet initialized correctly
		
		$.observer.postNotification(this.notificationName(), this, wasRemoval);
	},
	
	missingCommaErrorPreventer:''
});
