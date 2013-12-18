// REFACT: the loader should probably get a sense of what is expected 
// of him to load and only load that
// (this needs to be included in lots of places in agilo though, so
// thats why it's still in here...). Consider to create a function 
// that includes everything needed for the backlog in the request.
function BacklogServerCommunicator(aBacklogInfo) {
	this.setInfo(aBacklogInfo);
	this.configureLoaders();
}

$.extend(BacklogServerCommunicator.prototype, {
	
	setInfo: function(aBacklogInfo) {
		this._json = aBacklogInfo;
	},
	
	info: function() {
		if (undefined === this._json)
			return undefined;
		return this._json.content;
	},
	
	permissions: function() {
		if (undefined === this._json)
			return [];
		return this._json.permissions;
	},
	
	isLoadingSprint: function() {
		return 'sprint' === this.info().type;
	},
	
	assertInfoIsSet: function() {
		if ( ! this.info())
			throw "You need to provide a backlog info to the loader for it to work. Usually provided via window.BACKLOG_INFO either in the constructor or via setInfo().";
	},
	
	registerErrorSink: function(aShowErrorCallback) {
		this._errorSink = aShowErrorCallback;
	},
	
	showError: function(anErrorString) {
		if ($.isFunction(this._errorSink))
			this._errorSink(anErrorString);
		else
			alert(anErrorString);
	},
	
	url: function() {
		return new URLGenerator(this.info());
	},
	
	// Generic helpers .......................................................
	
	// REFACT: Also consider extracting a communication object / or make the ticket object use this code here
	get: function(url, optionalDataSinkCallback) {
		this.sendRequestToServer('GET', url, optionalDataSinkCallback);
	},
	
	post: function(url, json, optionalDataSinkCallback) {
		this.sendRequestToServer('POST', url, optionalDataSinkCallback, json);
	},
	
	put: function(url, json, optionalDataSinkCallback) {
		this.sendRequestToServer('PUT', url, optionalDataSinkCallback, json);
	},
	
	// REFACT: the callback should really not be optional - we always return the updated values and they should always be used
	sendRequestToServer: function(method, url, optionalDataSinkCallback,  jsonPayload) {
		
		function dataSink(receivedData) {
			if (optionalDataSinkCallback)
				optionalDataSinkCallback(receivedData);
		}
		
		var shouldSendData = -1 !== $.inArray(method, ['POST', 'PUT']);
		return $.ajax({
			error:       function (XMLHttpRequest, textStatus, errorThrown) {
				// typically only one of textStatus or errorThrown will have info
				// this; // the options for this ajax request
				// XMLHttpRequest.responseText contains what was delivered
				// console.log('response:', XMLHttpRequest.responseText, 'textStatus:', textStatus,
				//  	'errorThrown:', errorThrown, 'status:', XMLHttpRequest.status);
				this.handleErrorFromServer(XMLHttpRequest.responseText, dataSink);
			}.bind(this),
			success:     function(data, textStatus) {
				dataSink(data);
			},
			type:        method,
			url:         url,
			contentType: 'application/json', // what I'm sending
			dataType:    'json',             // what I'm expecting
			data:        (shouldSendData) ? JSON.stringify(jsonPayload) : undefined,
			processData: false               // already stringified
		});
	},
	
	handleErrorFromServer: function(responseText, dataSinkCallback){
		if ( ! responseText || 0 === responseText.length) {
			this.showError("The server didn't answer at all and is probably down. Still you can try to reload the page and if that doesn't help contact your system administrator.");
			return;
		}
		var responseJSON = null;
		try {
			responseJSON = JSON.parse(responseText);
		}
		catch (exception) {
			this.showError("Server sent back unparseable data - try reloading the page!");
			return;
		}
		
		if (this.isBadJSONErrorReturnStructure(responseJSON)) {
			this.showError("Server sent back bad structured data - try reloading the page!");
			return;
		}
		var errorMessage = responseJSON.errors.join('\n');
		this.showError(errorMessage);
		
		// empty response is certainly not usable data
		// sadly I know no short way of checking a dictionary for 'emptiness'. jQuery 1.4 might help here
		if (isEmpty(responseJSON.current_data) || '{}' === JSON.stringify(responseJSON.current_data))
			return;
		
		// TODO: there should be more checking that the returned data actually is what we expect
		dataSinkCallback(responseJSON.current_data);
	},
	
	
	
	/// this checks very carefully that this is a json error structure
	isBadJSONErrorReturnStructure: function(someJSON){
		return ! someJSON
			|| 'object' !== typeof someJSON
			|| ! someJSON.errors
			|| Array !== someJSON.errors.constructor
			|| ! someJSON.current_data;
	},
	
	// Generic loader configurations .......................................
	
	configureLoaders: function() {
		this.backlogLoader = new BacklogServerRequest(this);
		this.backlogLoader.url = this.urlForBacklog.bind(this);
		
		this.columnLoader = new BacklogServerRequest(this);
		// no json view yet this.columnLoader.url = 
		// These will be filled after loadBacklog(aCallback) has called it's callback
		this.setStaticDefaultColumnConfiguration();
		this.initializeColumnConfigFromInfoIfAvailable();
		
		this.sprintListLoader = new BacklogServerRequest(this);
		this.sprintListLoader.url = this.urlForSprintList.bind(this);
		
		this.contingentsLoader = new BacklogServerRequest(this);
		this.contingentsLoader.url = this.url().listContingents.bind(this.url());
		
		this.alternativeViewsLoader = new BacklogServerRequest(this);
		this.alternativeViewsLoader.url = this.url().alternativeViewsURL.bind(this.url());
		
		this.configuredColumnsLoader = new BacklogServerRequest(this);
		// no json view yet this.configuredColumnsLoader.url = 
		
		var urlGenerator = this.url();
		
		this.burndownValuesLoader = new BacklogServerRequest(this);
		$.extend(this.burndownValuesLoader, {
			url: function() {
				var queryHash = this.filter_by && { filter_by: this.filter_by };
				return urlGenerator.jsonBurndownValues(queryHash);
			},
			setFilterBy: function(aString) {
				this.filter_by = aString;
			}
		});
	},
	
	// Loading tickets .....................................................
	
	startLoadingBacklog: function(optionalCallback) {
		this.backlogLoader.startLoading(optionalCallback);
	},
	
	urlForBacklog: function() {
		if ("sprint" === this.info().type)
			return encodedURLFromComponents("json", "sprints", this.info().sprint_or_release, "backlog");
		else if ("milestone" === this.info().type)
			return encodedURLFromComponents('json', 'backlogs', this.info().name, this.info().sprint_or_release);
		return encodedURLFromComponents('json', 'backlogs', this.info().name);
	},
	
	setBacklogFixture: function(aFixture) {
		this.backlogLoader.setFixture(aFixture);
	},
	
	// positions ....................................................
	
	urlForMassPositionsUpdate: function() {
		// TODO: this should always hand in 'global' when it is a global backlog as the sprint or release scope
		// else it could happen that a global backlog gets selected when we want to update positions and 
		// append '/positions' to this url
		return encodedURLFromComponents('json', 'backlogs', this.info().name, this.info().sprint_or_release, 'positions');
	},
	
	// Loading column configuration .........................................
	// TODO still incomplete
	
	startLoadingColumnConfiguration: function(optionalCallback) {
		this.columnLoader.startLoading(optionalCallback);
	},
	
	setStaticDefaultColumnConfiguration: function() {
		this.columnLoader.setFixture({
			sprint_backlog: [
				"id", "summary", ["remaining_time", "total_remaining_time"], "owner", "drp_resources", "estimated_remaining_time", "rd_points"
			],
			product_backlog: [
				"id", "summary", "sprint", "businessvalue", "roif", "story_priority", "rd_points"
			],
			human_readable_names: {
				id: 'ID', summary: 'Summary', remaining_time: "Remaining Time", owner: "Owner", 
				drp_resources: "Team Members", estimated_remaining_time: 'Estimated Remaining Time',
				rd_points: 'Story Points', businessvalue: 'Business Value', roif: 'Return on Investment Factor',
				story_priority: 'Story Priority', sprint: 'Sprint'
			}
		});
	},
	
	initializeColumnConfigFromInfoIfAvailable: function() {
		if (this.info() && this.info().configured_columns) {
			this.columnLoader.fixture = this.info().configured_columns;
		}
	},
	
	columnConfiguration: function() {
		// always prefer data from server over static defaults
		if (this.columnLoader.json.columns)
			return this.columnLoader.json.columns;
		
		// well, this is just supposed to return something... for now ...
		if ("sprint" === this.info().type)
			return this.columnLoader.json.sprint_backlog;
		else
			return this.columnLoader.json.product_backlog;
	},
	
	columnNames: function() {
		return this.columnLoader.json.human_readable_names;
	},
	
	// Loading backlog configuration .......................................
	// TODO: still very incomplete as it comes completely from the BACKLOG_INFO
	
	accessibleTypes: function() {
		if (this.info() && this.info().types_to_show)
			return this.info().types_to_show;
		else
			return [];
	},
	
	loggedInUser: function() {
		if (this.info() && this.info().username !== undefined)
			return this.info().username;
		else
			// use same behavior as Trac
			return 'anonymous';
	},
	
	setLoggedInUser: function(aUserName) {
		if (undefined === this.info())
			this._json = { content: {} };
		this.info().username = aUserName;
	},
	
	isUserLoggedIn: function() {
		return ('anonymous' !== this.loggedInUser());
	},
	
	permittedLinks: function() {
		if (this.info())
			return this.info().configured_child_types.permitted_links_tree;
	},
	
	configuredLinks: function() {
		return this.info().configured_child_types.configured_links_tree;
	},
	
	childTypesForTypeInLinkTree: function(aType, aLinkTree) {
		if (!aLinkTree)
			return;
		var childTypes = [];
		for (var possibleChild in aLinkTree[aType])
			childTypes.push(possibleChild);
		return childTypes;
	},

	permittedChildTypesForType: function(aType) {
		return this.childTypesForTypeInLinkTree(aType, this.permittedLinks());
	},
	
	configuredChildTypesForType: function(aType) {
		return this.childTypesForTypeInLinkTree(aType, this.configuredLinks());
	},
	
	preferredChildType: function(aType) {
		var allowedChildTypes = this.permittedChildTypesForType(aType);
		if (-1 !== $.inArray("task", allowedChildTypes))
			return "task";
		return allowedChildTypes[0];
	},
	
	attributesToCopyForType: function(parentType, childType) {
		var permittedLinks = this.permittedLinks();
		if ( ! permittedLinks[parentType][childType])
			return [];
		return JSON.parse(JSON.stringify(permittedLinks[parentType][childType]));
	},
	
	humanReadableTypeNames: function() {
		var backlogInfo = this.info();
		if ( ! backlogInfo)
	 		return {};
		return backlogInfo.type_aliases || {};
	},
	
	humanizeTypeName: function(aTypeName) {
		var map = this.humanReadableTypeNames();
		if (aTypeName in map)
			return map[aTypeName];
		
		return aTypeName.replace(/\w+/g, function(match) {
			return match.substring(0,1).toUpperCase() + match.substring(1).toLowerCase();
		});
	},
	
	topLevelTypes: function() {
		var allChildTypes = $.map(this.accessibleTypes(), function(each) {
			return this.configuredChildTypesForType(each);
		}.bind(this));
		return $.grep(this.accessibleTypes(), function(each) {
			return -1 === $.inArray(each, allChildTypes);
		}.bind(this));
	},
	
	topLevelContainerTypes: function() {
		return $.grep(this.topLevelTypes(), function(each) {
			return 0 !== this.configuredChildTypesForType(each).length;
		}.bind(this));
	},
	
	containerTypes: function() {
		return $.grep(this.accessibleTypes(), function(each) {
			return 0 !== this.configuredChildTypesForType(each).length;
		}.bind(this));
	},
	
	// Loading available sprints ............................................
	
	startLoadingSprintList: function(optionalCallback) {
		this.sprintListLoader.startLoading(optionalCallback);
	},
	
	urlForSprintList: function() {
		return encodedURLFromComponents('json', 'sprints');
	},
	
	// Loading contingents ..................................................
	
	startLoadingContingents: function(optionalCallback) {
		this.contingentsLoader.startLoading(optionalCallback);
	},
	
	postUpdateForContingent: function(json, optionalCallback) {
		this.post(this.url().updateContingent(json.name), json, optionalCallback);
	},
	
	putCreateContingent: function(json, optionalCallback) {
		this.put(this.url().createContingent(), json, optionalCallback);
	},
	
	// Loading configured columns ...........................................
	
	startLoadingConfiguredColumnns: function(optionalCallback) {
		this.configuredColumnsLoader.startLoading(optionalCallback);
	},
	
	// Loading Burndown Values ..............................................
	
	startLoadingBurndownValues: function(optionalCallback) {
		this.burndownValuesLoader.startLoading(optionalCallback);
	},
	
	shouldReloadBurndownFilteredByComponent: function() {
		if ( ! this.info())
			return false;
		
		return "component" === this.info().should_filter_by_attribute
			&& this.info().should_reload_burndown_on_filter_change_when_filtering_by_component;
	},
	
	// Loading Confirm Commitment ...........................................
	
	startLoadingAlternativeViews: function(optionalCallback) {
		this.alternativeViewsLoader.startLoading(optionalCallback);
	},
	
	// Loading Confirm Commitment ...........................................
	
	canConfirmCommitment: function() {
		return -1 !== $.inArray('AGILO_CONFIRM_COMMITMENT', this.permissions());
	},
	
	postConfirmCommitment: function(optionalCallback) {
		this.post(this.url().confirmCommitment(), {}, optionalCallback);
	},
	
	
	// Loading everything ...................................................
	
	// REFACT: we could evolve the stubbing functionality to be able to take the backlogInfo as an alternative source for the json
	// to prevent us from having to take an extra round trip to the -moon- server for everything
	stubEverything: function() {
		if ( ! this.info()) {
			this.setInfo({
				content: {
					type: "global",
					name: "aBacklog",
					sprint_or_release: "sprintName",
					access_control: {
						is_read_only: false
					},
					configured_child_types: {
						configured_links_tree: {},
						permitted_links_tree: {}
					}
				},
				content_type: "backlog_info",
				permissions: []
			});
		}
		
		this.backlogLoader.setFixture([]);
		this.setStaticDefaultColumnConfiguration();
		this.sprintListLoader.setFixture([]);
		// empty version of the application protocol. Emtpy because content is empty
		this.contingentsLoader.setFixture({ permissions:[], content_type:'contingent_list', content:[] });
		this.alternativeViewsLoader.setFixture(['new_backlog']);
	},
	
	loadBacklog: function(optionalCallback) {
		this.backlogLoadedCallback = optionalCallback;
		var didLoadCallback = this.didReceiveBacklog.bind(this);
		this.startLoadingBacklog(didLoadCallback);
		this.startLoadingColumnConfiguration(didLoadCallback);
		this.startLoadingSprintList(didLoadCallback);
		
		if (this.isLoadingSprint())
			this.startLoadingContingents(didLoadCallback);
	},
	
	didReceiveBacklog: function() {
		if (undefined === this.backlogLoader.json 
			|| undefined === this.columnLoader.json
			|| undefined === this.sprintListLoader.json)
			return;
		if (this.isLoadingSprint()
			&& undefined === this.contingentsLoader.json)
			return;
		
		if ($.isFunction(this.backlogLoadedCallback))
			this.backlogLoadedCallback(this);
	},

	
	loadContingents: function(optionalCallback) {
		this.backlogLoadedCallback = optionalCallback;
		var didLoadCallback = this.didReceiveContingents.bind(this);

		if (this.isLoadingSprint())
			this.startLoadingContingents(didLoadCallback);
		else
			this.didReceiveContingents();
	},
	
	didReceiveContingents: function() {
		if (this.isLoadingSprint()
				&& undefined === this.contingentsLoader.json)
			return;
		
		if ($.isFunction(this.backlogLoadedCallback))
			this.backlogLoadedCallback(this);
	},
	
	// Sending position information to the server ..............................
	
	// REFACT: add a callback so the gui can know when the positions are saved
	// REFACT: add error reporting!
	sendPositionsUpdateToServer: function(anOrder) {
		this.post(this.urlForMassPositionsUpdate(), {positions: anOrder});
	},
	
	missingCommaErrorPreventer:''
});

