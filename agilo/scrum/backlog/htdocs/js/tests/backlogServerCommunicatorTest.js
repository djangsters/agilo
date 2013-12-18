
// TODO: add a test that shows that global backlogs always generate the correct url (and decide whether we always want to append 'global' for their scope. That might make implementation much easier)
// TODO: consider what defense we can have against tickets which aren't containers, but still have children
// TODO: consider to guard against non unique IDs?
// TODO: consider abstracting  the tests so they test the same stuff for each of the modules provided

module('backlog loader test', {
	setup: function(){
		// This is the minimal info thing - it can contain much more already
		var content = {"type": "global", "name": "aBacklog", "sprint_or_release": "sprintName"};
		this.info = wrapContentInInfo(content);
		this.loader = new BacklogServerCommunicator(this.info);
		
		this.setChildMapping = function(mapping) {
			this.loader.info().configured_child_types = { permitted_links_tree: mapping,
														configured_links_tree: mapping };
		};
		
		this.errors = [];
		this.loader.registerErrorSink(function(errorMessage) { this.errors.push(errorMessage); }.bind(this));
	}
});


test("can set backlog info after constructor", function() {
	this.loader.setInfo({
		content: "fnord"
	});
	equals(this.loader.info(), "fnord");
});

test("will throw if no backlogInfo is provided", function() {
	this.loader.setInfo(undefined);
	assertThrows(/You need to provide a backlog info to the loader/, this.loader.startLoadingBacklog.bind(this.loader));
	assertThrows(/You need to provide a backlog info to the loader/, this.loader.startLoadingSprintList.bind(this.loader));
});

// Generic server communications ................................

test("error return: shows error if nothing is returned by the server", function() {
	this.loader.handleErrorFromServer(undefined);
	equals(this.errors.length, 1);
	assertMatches(this.errors[0], "The server didn't answer at all and is probably down");
	
	this.loader.handleErrorFromServer('');
	equals(this.errors.length, 2);
	assertMatches(this.errors[1], "The server didn't answer at all and is probably down");
});

test("error return: shows error if result is not parseable json", function() {
	// e.g. trac-error that got through accidentally
	this.loader.handleErrorFromServer('<html>fnordifnord</html>');
	equals(this.errors.length, 1);
	assertMatches(this.errors[0], "Server sent back unparseable data");
});

test("error return: shows error if structure is not valid error json", function() {
	this.loader.handleErrorFromServer('{}');
	equals(this.errors.length, 1);
	assertMatches(this.errors[0], "Server sent back bad structured data");
});


test("doesn't callback if error is shown (all errors should be fatal at this stage)", function() {
	expect(0);
	var checker = function() { ok(false, "checker was called where it shouldn't have been!"); };
	this.loader.handleErrorFromServer(undefined, checker);
	this.loader.handleErrorFromServer('', checker);
	this.loader.handleErrorFromServer('<html>fnordifnord</html>', checker);
	this.loader.handleErrorFromServer('{}', checker);
});


test("only calls datasink in error case if data was actually returned", function() {
	expect(1);
	var checker = function() { ok(false, "checker was called where it shouldn't have been!"); };
	this.loader.handleErrorFromServer(JSON.stringify({
		errors: [],
		current_data: {}
	}), checker);
	this.loader.handleErrorFromServer(JSON.stringify({
		errors: [],
		current_data: []
	}), checker);
	// TODO: consider to also disallow empty strings as current_data? (currently catched earlier as an invalid type of current_data when the structure is checked)
	same(this.errors, ['', '']);
});


// Loading backlogs ...........................................

test("loader knows the correct url for sprint backlogs", function() {
	var content = {"type": "sprint", "name": "Sprint Backlog", "sprint_or_release": "My Sprint #1"};
	this.loader.setInfo(wrapContentInInfo(content));
	var url = this.loader.urlForBacklog();
	equals(url, "/json/sprints/My%20Sprint%20%231/backlog");
});

