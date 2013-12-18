module('a ticket can', {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
	}
});

test("accept json", function() {
	var ticket = new Ticket();
	ticket.setJSON('fnord');
	equals(ticket.json, 'fnord');
});

test("can set json in the constructor", function() {
	var ticket = new Ticket('fnord');
	equals(ticket.json, 'fnord');
});

test("can set backlog object", function() {
	var backlog = new Backlog();
	var ticket = new Ticket();
	ticket.setBacklog(backlog);
	equals(ticket.backlog, backlog);
});

test("can set backlog in the constructor", function() {
	var backlog = new Backlog();
	var ticket = new Ticket('fnord', backlog);
	equals(ticket.backlog, backlog);
});

test("tickets know if they are taskLike", function() {
	var ticket = new Ticket({id:1});
	equals(ticket.isTaskLike(), false);
	
	ticket = new Ticket({id:1, remaining_time:0});
	equals(ticket.isTaskLike(), true);
});

test("tasks are recognized as task-like", function() {
	var unreferencedTask = this.injectTask(3);
	ok(unreferencedTask.isTaskLike());
	
	var story = this.injectUserStory(1);
	var task = this.injectTask(2, story);
	ok(task.isTaskLike());
});

test("containers know they are containers (even if they don't have children)", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var task = this.injectTask(3, story);
	
	ok(requirement.isContainer());
	ok(story.isContainer());
	ok( ! task.isContainer());
});

test("knows if it has incoming links", function() {
	var requirement = this.injectRequirement(23);
	var story = this.injectUserStory(3, requirement);
	ok( ! requirement.hasIncomingLinks());
	ok(story.hasIncomingLinks());
});

test("knows if it is a fake ticket", function() {
    var requirement = this.injectRequirement(23);
    var story = this.injectRequirement(-1);
    ok( ! requirement.isFakeTicket());
    ok( story.isFakeTicket());
});

test("know what keys it has and get their value", function() {
	var task = this.injectTask(1);
	ok(task.hasKey('id'));
	ok(task.hasKey('summary'));
	ok( ! task.hasKey('fnord'));
});

test("get json values via a function", function() {
	var task = this.injectTask(1);
	equals(task.valueForKey('id'), 1);
	equals(task.valueForKey('fnord'), "", "should return empty string for non existant keys");
});

test("know if a value would make a change to a property", function() {
	var task = this.injectTask(1);
	task.json.foo = 0;
	ok( ! task.wouldChangeValueForKey(0, 'foo'), "literal 0");
	ok( ! task.wouldChangeValueForKey('0', 'foo'), "string 0");
	ok(task.wouldChangeValueForKey('', 'foo'), "empty string");

	task.json.foo = '';
	ok(task.wouldChangeValueForKey(0, 'foo'), "literal 0");
	ok(task.wouldChangeValueForKey('0', 'foo'), "string 0");
	ok( ! task.wouldChangeValueForKey('', 'foo'), "empty string");
	
	task.json.foo = 10;
	ok( ! task.wouldChangeValueForKey(10, 'foo'), "literal 10");
	ok( ! task.wouldChangeValueForKey('10', 'foo'), "string 10");
});

test("can access multi-linked children", function() {
	var story1 = this.injectStory(1);
	var story2 = this.injectStory(2);
	var task = this.injectTask(3, story1);
	task.json.incoming_links.push(2);
	story2.linkToChild(task);
	
	ok(story1.hasChildren());
	ok(story2.hasChildren());
	same(story1.children()[0].json, task.json);
	same(story2.children()[0].json, task.json);
});

test("knows the index of of a specific parent if it has multiple ones", function() {
	var story1 = this.injectStory(1);
	var story2 = this.injectStory(2);
	var task = this.injectTask(3, story1);
	task.json.incoming_links.push(2);
	story2.linkToChild(task);
	
	equals(task.indexOfParent(story1), 0);
	equals(task.indexOfParent(story2), 1);
});

test("throws if asked for the index of a non parent", function() {
	var story1 = this.injectStory(1);
	var story2 = this.injectStory(2);
	assertThrows(/not a child of/, function(){ story1.indexOfParent(story2); });
});

test("can access type in humanized form", function() {
	// Story instead of User Story because the uninitialized humanizer will just capitalize
	equals(this.injectStory(1).humanReadableTypeName(), 'Story');
	equals(this.injectTask(2).humanReadableTypeName(), 'Task');
	equals(this.injectRequirement(3).humanReadableTypeName(), 'Requirement');
	var ticket = this.injectTask(4);
	ticket.json.type = 'fnord';
	equals(ticket.humanReadableTypeName(), 'Fnord');
	ticket.json.type = 'fnord foo';
	equals(ticket.humanReadableTypeName(), 'Fnord Foo');
});

