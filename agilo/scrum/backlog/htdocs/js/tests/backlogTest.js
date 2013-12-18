module("backlog model", {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		addErrorCatchingArrayAndMethodsForBacklog(this, this.backlog);
		window.BACKLOG_INFO = undefined;
		this.info = this.buildInfo();
		
		this.injectTaskWithTwoParents = function() {
			this.story1 = this.injectStory(1);
			this.story2 = this.injectStory(2);
			this.task = this.injectTask(3, this.story1);
			this.linkChildToParent(this.task, this.story2);
			return this.task;
		};
	},
	teardown: function(){
		$.observer.removeObserver();
	}
});

window.BACKLOG_INFO = undefined;

test("can load backlog synchronously from fixture", function() {
	expect(4);
	var story = this.buildJSON(1, 'story');
	this.backlog.loader.stubEverything();
	this.backlog.loader.setBacklogFixture([story]);
	
	equals(this.backlog.tickets().length, 0);
	this.backlog.loadFromServer(function(){ ok(true); });
	equals(this.backlog.tickets().length, 1);
	same(this.backlog.tickets()[0].json, story);
});

test("backlog instantiates a ticket object for each json", function() {
	var json = [{id:1}, {id:2}];
	this.backlog.setJSONForTickets(json);
	equals(this.backlog.tickets().length, 2);
	var firstTicket = this.backlog.tickets()[0];
	ok(firstTicket instanceof Ticket);
	equals(firstTicket.json.id, 1);
	var secondTicket = this.backlog.tickets()[1];
	ok(secondTicket instanceof Ticket);
	equals(secondTicket.json.id, 2);
});

test("can add new ticket from json anytime", function() {
	var json = this.buildJSON(1, 'task');
	equals(this.backlog.tickets().length, 0);
	var ticket = this.backlog.addTicketFromJSON(json);
	equals(this.backlog.tickets().length, 1);
	equals(this.backlog.tickets()[0].constructor, Ticket);
	ok(ticket === this.backlog.tickets()[0]);
});

test("creates back-link if adding a ticket from json with a parent-link", function() {
	var story = this.injectUserStory(1);
	var taskJSON = this.buildJSON(2, 'task');
	taskJSON.incoming_links.push(1);
	var task = this.backlog.addTicketFromJSON(taskJSON);
	equals(task.parents().length, 1);
	ok(story === task.parents()[0]);
	ok(story.hasChildrenWithoutMultiLink());
	equals(story.childrenWithoutMultiLink().length, 1);
	ok(task === story.childrenWithoutMultiLink()[0]);
	same(story.json.outgoing_links, [taskJSON.id]);
});

test("can create links to multiple parents when adding from json", function() {
	var story1 = this.injectStory(1);
	var story2 = this.injectStory(2);
	var taskJSON = this.buildJSON(3, 'task');
	taskJSON.incoming_links.push(1);
	taskJSON.incoming_links.push(2);
	
	var task = this.backlog.addTicketFromJSON(taskJSON);
	ok(story1.hasChild(task));
	ok(story2.hasChild(task));
});

test("shows configured top level types", function() {
	equals(this.backlog.topLevelContainers().length, 0);
	
	this.info.content.types_to_show = ['impediment', 'bug'];
	this.info.content.configured_child_types = { 
		configured_links_tree: {
			impediment: { bug: []},
			bug: {}
		}
	};
	this.backlog.loader.setInfo(this.info);
	var impediment = this.injectTicket(1, { type: 'impediment'});
	ok(impediment.isContainer());
	ok(impediment.isTopLevelContainer());
	
	var bug = this.injectBug(2);
	ok( ! bug.isContainer());
	equals(this.backlog.topLevelContainers().length, 1);
	equals(this.backlog.topLevelContainers()[0].json.type, 'impediment');
});

test("shows top level types even if they are linked by types that are not displayed", function() {
	this.info.content.types_to_show = ['requirement', 'story', 'task'];
	this.info.content.configured_child_types = { 
		configured_links_tree: {
			requirement: { story: []},
			story: { task: []}
		},
		permitted_links_tree: {
			requirement: { },
			story: { task: []}
		}
	};
	this.backlog.loader.setInfo(this.info);
	var requirement = this.injectTicket(1, { type: 'requirement'});
	ok(requirement.isContainer());
	ok(requirement.isTopLevelContainer());
	
	var story = this.injectStory(2, requirement);
	ok(story.isContainer());
	ok( ! story.isTopLevelContainer());
});