test("loader knows the correct url for the product backlog", function() {
	var content = {"type": "global", "name": "Product Backlog", "sprint_or_release": "global"};
	this.loader.setInfo(wrapContentInInfo(content));
	var url = this.loader.urlForBacklog();
	equals(url, "/json/backlogs/Product%20Backlog");
});

test("loader knows the correct url for release backlogs", function() {
	var content = {"type": "milestone", "name": "Our Release Backlog", "sprint_or_release": "1.0"};
	this.loader.setInfo(wrapContentInInfo(content));
	var url = this.loader.urlForBacklog();
	equals(url, "/json/backlogs/Our%20Release%20Backlog/1.0");
});

test("can callback after successful load", function() {
	var sensedJSON = "marker";
	this.loader.startLoadingBacklog(function(json){
		sensedJSON = json;
	});
	equals(sensedJSON, "marker");
	this.loader.backlogLoader.receiveJSON("fnord");
	equals(sensedJSON, "fnord");
	equals(this.loader.backlogLoader.json, "fnord");
});

test("can use fixture for synchronous backlog loading", function() {
	expect(1);
	this.loader.setInfo(undefined); // no info needed if fixtures are used
	this.loader.setBacklogFixture("foo");
	this.loader.startLoadingBacklog(function(json){
		equals(json, "foo");
	});
});

// Loading and saving positions .............................................

test("send correct json format when updating positions", function() {
	expect(1);
	this.loader.post = function(anURL, aJSON) {
		same({positions: [1, 2]}, aJSON);
	};
	this.loader.sendPositionsUpdateToServer([1, 2]);
});

test("knows the correct url to get and set multiple ticket positions together", function() {
	equals(this.loader.urlForMassPositionsUpdate(), "/json/backlogs/aBacklog/sprintName/positions");
});

test("can apply old positions on error from server", function() {
	// TODO: We don't send them along yet
});

test("can mock alternative views", function() {
	this.loader.alternativeViewsLoader.setFixture("fnord");
	var sensed = "marker";
	this.loader.startLoadingAlternativeViews(function(json){
		sensed = json;
	});
	equals(sensed, "fnord");
});


// Column Configuration ..........................................................

test("can mock column-configuration", function() {
	this.loader.columnLoader.setFixture("fnord");
	var sensed = "marker";
	this.loader.startLoadingColumnConfiguration(function(json){
		sensed = json;
	});
	equals(sensed, "fnord");
});

test("initializes column configuration from info if available", function() {
	this.loader.info().configured_columns = {
		columns: ['foo', 'bar'],
		human_readable_names: { foo: 'Foo', bar: 'Bar' }
	};
	this.loader.configureLoaders();
	same(this.loader.columnLoader.fixture, this.loader.info().configured_columns);
});


test("pre-loads default configuration automatically", function() {
	var sensed = "marker";
	this.loader.startLoadingColumnConfiguration(function(json){
		sensed = json;
	});
	// TODO: this format is very much a work in progress until we know what we actually need
	same(sensed.sprint_backlog, 
		["id", "summary", ["remaining_time", "total_remaining_time"], "owner", "drp_resources", "estimated_remaining_time", "rd_points"]);
	same(sensed.product_backlog, 
		["id", "summary", "sprint", "businessvalue", "roif", "story_priority", "rd_points"]);
	// TODO: these should probably come from somewhere else? Translation provider or something like it
	var stubbed_values = {
		id: 'ID', summary: 'Summary', remaining_time: "Remaining Time", owner: "Owner", 
		drp_resources: "Team Members", estimated_remaining_time: 'Estimated Remaining Time',
		rd_points: 'Story Points', businessvalue: 'Business Value', roif: 'Return on Investment Factor',
		story_priority: 'Story Priority', sprint: 'Sprint'
	};
	same(sensed.human_readable_names, stubbed_values);
	same(this.loader.columnNames(), stubbed_values);
});

