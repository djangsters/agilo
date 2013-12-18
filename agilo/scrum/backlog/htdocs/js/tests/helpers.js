function addBacklogAndTestDataCreationMethods(target){
	target.backlog = new Backlog();
	
	target.buildInfo = function() {
		var content = {
			type: "global", name: "aBacklog", sprint_or_release: "sprintName",
			types_to_show: ['requirement', 'story', 'bug', 'task'],
			configured_child_types: { 
				permitted_links_tree: {
					requirement: { story: []},
					story: { task: []},
					bug: { story: [], task: []},
					bug: { task: []}
				},
				configured_links_tree: {
					requirement: { story: []},
					story: { task: []},
					bug: { story: [], task: []},
					bug: { task: []}
				}
			}
		};
		var info = wrapContentInInfo(content);
		return info;
	};
	target.backlog.loader.setInfo(target.buildInfo());
	
	target.buildJSON = function(id, type) {
		return {
			id: id,
			type: type,
			status: 'new', // REFACT: should be new or in_progress at the start
			summary: type + ' #' + id,
			incoming_links: [],
			outgoing_links: [],
			sprint: '',
			
			can_edit: true
		};
	};
	
	target.linkChildToParent = function(child, parent) {
		child.json.incoming_links.push(parent.json.id);
		parent.json.outgoing_links.push(child.json.id);
	};
	
	target.addTicketWithJSON = function(json, optionalContainer) {
		var ticket = target.backlog.addTicketFromJSON(json);
		if (optionalContainer)
			target.linkChildToParent(ticket, optionalContainer);
		return ticket;
	};

	target.injectRequirement = function(id, optionalContainer) {
		var ticket = target.addTicketWithJSON(target.buildJSON(id, 'requirement'), optionalContainer);
		ticket.json.businessvalue = 300;
		return ticket;
	};
	target.injectUserStory = function(id, optionalContainer) {
		var story = target.addTicketWithJSON(target.buildJSON(id, 'story'), optionalContainer);
		story.json.priority = 'high or low';
		return story;
	};
	// Alias because I mistyped this so many times
	target.injectStory = target.injectUserStory;
	
	target.injectTask = function(id, optionalContainer) {
		var task = target.addTicketWithJSON(target.buildJSON(id, 'task'), optionalContainer);
		task.json.remaining_time = 23;
		return task;
	};
	
	target.injectBug = function(id, optionalContainer) {
		return target.addTicketWithJSON(target.buildJSON(id, 'bug'), optionalContainer);
	};
	
	target.injectTicket = function(id, overwriteJSON, optionalContainer) {
		var json = target.buildJSON(id, 'fnord');
		$.extend(json, overwriteJSON);
		return target.addTicketWithJSON(json, optionalContainer);
	};
	
	target.injectFixture = function(){
		this.requirement = this.injectRequirement(1);
		this.story1 = this.injectUserStory(2, this.requirement);
		this.task1 = this.injectTask(3, this.story1);

		this.story2 = this.injectUserStory(4, this.requirement);
		this.task2 = this.injectTask(5, this.story2);

		this.story3 = this.injectUserStory(6);
		this.task3 = this.injectTask(7, this.story3);
		this.originalOrder = [1,2,3,4,5,6,7];
	};
}

function addErrorCatchingArrayAndMethodsForBacklog(target, backlog) {
	// Catch error messages to make them testable
	target.errors = [];
	backlog.showError = function(someError) {
		target.errors.push(someError);
	};
	
	Ticket.prototype.showError = function(someError) {
			target.errors.push(someError);
	};
}

function wrapContentInInfo(content) {
	return {content: content,
		content_type: "backlog_info",
		permissions: []
	};
};

function equalArrays(actualArray, expectedArray) {
	// Arrays don't pose a problem, but if one of them is a jquery array...
	if ($.isFunction(actualArray.get))
		actualArray = actualArray.get();
	if ($.isFunction(expectedArray.get))
		expectedArray = expectedArray.get();
	
	same(actualArray, expectedArray);
}

function assertThrows(expectedErrorRegex, throwingCallable) {
	var actualException = null;
	try {
		throwingCallable();
	}
	catch(exception) {
		actualException = exception;
	}
	ok(actualException, "No exception was thrown");
	ok(expectedErrorRegex.test(actualException), "Expected exception <" + actualException + "> to match: <" + expectedErrorRegex + ">");
};

function assertMatches(actual, regex) {
	ok(RegExp(regex).test(actual), "Expected regex <" + regex + "> to match <" + actual + ">.");
}

/// simulate a drag to a target by selector
$.fn.simulateDrag = function(targetJQueryStringOrObject) {
	return this.simulate('drag', { dropTarget:targetJQueryStringOrObject});
};