test("can update ticket from json", function() {
	var task = this.injectTask(1);
	var json = this.buildJSON(1, 'task');
	json.remaining_time = 200;
	equals(task.json.remaining_time, 23);
	var ticket = this.backlog.updateTicketFromJSON(json);
	equals(task.json.remaining_time, 200);
	ok(ticket === task);
});

test("can check backlog json for board constraints", function() {
	this.backlog.loader.stubEverything();
	this.backlog.loader.setBacklogFixture([{ remaining_time:0, outgoing_links:[1]}]);
	this.backlog.loadFromServer();
	var errors = this.backlog.checkJSONForBoardConstraints();
	equals(errors.length, 2);
	assertMatches(errors[0], /Found a ticket without an id/);
	assertMatches(errors[1], /is tasklike .* but still has children/);
});

// Handling unreferenced tasks ............................

test("can return all unreferenced tasks", function() {
	equals(this.backlog.hasUnreferencedTasks(), false);
	
	this.injectTask(123);
	this.injectTask(124);
	
	equals(this.backlog.hasUnreferencedTasks(), true);
	
	var unreferencedTasks = this.backlog.unreferencedTasks();
	equals(unreferencedTasks.length, 2);
	equals(unreferencedTasks[0].json.id, 123);
	equals(unreferencedTasks[1].json.id, 124);
});

test("each unreferenced task gets the fake story as parent", function() {
	var task = this.injectTask(123);
	this.backlog.addFakeStoryIfNecessary();
	equals(task.parents().length, 1);
	equals(task.parents()[0].json.id, -1);
});

test("unreferenced tasks will return in a surrogate top level container", function() {
	var firstTask = this.injectTask(1);
	var secondTask = this.injectTask(2);
	var surrogateContainer = this.backlog.topLevelContainers();
	equals(surrogateContainer.length, 1);
	equals(surrogateContainer[0].childrenWithoutMultiLink().length, 2);
	same(surrogateContainer[0].childrenWithoutMultiLink()[0].json, firstTask.json);
	same(surrogateContainer[0].childrenWithoutMultiLink()[1].json, secondTask.json);
});

test("when the fake story is first requested it stays (important for the whiteboard and the inline additor)", function() {
	var firstTask = this.injectTask(1);
	equals(this.backlog.tickets().length, 1);
	this.backlog.addFakeStoryIfNecessary();
	equals(this.backlog.tickets().length, 2);
});

test("can still access unreferenced tasks", function() {
	ok( ! this.backlog.hasUnreferencedTasks());
	var firstTask = this.injectTask(1);
	ok(this.backlog.hasUnreferencedTasks());
	equals(this.backlog.unreferencedTasks().length, 1);
	
	this.backlog.addFakeStoryIfNecessary();
	ok(this.backlog.hasUnreferencedTasks());
	equals(this.backlog.unreferencedTasks().length, 1);
});

test("adding unreferenced tasks adds them to the fake story if it is available", function() {
	var firstTask = this.injectTask(1);
	ok(this.backlog.hasUnreferencedTasks());
	this.backlog.addFakeStoryIfNecessary();
	equals(this.backlog.topLevelContainers()[0].childrenWithoutMultiLink().length, 1);
	equals(this.backlog.unreferencedTasks().length, 1);

	var secondTask = this.injectTask(2);
	ok(this.backlog.hasUnreferencedTasks());
	equals(this.backlog.topLevelContainers()[0].childrenWithoutMultiLink().length, 2);
	equals(this.backlog.unreferencedTasks().length, 2);
});

test("handles tasks as unreferenced when their parents are not in the backlog", function() {
	var task = this.injectTask(2);
	task.json.incoming_links = [1];
	ok(this.backlog.hasUnreferencedTasks());
	this.backlog.addFakeStoryIfNecessary();
	var fakeStory = this.backlog.fakeStory();
	equals(fakeStory.children().length, 1);
	equals(fakeStory.children()[0].parentWithoutMultilink().id(), -1);
});