test("loader knows which static configuration to return", function() {
	this.loader.startLoadingColumnConfiguration();
	this.loader.info().type = 'global';
	same(this.loader.columnConfiguration(), this.loader.columnLoader.fixture.product_backlog);
	this.loader.info().type = 'sprint';
	same(this.loader.columnConfiguration(), this.loader.columnLoader.fixture.sprint_backlog);
});

test("always prefers dynamic configuration", function() {
	this.loader.info().configured_columns = {
		columns: ['foo', 'bar'],
		human_readable_names: { foo: 'Foo', bar: 'Bar' }
	};
	this.loader.configureLoaders();
	this.loader.startLoadingColumnConfiguration();
	same(this.loader.columnConfiguration(), this.loader.info().configured_columns.columns);
});


test("autoloads configuration with the rest", function() {
	// TODO: right now everything is still stubbed out and is static
});


// Username ..............................................................

test("can return username from backlog-info", function() {
	same(this.loader.loggedInUser(), 'anonymous');
	this.loader.setInfo(wrapContentInInfo({username: 'agilouser'}));
	same(this.loader.loggedInUser(), 'agilouser');
});

test("knows if user is logged in", function() {
	same(this.loader.loggedInUser(), 'anonymous');
	ok( ! this.loader.isUserLoggedIn());
	
	this.loader.setInfo(wrapContentInInfo({username: 'someone'}));
	ok(this.loader.isUserLoggedIn());
});

test("can set currently logged in user", function() {
	ok( ! this.loader.isUserLoggedIn());
	this.loader.setLoggedInUser('agilouser');
	same(this.loader.loggedInUser(), 'agilouser');
});


// Loading sprint names ..................................................

test("knows if it is loading a sprint backlog", function() {
	equals(this.loader.isLoadingSprint(), false);
	this.info.content.type = 'sprint';
	this.loader.setInfo(this.info);
	equals(this.loader.isLoadingSprint(), true);
});

test("knows right url for loading sprints", function() {
	equals(this.loader.urlForSprintList(), '/json/sprints');
});

test("can callback after successful load of sprints", function() {
	var sensedJSON = 'not yet';
	this.loader.startLoadingSprintList(function(json){
		sensedJSON = json;
	});
	equals(sensedJSON, 'not yet');
	this.loader.sprintListLoader.receiveJSON('now');
	equals(sensedJSON, 'now');
});

test("can use sprintListFixture as synchronous datasource", function() {
	expect(1);
	this.loader.sprintListLoader.setFixture('fixture');
	this.loader.startLoadingSprintList(function(){ ok(true); });
});

// Loading burndown values ....................................................

test("can callback after successful load of burndown values", function() {
	var sensedJSON = null;
	this.loader.startLoadingBurndownValues(function(json) { sensedJSON = json; });
	equals(sensedJSON, null);
	this.loader.burndownValuesLoader.receiveJSON('fnord');
	equals(sensedJSON, 'fnord');
});

test("knows when burndown reloading should happen", function() {
	var setFilterBy = function(filterByString, doReload) {
		this.info.content.should_filter_by_attribute = filterByString;
		this.info.content.should_reload_burndown_on_filter_change_when_filtering_by_component =  doReload;
	}.bind(this);
	
	setFilterBy(undefined, undefined);
	ok( ! this.loader.shouldReloadBurndownFilteredByComponent());
	
	setFilterBy('fnord', true);
	ok( ! this.loader.shouldReloadBurndownFilteredByComponent());
	
	setFilterBy('component', false);
	ok( ! this.loader.shouldReloadBurndownFilteredByComponent());
	
	setFilterBy('component', true);
	ok(this.loader.shouldReloadBurndownFilteredByComponent());
});

// Loading and saving contingents .............................................

test("can callback after loading contingents", function() {
	var sensor = null;
	this.loader.startLoadingContingents(function(json){ sensor = json; });
	equals(sensor, null);
	this.loader.contingentsLoader.receiveJSON('fnord');
	equals(sensor, 'fnord');
});