// ........................................................................


// REFACT: .fixture should become the generic way for the backlog to initialize stuff out of the info dict
function BacklogServerRequest(aCommunicator) {
	this.loader = aCommunicator;
	this.fixture = undefined;
	this.callback = undefined;
	this.json = undefined;
}
$.extend(BacklogServerRequest.prototype, {
	
	setFixture: function(aFixture) {
		this.fixture = aFixture;
	},
	
	startLoading: function(aCallback) {
		this.callback = aCallback;
		
		if (this.fixture) {
			this.receiveJSON(this.fixture);
			return;
		}
		
		this.loader.assertInfoIsSet();
		this.loader.get(this.url(), this.receiveJSON.bind(this));
	},
	
	receiveJSON: function(someJSON) {
		this.json = someJSON;
		if ($.isFunction(this.callback))
			this.callback(someJSON);
	},
	
	didReceiveJSON: function() {
		return undefined !== this.json;
	},
	
	url: function() {
		throw "You need to override url() to return the url to get from the server.";
	},
	
	missingCommaErrorPreventer:''
});


// ........................................................................


function JSONIntegrityChecker(json) {
	this.setJSON(json);
}
$.extend(JSONIntegrityChecker.prototype, {
	setJSON: function(json) {
		this.json = json;
	},
	
	doesMatch: function(anElement, aMatcher) {
		return !! aMatcher(anElement);
	},
	
	errorsForCriteria: function(aCriteria) {
		// REFACT: rename test and arrayTest keys so it is self documenting whether returning true or false marks each element as good or bad
		// using $.map to collect errors as it flattens returned arrays
		if ('test' in aCriteria) {
			if (this.doesMatch(this.json, aCriteria.test))
				return $.map([this.json], aCriteria.errorFor);
		}
		
		if ('arrayTest' in aCriteria) {
			return $.map(this.json, function(element) {
				if (this.doesMatch(element, aCriteria.arrayTest))
					return aCriteria.errorFor(element);
			}.bind(this));
		}
		return [];
	},
	
	errorsForCriterias: function(someCriterias) {
		return $.map(someCriterias, this.errorsForCriteria.bind(this));
	},
	
	// Aggregated checks .................................................
	
	checkAllTicketsHaveAnID: function() {
		return this.errorsForCriteria({
			arrayTest: function(element) { return undefined === element.id; },
			errorFor: function(element) { return "Found a ticket without an id. This is an unrecoverable error as each ticket needs to have an id to be identified by. Try reloading the page and if that doesn't work contact your system administrator."; }
		});
	},
	
	checkTasklikesHaveNoChildren: function() {
		return this.errorsForCriteria({
			arrayTest: function(element) { 
				return undefined !== element.remaining_time
					&& element.outgoing_links
					&& element.outgoing_links.length > 0;
			},
			errorFor: function(element) { return 'Ticket #' + element.id + ' is tasklike (has attribute remaining_time) but still has children. Child-Tickets for tasklikes are not supported right now. To continue please remove these child-links and make sure that there are no children associated with tickets of type ' + element.type + '. You can change this setting in Agilo > Admin > Links.'; }
		});
	},
	
	missingCommaErrorPreventer:''
});