test("throws in isTaskLike() if tasklike has children", function() {
	var task = this.injectTask(1);
	var child = this.injectTask(2, task);
	assertThrows(/is tasklike as it has 'remaining_time'/, function(){ task.isTaskLike(); });
});

test("fake story belongs to the current sprint", function() {
	this.injectTask(2);
	this.backlog.addFakeStoryIfNecessary();
	var fakeStory = this.backlog.fakeStory();
	ok(fakeStory);
	equals(fakeStory.json.sprint, this.backlog.loader.info().sprint_or_release);
});

// Navigating ticket relationships ............................

test("can get top level task containers", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	this.injectTask(3, story);
	
	equals(this.backlog.tickets().length, 3);
	equals(this.backlog.topLevelContainers().length, 1);
	equals(this.backlog.topLevelContainers()[0].id, requirement.id);
});

test("containerWithID can find an arbitrary container", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	this.injectTask(3, story);
	equals(this.backlog.tickets().length, 3);
	
	var foundStory = this.backlog.containerWithID(story.json.id);
	ok(foundStory);
	ok(foundStory === story);
});

test("can get tickets with specific id", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	this.injectTask(3, story);
	
	var foundStory = this.backlog.ticketWithID(story.json.id);
	ok(foundStory);
	equals(foundStory.json.id, story.json.id);
});

test("can get childs for container", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var story2 = this.injectUserStory(3, requirement);
	var task = this.injectTask(4, story);
	
	var foundChildren = this.backlog.childrenForContainerWithoutMultilink(requirement);
	equals(foundChildren.length, 2);
	equals(foundChildren[0].json.id, story.json.id);
	equals(foundChildren[1].json.id, story2.json.id);
	
	equals(this.backlog.childrenForContainerWithoutMultilink(story2).length, 0);
	
	var foundTasks = this.backlog.childrenForContainerWithoutMultilink(story);
	equals(foundTasks.length, 1);
	equals(foundTasks[0].json.id, task.json.id);
});

test("can get container from child", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var task = this.injectTask(4, story);
	
	equals(this.backlog.containerForChildWithoutMultilink(task).json.id, story.json.id);
	equals(this.backlog.containerForChildWithoutMultilink(story).json.id, requirement.json.id);
});

test("containerForChildWithoutMultilink returns null if no parents are found", function() {
	var requirement = this.injectRequirement(1);
	equals(this.backlog.containerForChildWithoutMultilink(requirement), null);
});

// Handling multiple parents ..........................................

test("containerForChildWithoutMultilink will return first parent if multiple parents are found", function() {
	this.injectTaskWithTwoParents();
	same(this.backlog.containerForChildWithoutMultilink(this.task).json, this.story1.json);
});

test("childrenForContainerWithoutMultilink will not return children that are already part of a different container", function() {
	this.injectTaskWithTwoParents();
	equals(this.backlog.childrenForContainerWithoutMultilink(this.story1).length, 1);
	same(this.backlog.childrenForContainerWithoutMultilink(this.story1)[0].json, this.task.json);
	equals(this.backlog.childrenForContainerWithoutMultilink(this.story2).length, 0);
});

test("can return all parents for a ticket", function() {
	this.injectTaskWithTwoParents();
	equals(this.backlog.containersForChild(this.task).length, 2);
	same(this.backlog.containersForChild(this.task)[0].json, this.story1.json);
	same(this.backlog.containersForChild(this.task)[1].json, this.story2.json);
});

test("ticket knows it has multiple parents", function() {
	this.injectTaskWithTwoParents();
	ok(this.task.hasMultipleParentLinks());
});

test("can return all childs for a container", function() {
	this.injectTaskWithTwoParents();
	equals(this.backlog.childrenForContainerWithoutMultilink(this.story2).length, 0);
	equals(this.backlog.childrenForContainer(this.story2).length, 1);
});

test("tickets can get their parents too", function() {
	this.injectTaskWithTwoParents();
	ok(this.task.hasMultipleParentLinks());
	ok(this.task.parents().length, 2);
});


// Navigating relationships ................................................