test("can set a fixture for contingents", function() {
	expect(1);
	this.loader.contingentsLoader.setFixture('fnord');
	this.loader.startLoadingContingents(function(json){ equals(json, 'fnord'); });
});

test("can submit contingent to server", function() {
	expect(2);
	var actualJSON = { name: 'fnord' };
	this.loader.post = function(url, json, callback) {
		equals(url, this.loader.url().updateContingent('fnord'));
		same(json, actualJSON);
	}.bind(this);
	this.loader.postUpdateForContingent(actualJSON);
});

test("can submit new contingent to server", function() {
	expect(2);
	var actualJSON = 'fnord';
	this.loader.put = function(url, json, callback) {
		equals(url, this.loader.url().createContingent());
		equals(json, actualJSON);
	}.bind(this);
	this.loader.putCreateContingent(actualJSON);
});


test("will only load contingents with the rest if loading a sprint", function() {
	var didCall = false;
	this.loader.startLoadingContingents = function(){ didCall = true; };
	ok( ! this.loader.isLoadingSprint());
	this.loader.loadBacklog();
	ok( ! didCall);
	
	this.loader.info().type = 'sprint';
	ok(this.loader.isLoadingSprint());
	this.loader.loadBacklog();
	ok(didCall);
});

test("does not wait for contingents if not loading a sprint", function() {
	var sensor = "fnord";
	this.loader.loadBacklog(function(loader){
		sensor = loader;
	});
	this.loader.columnLoader.receiveJSON('baz');
	this.loader.backlogLoader.receiveJSON("bar");
	this.loader.sprintListLoader.receiveJSON('foobar');
	ok(sensor === this.loader);
});

// Accessible types .....................................................

test("can return accessible types from backlog-info", function() {
	same(this.loader.accessibleTypes(), []);
	this.loader.setInfo(wrapContentInInfo({types_to_show: ['fnord']}));
	same(this.loader.accessibleTypes(), ['fnord']);
});

// Accessing childtype mappings ..........................................

function childTypesMappingFixture() {
	return {
		"configured_links_tree": {
			"requirement": {"story": ["owner"]}, 
			"task": {}, "aq_story": {"task": ["owner", "sprint"]}, 
			"story": {"task": ["owner", "sprint"]}, 
			"aq_requirement": {"aq_story": ["owner"], 
			"story": ["owner"]}, 
			"bug": {"story": [], "task": ["owner", "sprint"]}
		}, 
		"permitted_links_tree": {
			"requirement": {}, 
			"task": {}, "aq_story": {"task": ["owner", "sprint"]}, 
			"story": {"task": ["owner", "sprint"]}, 
			"aq_requirement": {}, 
			"bug": {"story": [], 
			"task": ["owner", "sprint"]}
		}
	};
}

test("can access permitted links via the backlog-info", function() {
	var mappings = childTypesMappingFixture();
	this.loader.info().configured_child_types = mappings;
	same(this.loader.permittedLinks(), mappings.permitted_links_tree);
});

test("can access permitted links via the backlog-info", function() {
	var mappings = childTypesMappingFixture();
	this.loader.info().configured_child_types = mappings;
	same(this.loader.configuredLinks(), mappings.configured_links_tree);
});

test("can access global mapping of types", function() {
	this.loader.info().configured_child_types = { 
		configured_links_tree: {"requirement": {}, "task": {}, "story": {"task": ["owner", "sprint"]}, "bug": {"task": ["owner", "sprint"]}},
		permitted_links_tree: {"requirement": {}, "task": {}, "story": {}, "bug": {"task": ["owner", "sprint"]}}
	};
	same(this.loader.configuredChildTypesForType('requirement'), []);
	same(this.loader.configuredChildTypesForType('story'), ['task']);
	same(this.loader.permittedChildTypesForType('story'), []);
	same(this.loader.permittedChildTypesForType('bug'), ['task']);
});