// ........................................................................


function URLGenerator(anInfoDict) {
	this.setBacklogInfo(anInfoDict);
}
$.extend(URLGenerator.prototype, {
	
	// Helpers ......................................
	
	setBacklogInfo: function(anInfoDict) {
		this.info = anInfoDict;
	},
	
	backlogInfo: function() {
		return this.info;
	},
	
	sprintName: function() {
		return this.backlogInfo().sprint_or_release;
	},
	
	backlogName: function() {
		return this.backlogInfo().name;
	},
	
	// URL Generators ................................
	
	// REFACT: It would be nice to get more structure in here so the urls that belong together are better seen and can more easily be changed together
	// One approach could be to structure it so that urls could be generated like this:
	// backlogs.get(), backlogs.post(), contingents.get(), contingent.get('foo')
	// I don't really like it yet, but it's a start for some thinking
	
	backlogViewURLs: function(optionalQueryParameters) {
		if ('global' === this.backlogInfo().type)
			return {
				new_backlog: encodedURLFromComponents('backlog', this.backlogName(), optionalQueryParameters)
			};
		else 
			return {
				new_backlog: encodedURLFromComponents('backlog', this.backlogName(), this.sprintName()), 
				whiteboard: encodedURLFromComponents('agilo-pro', 'sprints', this.sprintName(), 'whiteboard')
			};
	},
	
	backlogViewURL: function() {
		return this.backlogViewURLs().new_backlog;
	},
	
	whiteboardViewURL: function() {
		return this.backlogViewURLs().whiteboard;
	},
	
	alternativeViewsURL: function() {
		return encodedURLFromComponents('json', 'config', 'backlog', 'alternative_views');
	},
	
	jsonBurndownValues: function(optionalQueryParameters) {
		return encodedURLFromComponents('json', 'sprints', this.sprintName(), 'burndownvalues', optionalQueryParameters);
	},
	
	newTicketPageURL: function(optionalQueryParameters) {
		return encodedURLFromComponents('newticket', optionalQueryParameters);
	},
	
	listContingents: function() {
		return encodedURLFromComponents('json', 'sprints', this.sprintName(), 'contingents');
	},
	
	createContingent: function() {
		return this.listContingents();
	},
	
	updateContingent: function(aContingentName) {
		return encodedURLFromComponents('json', 'sprints', this.sprintName(), 'contingents', aContingentName, 'add_time');
	},
	
	confirmCommitment: function() {
		return encodedURLFromComponents('json', 'sprints', this.sprintName(), 'commit');
	},
	
	missingCommaErrorPreventer:''
});