test("tickets can navigate parent->child relationships too", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var story2 = this.injectUserStory(3, requirement);
	var task = this.injectTask(4, story);
	
	ok(requirement.hasChildrenWithoutMultiLink());
	equals(requirement.childrenWithoutMultiLink().length, 2);
	equals(requirement.childrenWithoutMultiLink()[0].json.id, story.json.id);
	equals(requirement.childrenWithoutMultiLink()[1].json.id, story2.json.id);
	
	ok( ! story2.hasChildrenWithoutMultiLink());
	equals(story2.childrenWithoutMultiLink().length, 0);
	
	ok(story.hasChildrenWithoutMultiLink());
	equals(story.childrenWithoutMultiLink().length, 1);
	equals(story.childrenWithoutMultiLink()[0].json.id, task.json.id);
});

test("tickets can navigate child->parent relationships too", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var story2 = this.injectUserStory(3, requirement);
	var task = this.injectTask(4, story);
	
	ok( ! requirement.hasParents());
	ok(story.hasParents());
	equals(story.parents()[0].json.id, requirement.json.id);
	ok(story2.hasParents());
	equals(story2.parents()[0].json.id, requirement.json.id);
	ok(task.hasParents());
	equals(task.parents()[0].json.id, story.json.id);
});

test("backlog knows about errors that happened in the code", function() {
	equals(this.errors.length, 0);
	this.backlog.showError('fnord');
	same(this.errors, ['fnord']);
});

test("stories with incoming links are still top level items if their linkee is not part of the current backlog", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	// remove the requirement so the story has a dangling incomming link
	same(this.backlog.tickets()[0].json, requirement.json);
	this.backlog._tickets.splice(0,1);
	equals(this.backlog._tickets.length, 1);
	same(this.backlog._tickets[0].json, story.json);
	
	equals(this.backlog.topLevelContainers().length, 1);
	same(this.backlog.topLevelContainers()[0].json, story.json);
});

test("can compute totals for attribute", function() {
	var task1 = this.injectTask(2, this.injectUserStory(1));
	var task2 = this.injectTask(3);
	task1.json.foo = 2;
	task2.json.foo = 3;
	
	equals(this.backlog.computeTotal('foo'), 2+3);
});

test("computed total is 0 if one numeric value was found", function() {
	var task = this.injectTask();
	task.json.foo = 0;
	equals(this.backlog.computeTotal('foo'), 0);
});

test("computed total is empty string if no numeric value was found", function() {
	this.injectStory(1);
	equals(this.backlog.computeTotal('foo'), "");
});

test("converts strings to numbers before computing totals", function() {
	// in Trac there are no numeric custom fields so these are always 
	// transmitted to the JS as string
	var task1 = this.injectTask(1);
	var task2 = this.injectTask(2);
	task1.json.foo = '2';
	task2.json.foo = '5';
	
	equals(this.backlog.computeTotal('foo'), 2+5);
});

test("can use filter to include only specific items for totals", function() {
	var task1 = this.injectTask(1);
	var task2 = this.injectTask(2);
	task1.json.foo = 2;
	task2.json.foo = 5;
	
	var fakeFilter = {
		shouldShow: function(aTicket) { return aTicket.json.id === 1; }
	};
	equals(this.backlog.computeTotal('foo'), 2+5);
	equals(this.backlog.computeTotal('foo', fakeFilter), 2);
    equals(this.backlog.numberOfTicketsWithParentsMatchingFilter(fakeFilter), 1);
});


test("counts multi linked items only once when computing totals for attribute", function() {
	var task = this.injectTaskWithTwoParents();
	task.json.remaining_time = 12;
	
	equals(this.backlog.computeTotal('remaining_time'), 12);
});

test("counts up the number of backlog items", function() {
	var task1 = this.injectTask(1);
	var task2 = this.injectTask(2);
	equals(this.backlog.numberOfTicketsWithParentsMatchingFilter(), 2);
});

test("does not include the fake story when counting up the number of backlog items", function() {
	var task = this.injectTask(1);
    this.backlog.addFakeStoryIfNecessary();
	equals(this.backlog.numberOfTicketsWithParentsMatchingFilter(), 1);
});




// TODO: this should become a nested module which shares setup code - I always need a small backlog

// Ticket positioning ..........................................

test("can get all ticket-positions at once", function() {
	var story = this.injectUserStory(1);
	var task1 = this.injectTask(2, story);
	var task2 = this.injectTask(3, story);
	equalArrays(this.backlog.orderOfTickets(), [story.json.id, task1.json.id, task2.json.id]);
});