test("can get empty array if a ticket has no parent", function() {
	var task = this.injectTask(1);
    equals(task.allParents().length, 0);
});

test("can get all the parents for a ticket", function() {
    var requirement1 = this.injectRequirement(1);
	var story1 = this.injectStory(2, requirement1);
	var task = this.injectTask(3, story1);

    var allParents = task.allParents();
    equals(allParents.length, 2);
    ok(_(allParents).include(requirement1));
    ok(_(allParents).include(story1));
});

test("can get all the parents for a ticket if it has multiple parents", function() {
	var story1 = this.injectStory(1);
	var story2 = this.injectStory(2);
	var task = this.injectTask(3, story1);
	task.json.incoming_links.push(2);
	story2.linkToChild(task);

    var allParents = task.allParents();
    equals(allParents.length, 2);
    ok(_(allParents).include(story1));
    ok(_(allParents).include(story2));
});

test("can get all the parents without duplicates for a ticket reaching the same parent multiple times", function() {
    var requirement1 = this.injectRequirement(4);
	var story1 = this.injectStory(1,requirement1);
	var story2 = this.injectStory(2,requirement1);
	var task = this.injectTask(3, story1);
	task.json.incoming_links.push(2);
	story2.linkToChild(task);

    var allParents = task.allParents();
    equals(allParents.length, 3);
});


module("a ticket can communicate with the server", {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.task = this.injectTask(1);
		
		addErrorCatchingArrayAndMethodsForBacklog(this, this.backlog);
	},
	teardown: function() {
		$.observer.removeObserver();
	}
});

test("tasks require that the json from the server has at least the structure {errors:[], current_data:{id:}}", function() {
	ok(this.task.isBadJSONStructure(null), "needs outer dictionary");
	ok(this.task.isBadJSONStructure({}), "needs errors current_data");
	ok(this.task.isBadJSONStructure({errors:null}), "needs errors current_data");
	ok(this.task.isBadJSONStructure({current_data:null}), "needs errors current_data");
	
	ok(this.task.isBadJSONStructure({errors:null, current_data:{}}), "needs arrays of errors");
	ok( ! this.task.isBadJSONStructure({errors:[], current_data:{}}), "this is valid");
	
	this.task.handleErrorFromServer(JSON.stringify(null));
	this.task.handleErrorFromServer(JSON.stringify({errors:null, current_data:{}}));
	equals(this.errors.length, 2);
	$(this.errors).each(function(index, message){
		ok(message.match(/bad structured data/), 'message is: '+message);
	});
	
	ok(this.task.isBadJSONTaskStructure({}), "needs to at least status and id");
	ok(this.task.isBadJSONTaskStructure({id:3}), "needs status");
	ok(this.task.isBadJSONTaskStructure({status:'fnord'}), "needs to at least contain id");
	
	this.errors = [];
	var oldJSON = this.task.copyJSON();
	this.task.handleErrorFromServer(JSON.stringify({errors:['fnord'], current_data:{}}));
	equals(this.errors.length, 1);
	equals(this.errors[0], 'fnord');
	same(this.task.json, oldJSON);
});

test("tasks can reset their content on a failed server call", function() {
	equals(this.task.json.status, 'new');
	var errorResponse = {errors:['unused'], current_data:{id:this.task.json.id, status:'closed'}};
	var responseText = JSON.stringify(errorResponse);
	this.task.handleErrorFromServer(responseText, 500);
	equals(this.task.json.status, 'closed');
});

test("tasks can show error messages on failed server call", function() {
	var responseText = JSON.stringify({errors:['first', 'second'], current_data:{id:this.task.json.id, status:'closed'}});
	this.task.handleErrorFromServer(responseText, 500);
	equals(this.errors.length, 1);
	equals(this.errors[0], 'first\nsecond');
});

test("tasks show error message if server is down (doesn't answer at all to server requests)", function() {
	this.task.handleErrorFromServer('', undefined);
	equals(this.errors.length, 1);
	ok((/is probably down/).test(this.errors[0]));
});

test("tasks can updates json on successful server call", function() {
	var json = this.task.copyJSON();
	json.fnord = 'fnord';
	this.task.handleSuccessFromServer(json, 'unused status');
	equals(this.task.json.fnord, 'fnord');
});