test("knows which attributes should be copied to child tickets for a specific type", function() {
	this.loader.info().configured_child_types = { 
		permitted_links_tree: {"foo": {"bar": ["sprint", "someattribute"]}}
	};
	same(this.loader.attributesToCopyForType("foo", "bar"), ["sprint", "someattribute"]);
});

test("can tell which child type is preferred", function() {
	this.setChildMapping({"foo": {"bar": []}});
	equals(this.loader.preferredChildType('foo'), 'bar');
});

test("always prefers tasks as child types if they are available", function() {
	this.setChildMapping({
		"bug": {"story":[], "task":[], "foo":[]}
	});
	equals(this.loader.preferredChildType('bug'), 'task');
});

test("knows which types are top level items", function() {
	this.loader.setInfo(wrapContentInInfo({types_to_show: ['impediment', 'bug', 'task']}));
	this.setChildMapping({
		impediment: { bug: []},
		bug: {},
		task: {}
	});
	same(this.loader.topLevelTypes(), ['impediment', 'task']);
});

test("knows which types are top level containers", function() {
	this.loader.setInfo(wrapContentInInfo({types_to_show: ['impediment', 'bug', 'task']}));
	this.setChildMapping({
		impediment: { bug: []},
		bug: {},
		task: {}
	});
	same(this.loader.topLevelContainerTypes(), ['impediment']);
});

test("knows which types are containers", function() {
	this.loader.setInfo(wrapContentInInfo({types_to_show: ['impediment', 'bug', 'task']}));
	this.setChildMapping({
		impediment: { bug: []},
		bug: { task: []},
		task: {}
	});
	same(this.loader.containerTypes(), ['impediment', 'bug']);	
});


test("can set and get permissions", function() {
	var backlog_info = wrapContentInInfo({});
	backlog_info.permissions.push('fnord');
	this.loader.setInfo(backlog_info);
	
	same(this.loader.permissions(), ['fnord']);
});

test("permissions are empty if uninitialized", function() {
	var loader = new BacklogServerCommunicator();
	same(loader.permissions(), []);
});


test("can decide if user is allowed to confirm commitment", function() {
	var backlog_info = wrapContentInInfo({});
	backlog_info.permissions.push('AGILO_CONFIRM_COMMITMENT');
	this.loader.setInfo(backlog_info);
	
	ok(this.loader.canConfirmCommitment());
});


test("can decide if user is forbidden to confirm commitment", function() {
	var backlog_info = wrapContentInInfo({});
	this.loader.setInfo(backlog_info);
	
	ok( ! this.loader.canConfirmCommitment());
});

test("can send confirm commitment to server", function() {
	expect(1);
	this.loader.post = function(url, json, callback) {
		equals(url, this.loader.url().confirmCommitment('fnord'));
	}.bind(this);
	this.loader.postConfirmCommitment();
});


// Ticket Type Aliases .............................................

test("can resolve custom type alias from backlog info", function() {
	this.loader.setInfo(wrapContentInInfo({type_aliases: {'story': 'Fnord'}}));
	same(this.loader.humanizeTypeName('story'), 'Fnord');	
});



// Everything is loaded together ....................................
// (probably need to modify these whenever a new type to load is added)

test("can start all requests together", function() {
	expect(4);
	// only if we load a sprint is really everything loaded
	this.loader.info().type = 'sprint';
	
	var sensor = function(){ ok(true); };
	this.loader.startLoadingBacklog = sensor;
	this.loader.startLoadingColumnConfiguration = sensor;
	this.loader.startLoadingSprintList = sensor;
	this.loader.startLoadingContingents = sensor;
	this.loader.loadBacklog();
});