test("can move tickets around", function() {
	var story = this.injectUserStory(1);
	var task1 = this.injectTask(2, story);
	var task2 = this.injectTask(3, story);
	
	equalArrays(this.backlog.orderOfTickets(), [story.json.id, task1.json.id, task2.json.id]);
	this.backlog.moveTicketToPosition(task1.json.id, 0); // start
	equalArrays(this.backlog.orderOfTickets(), [task1.json.id, story.json.id, task2.json.id]);
});

test("can set all ticket positions at once", function() {
	var story = this.injectUserStory(1);
	var task1 = this.injectTask(2, story);
	var task2 = this.injectTask(3, story);
	
	var expectedOrder = [story.json.id, task1.json.id, task2.json.id];
	this.backlog.setOrderOfTickets(expectedOrder);
	equalArrays(this.backlog.orderOfTickets(), expectedOrder);
	expectedOrder = [task2.json.id, task1.json.id, story.json.id];
	this.backlog.setOrderOfTickets(expectedOrder);
	equalArrays(this.backlog.orderOfTickets(), expectedOrder);
});

test("doesn't throw if you try to set the position of a non-existing ticket", function() {
	// if you hide items from a backlog via the admin interface, it will 
	// still contain ordering information for stuff that is not anymore there
	this.backlog.moveTicketToPosition(31337, 234234);
});

test("will sort tickets without a position below the positioned tickets", function() {
	var story = this.injectUserStory(1);
	var task1 = this.injectTask(2, story);
	var task2 = this.injectTask(3, story);
	
	var expectedOrder = [task2.json.id, task1.json.id, story.json.id];
	this.backlog.setOrderOfTickets(expectedOrder);
	equalArrays(this.backlog.orderOfTickets(), expectedOrder);
	
	// this means that only the story gets a defined position, the rest is undefined (unchanged probably)
	this.backlog.setOrderOfTickets([story.json.id]);
	equalArrays(this.backlog.orderOfTickets(), [story.json.id, task2.json.id, task1.json.id]);
	// This will need to become more sophisticated when we want to support splits, i.e. render one
	// story for a requirement at the top and one at the bottom
});

test("subtickets are sorted correctly according to the sort criteria received", function() {
	var story = this.injectStory(1);
	var task1 = this.injectTask(2, story);
	var task2 = this.injectTask(3, story);
	this.backlog.setOrderOfTickets([1,3,2]);
	equals(story.childrenWithoutMultiLink()[0].json.id, 3);
	equals(story.childrenWithoutMultiLink()[1].json.id, 2);
});


// Filtering out unwanted types ............................

test("non accessible tickets are just moved to the end of the backlog on setOrderOfTickets", function() {
	// This should work as they are ignored anywhere anyhow
	// it means that when you toggle the visible types for a backlog it will not be nicely ordered
	// but we can attack that later on.
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var story2 = this.injectUserStory(3, requirement);
	this.backlog.accessibleTypes(["story"]);

	equalArrays([1,2,3], this.backlog.orderOfTickets());
	this.backlog.setOrderOfTickets([2,3]);
	equalArrays([2,3, 1], this.backlog.orderOfTickets());
});

test("can set types to show backlog", function() {
	same([], this.backlog.accessibleTypes());
	this.backlog.accessibleTypes(["fnord"]);
	same(["fnord"], this.backlog.accessibleTypes());
});

test("knows which types to filter", function() {
	ok( ! this.backlog.isFilteredType('fnord'));
	ok(this.backlog.isAccessibleType('fnord'));
	this.backlog.accessibleTypes(['fnord']);
	ok( ! this.backlog.isFilteredType('fnord'));
	ok(this.backlog.isAccessibleType('fnord'));
	this.backlog.accessibleTypes(['bar']);
	ok(this.backlog.isFilteredType('fnord'));
	ok( ! this.backlog.isAccessibleType('fnord'));
});

test("can filter out last link", function() {
	var story = this.injectUserStory(1);
	var task = this.injectTask(2, story);
	
	this.backlog.accessibleTypes(["story"]);
	equals(this.backlog.topLevelContainers().length, 1);
	equals(story.childrenWithoutMultiLink().length, 0);
});