test("tasks don't die when borked json comes back from the server", function() {
	var json = this.task.copyJSON();
	this.task.handleErrorFromServer("something that doesn't scan as json }}}", 500);
	same(this.task.json, json);
	equals(this.errors.length, 1);
	ok(this.errors[0].match(/Server sent back unparseable data/));
});

test("tasks can reload json themselves", function() {
	expect(2);
	this.task.sendRequestToServer = function(httpMethod, url) {
		equals(httpMethod, 'GET');
		ok((new RegExp(this.task.json.id + '$')).test(url));
	}.bind(this);
	this.task.reloadFromServer();
});

test("when reloading a task will throw when it doesn't exist on the server", function() {
	expect(1);
	this.task.json.id = undefined;
	try { this.task.reloadFromServer(); }
	catch (exception) {
		ok((/Can't get a ticket that does not yet exist on the server/).test(exception));
	}
});

test("can give optional callback to submit functions", function() {
	// error callbacks will only happen if it was a recoverable error, i.e. the server sent back the correct json structure
	expect(4);
	var callback = function(source){ok(source === this.task);}.bind(this);
	var error_json = '{"errors":[], "current_data":{"id":1, "status":"new"}}';
	var success_json = {"id":1, "status":"new"};
	
	this.task.submitToServer(callback);
	this.task.handleSuccessFromServer(success_json, 'unused status');
	
	this.task.submitToServer(callback);
	this.task.handleErrorFromServer(error_json, 404);
	
	this.task.reloadFromServer(callback);
	this.task.handleSuccessFromServer(success_json, 'unused status');
	
	this.task.reloadFromServer(callback);
	this.task.handleErrorFromServer(error_json, 404);
});

test("optional callback can find out if callback was successful", function() {
	expect(2);
	var error_json = '{"errors":[], "current_data":{"id":1, "status":"new"}}';
	var success_json = {"id":1, "status":"new"};
	
	this.task.submitToServer(function(unused, wasSuccess){ok(wasSuccess);});
	this.task.handleSuccessFromServer(success_json, 'unused status');
	
	this.task.submitToServer(function(unused, wasSuccess){ok(!wasSuccess);});
	this.task.handleErrorFromServer(error_json, 404);
});



// REFACT: migrate to new notificatons api
test("can register for callbacks after each server-return", function() {
	var ticket = this.injectTask(1);
	var firstSensor = null;
	Ticket.registerCallbackAfterEachServerReturn(function(aTicket) { firstSensor = aTicket; });
	var secondSensor = null;
	Ticket.registerCallbackAfterEachServerReturn(function(aTicket) { secondSensor = aTicket; });
	ticket.handleSuccessFromServer(ticket.json);
	ok(firstSensor === ticket);
	ok(secondSensor === ticket);
	
	firstSensor = secondSensor = null;
	var error_json = '{"errors":[], "current_data":{"id":1, "status":"new"}}';
	ticket.handleErrorFromServer(error_json, 500);
	ok(firstSensor === ticket);
	ok(secondSensor === ticket);
});

test("can subscribe for changes on specific tickets", function() {
	expect(1);
	var firstTicket = this.injectTask(1);
	var secondTicket = this.injectTask(2);
	firstTicket.addObserver({}, function(aTicket) {
		same(aTicket.json, firstTicket.json);
	});
	firstTicket.postNotification();
	secondTicket.postNotification();
});

test("ticket will notify when json is changed", function() {
	var ticket = this.injectStory(1);
	ticket.addObserver({}, function(){ ok(true); });
	
	expect(3);
	ticket.setValueForKey('fnord', 'foo');
	var json = copyJSON(ticket.json);
	json.fnord = 'bar';
	ticket.setJSON(json);
	json = copyJSON(ticket.json);
	json.fnord = 'baz';
	ticket.updateJSON(json);
});

test("can remove observer of ticket", function() {
	expect(0);
	var ticket = this.injectStory(1);
	var observer = {};
	ticket.addObserver(observer, function(){ ok(false); });
	ticket.removeObserver(observer);
	ticket.postNotification();
});

test("setJSON will not trigger notification if nothing has changed", function() {
	expect(0);
	var ticket = this.injectStory(1);
	ticket.addObserver({}, function(){
		ok(false, 'should not call observer');
	});
	ticket.setJSON(ticket.json);
});

test("setJSON will not trigger notification on first set", function() {
	expect(0);
	var ticket = this.injectStory(1);
	var json = ticket.json;
	ticket.addObserver({}, function() {
		ok(false, 'should not call observer');
	});
	delete ticket.json;
	ticket.setJSON(json);
});


// TODO: move tests for existing query functionality from the whiteboard to here