test("can get callback after all elements (tickets and column configuration) are loaded", function() {
	// only if we load a sprint is really everything loaded
	this.loader.info().type = 'sprint';
	
	var sensor = "fnord";
	this.loader.loadBacklog(function(loader){
		sensor = loader;
	});
	equals(sensor, "fnord");
	this.loader.columnLoader.receiveJSON('baz');
	equals(this.loader.columnLoader.json, "baz");
	equals(sensor, "fnord");
	this.loader.backlogLoader.receiveJSON("bar");
	equals(this.loader.backlogLoader.json, "bar");
	equals(sensor, "fnord");
	this.loader.sprintListLoader.receiveJSON('foobar');
	equals(this.loader.sprintListLoader.json, 'foobar');
	// equals(sensor, "fnord");
	this.loader.contingentsLoader.receiveJSON('foobar');
	equals(this.loader.contingentsLoader.json, 'foobar');
	
	ok(sensor === this.loader);
});

test("stubEverything really stubs everything", function() {
	expect(1);
	this.loader.stubEverything();
	this.loader.loadBacklog(function(){ ok(true); });
});

// Error reporting .......................................................

test("can register for error messages from loading", function() {
	expect(1);
	this.loader.registerErrorSink(function(errorMessage){
		equals(errorMessage, 'fnord');
	});
	this.loader.showError('fnord');
});




module("backlog loader request capsule", {
	setup: function() {
		// This is the minimal info thing - it can contain much more already
		var info = wrapContentInInfo({"type": "global", "name": "aBacklog", "sprint_or_release": "sprintName"});
		this.loader = new BacklogServerCommunicator(info);
		this.capsule = new BacklogServerRequest(this.loader);
		this.capsule.url = function(){};
	}
});

test("can instantiate capsule", function() {
	ok(this.capsule);
	equals(this.capsule.loader, this.loader);
});

test("can return fixture synchronously", function() {
	expect(1);
	this.capsule.setFixture('fnord');
	this.capsule.startLoading(function(result) {
		equals(result, 'fnord');
	});
});

test("will call back when data has arrived", function() {
	expect(1);
	this.capsule.startLoading(function(result) {
		equals(result, 'fnord');
	});
	this.capsule.receiveJSON('fnord');
});

test("will start request to with callback pointing to itself", function() {
	var sensor = null;
	var originalCallback = function(data) { sensor = data; };
	var receivedCallback = null;
	this.loader.get = function(url, callback) {
		ok(callback !== originalCallback);
		receivedCallback = callback;
	};
	this.capsule.startLoading(originalCallback);
	
	// verify that this is the right callback
	equals(sensor, null);
	receivedCallback('fnord');
	equals(sensor, 'fnord');
	
});

test("will cache json after the request was made", function() {
	this.capsule.startLoading(function(){});
	equals(this.capsule.receiveJSON('fnord'));
	equals(this.capsule.json, 'fnord');
});

test("can leave out callback", function() {
	this.capsule.startLoading();
	equals(this.capsule.receiveJSON('fnord'));
	equals(this.capsule.json, 'fnord');
});

test("knows if the callback has already returned", function() {
	this.capsule.receiveJSON('fnord');
	ok(this.capsule.didReceiveJSON());
});

test("asserts that info is set before a request is made", function() {
	this.loader.setInfo(undefined);
	assertThrows(/You need to provide a backlog info to the loader/, this.capsule.startLoading.bind(this));
});

test("throws if no url method is set when a request is started", function() {
	// restore original url method (overridden in setup)
	this.capsule.url = BacklogServerRequest.prototype.url;
	assertThrows(/You need to override url\(\) to return the url to get from the server/,
		this.capsule.startLoading.bind(this.capsule));
});






module("checking backlog json integrity", {
	setup: function(){
		this.tester = new JSONIntegrityChecker();
		this.never = function() { return false; };
		this.always = function() { return true; };
		this.identity = function(element) { return element; };
	}
});

test("smoke", function() {
	var tester = new JSONIntegrityChecker('foo');
	equals(tester.json, 'foo');
});

test("can apply test to one element", function() {
	this.tester.doesMatch('fnord', function(element) { return 'fnord' === element; });
});