test("can filter out top level elements", function() {
	var story = this.injectUserStory(1);
	var task = this.injectTask(2, story);
	this.backlog.accessibleTypes(["task"]);
	var topLevel = this.backlog.topLevelContainers();
	equals(topLevel.length, 1);
	equals(topLevel[0].json.id, -1, "fake story to host the task");
	equals(topLevel[0].childrenWithoutMultiLink().length, 1);
	equals(topLevel[0].childrenWithoutMultiLink()[0].json.id, 2);
});

test("can filter out requirements", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var task = this.injectTask(3, story);
	
	this.backlog.accessibleTypes(["story", "task"]);
	var topLevel = this.backlog.topLevelContainers();
	equals(topLevel.length, 1);
	equals(topLevel[0].json.id, story.json.id);
	equals(topLevel[0].childrenWithoutMultiLink().length, 1);
	equals(topLevel[0].childrenWithoutMultiLink()[0].json.id, task.json.id);
});

test("can filter out intermediate elements", function() {
	// Not really supported - doesn't break in a very bad way though
	// This behaves a bit strange - the task does have a story - 
	// that is filtered though, so it is seen as a top-level story, 
	// i.e. a task without story
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var task = this.injectTask(3, story);
	this.backlog.accessibleTypes(["requirement", "task"]);
	equals(this.backlog.topLevelContainers().length, 2);
	equals(this.backlog.topLevelContainers()[0].json.id, 1);
	equals(this.backlog.topLevelContainers()[1].json.id, -1);
});

test("can filter out unreferenced tasks correctly", function() {
	this.injectTask(1);
	
	this.backlog.accessibleTypes(["story"]);
	equals(this.backlog.topLevelContainers().length, 0);
});

// Filtering by json values ............................

test("can extract all possible values for a filter criteria from the backlog", function() {
	var ticket1 = this.injectRequirement(1);
	var ticket2 = this.injectUserStory(2);
	var ticket3 = this.injectTask(3);
	ticket1.json.fnord = 'foo';
	ticket2.json.fnord = 'bar';
	ticket3.json.fnord = 'bar';
	
	var criteria = this.backlog.possibleFilterCriteriaForAttribute('fnord');
	same(criteria, ['foo', 'bar']);
	
	var ticket4 = this.injectUserStory(4);
	ticket4.json.type = 'bug';
	this.injectUserStory(5); // so we are sure we have two of these
	// less stable - so maybe remove that later, but still interesting to see it working
	criteria = this.backlog.possibleFilterCriteriaForAttribute('type');
	// This test is problematic as it depends on the order of the result (which is not guaranteed to be stable)
	same(criteria, ['requirement', 'story', 'task', 'bug']);
});

test("extracting all values will remove empty values", function() {
	// that will be readded by the 'filter by' option which acts as the empty value
	var ticket1 = this.injectTask(1);
	var ticket2 = this.injectTask(2);
	ticket1.json.fnord = 'foo';
	ticket2.json.fnord = '';
	var criteria = this.backlog.possibleFilterCriteriaForAttribute('fnord');
	same(criteria, ['foo']);
});

// Merging new backlog data ...................................

test("merging can update existing tickets", function() {
	var task = this.injectTask(1);
	task.setValueForKey('remaining_time', 5);
	var json = copyJSON(task.json);
	json.remaining_time = 23;
	this.backlog.mergeUpdatedBacklogJSON([json]);
	equals(task.valueForKey('remaining_time'), 23);
});

test("merging can add tickets", function() {
	var story = this.injectStory(1);
	var newStoryJSON = this.buildJSON(2, 'story');
	var toPostProcess = this.backlog.mergeUpdatedBacklogJSON([story.json, newStoryJSON]);
	equals(this.backlog.tickets().length, 2);
	same(this.backlog.ticketWithID(2).json, newStoryJSON);
	equals(toPostProcess.added.length, 1);
});

test("merging can add ticket with childs", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	this.backlog._tickets = []; // clean out backlog again
	var toPostProcess = this.backlog.mergeUpdatedBacklogJSON([story.json, task.json]);
	equals(this.backlog.tickets().length, 2);
	var newStory = this.backlog.topLevelContainers()[0];
	equals(newStory.id(), 1);
	equals(newStory.children().length, 1);
	equals(newStory.children()[0].id(), 2);
	
	equals(toPostProcess.added.length, 2);
	equals(toPostProcess.added[0].id(), 1);
	equals(toPostProcess.added[1].id(), 2);
});

test("merging can remove tickets", function() {
	var task = this.injectTask(1);
	var toPostProcess = this.backlog.mergeUpdatedBacklogJSON([]);
	equals(this.backlog.tickets().length, 0);
	equals(toPostProcess.removed.length, 1);
	equals(toPostProcess.removed[0].id(), 1);
});

test("merging can add tickets at the correct position", function() {
	var story = this.injectStory(1);
	var story2 = this.injectStory(2);
	var story3 = this.injectStory(3);
	this.backlog.tickets().splice(1,1); // clean out second story
	equals(this.backlog.tickets().length, 2);
	this.backlog.mergeUpdatedBacklogJSON([story.json, story2.json, story3.json]);
	same(this.backlog.orderOfTickets(), [1,2,3]);
});


test("merging may change positions of existing tickets", function() {
	var story = this.injectStory(1);
	var story2 = this.injectStory(2);
	this.backlog.mergeUpdatedBacklogJSON([story2.json, story.json]);
	same(this.backlog.orderOfTickets(), [2, 1]);
});

test("merging may change positions of existing tickets when deletions and additions happen", function() {
	var story = this.injectStory(1);
	var story2 = this.injectStory(2);
	var story3 = this.injectStory(3);
	this.backlog.tickets().splice(1,1); // remove story 2
	this.backlog.mergeUpdatedBacklogJSON([story3.json, story2.json, story.json]);
	same(this.backlog.orderOfTickets(), [3,2,1]);
});

test("merging removal sends notification so view can update", function() {
	expect(1);
	var story = this.injectStory(1);
	story.addObserver({}, function(ticket, wasRemoval){ ok(wasRemoval, 'should be removed'); });
	this.backlog.mergeUpdatedBacklogJSON([]);
});

test("merging removal of story with remaining child tasks relinks them to the fake-story", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	this.backlog.mergeUpdatedBacklogJSON([task.json]);
	equals(this.backlog.tickets().length, 2, "task + fakestory");
	equals(this.backlog.tickets()[0].id(), 2);
	equals(this.backlog.tickets()[1].id(), -1);
	equals(this.backlog.tickets()[0].parents().length, 1);
	equals(this.backlog.tickets()[0].parents()[0].id(), -1);
});

test("merging add will send notification about added ticket", function() {
	expect(1);
	var storyJSON = this.buildJSON(1, 'story');
	this.backlog.addTicketAddingOrRemovingObserver(function(backlog, ticket, wasRemoved) {
		ok(false === wasRemoved, 'not undefined!');
	});
	this.backlog.mergeUpdatedBacklogJSON([storyJSON]);
});

test("merging can be triggered by triggering reload from server", function() {
	this.injectStory(1);
	this.backlog.loader.backlogLoader.setFixture([this.buildJSON(2, 'story')]);
	
	this.backlog.triggerUpdateFromServer();
	equals(this.backlog.tickets().length, 1);
	equals(this.backlog.tickets()[0].id(), 2);
});

test("merging will always retain the fake story at the end", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	var freeTask = this.injectTask(3);
	this.backlog.addFakeStoryIfNecessary();
	equals(this.backlog.topLevelContainers().length, 2);
	equals(this.backlog.topLevelContainers()[1].id(), -1);
	
	this.backlog.mergeUpdatedBacklogJSON([story.json, task.json, freeTask.json, this.buildJSON(4, 'story')]);
	var topLevelOrder = function() {
		return _(this.backlog.topLevelContainers()).map(function(ticket){ return ticket.id(); });
	}.bind(this);
	same(topLevelOrder(), [1,4,-1]);
});

test("merging will notify the view that the order of stories has changed", function() {
	expect(1);
	this.backlog.addSortingChangedObserver(function(aBacklog) {
		ok(aBacklog === this.backlog);
	}.bind(this));
	this.backlog.mergeUpdatedBacklogJSON([]);
});



// need position did change callback when positions are updated
// consider to trigger a full position save after such an update (to get correct board order of children)