test("can hand in criteria with error message", function() {
	this.tester.setJSON('fnord');
	var errors = this.tester.errorsForCriteria({
		test: this.always, 
		errorFor: this.identity
	});
	same(errors, ['fnord']);
});

test("does not produce error message if the test doesn't alarm", function() {
	this.tester.setJSON('fnord');
	var errors = this.tester.errorsForCriteria({
		test: this.never, 
		errorFor: this.identity
	});
	same(errors, []);
});

test("can return multiple error messages from errorFor", function() {
	this.tester.setJSON('fnord');
	var errors = this.tester.errorsForCriteria({
		test: this.always, 
		errorFor: function(json) { return ['first', 'second']; }
	});
	same(errors, ['first', 'second']);
});

test("can hand in multiple criteria with error messages", function() {
	this.tester.setJSON('fnord');
	var errors = this.tester.errorsForCriterias([{
		test: this.always, 
		errorFor: function(json) { return ['first', 'second']; }
	},
	{
		test: this.always,
		errorFor: function() { return ['three', 'four']; }
	}]);
	same(errors, ['first', 'second', 'three', 'four']);
});

test("can define criterias for arrays", function() {
	this.tester.setJSON(['foo', 'bar']);
	var errors = this.tester.errorsForCriteria({
		arrayTest: this.always,
		errorFor: function(element) { return element; }
	});
	same(errors, ['foo', 'bar']);
});

test("can test backlog for id and isTaskLike constraints", function() {
	this.tester.setJSON([{ /* missing id */ }, { id: 1 }, { id: 2 }]);
	var errors = this.tester.checkAllTicketsHaveAnID();
	equals(errors.length, 1);
	assertMatches(errors[0], /Found a ticket without an id/);
});

test("can test backlog for tasklikes with children", function() {
	this.tester.setJSON([{ remaining_time: 1, outgoing_links: [23] }, 
		{ remaining_time: 0 }, { remaining_time: 1 }]);
	var errors = this.tester.checkTasklikesHaveNoChildren();
	equals(errors.length, 1);
	assertMatches(errors[0], /is tasklike/);
	assertMatches(errors[0], /but still has children/);
});




module('url generator', {
	setup: function() {
		this.info = {"type": "global", "name": "aBacklogName", "sprint_or_release": "aSprintName"};
		this.url = new URLGenerator(this.info);
	}
});

test("smoke", function() {
	ok(this.url);
});

test("can set backlog info", function() {
	same(this.url.backlogInfo(), this.info);
});

test("can generate urls for global backlog views", function() {
	equals(this.url.backlogViewURL(), "/backlog/aBacklogName");
});

test("can generate urls for sprint backlogs", function() {
	this.info.type = 'sprint';
	equals(this.url.backlogViewURL(), "/backlog/aBacklogName/aSprintName");
	equals(this.url.whiteboardViewURL(), "/agilo-pro/sprints/aSprintName/whiteboard");
});

test("can generate url for burndown json view", function() {
	equals(this.url.jsonBurndownValues(), "/json/sprints/aSprintName/burndownvalues");
	assertMatches(this.url.jsonBurndownValues({filter_by: 'fnord'}), /burndownvalues\?filter_by=fnord$/);
});

test("can generate url for new ticket page", function() {
	equals(this.url.newTicketPageURL(), "/newticket");
});

test("knows contingent submit url", function() {
	equals(this.url.updateContingent('fnord'), '/json/sprints/aSprintName/contingents/fnord/add_time');
});

test("knows contingent list url", function() {
	equals(this.url.listContingents(), '/json/sprints/aSprintName/contingents');
});

test("knows contingent create url", function() {
	equals(this.url.createContingent(), '/json/sprints/aSprintName/contingents');
});

test("knows confirm commitment url", function() {
	equals(this.url.confirmCommitment(), '/json/sprints/aSprintName/commit');
});
