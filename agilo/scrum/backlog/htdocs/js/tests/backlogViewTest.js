module("simulating drag and drop", {
	setup: function(){
		this.dom = function(optionalSelector) {
			if (optionalSelector)
				return $('#test-container').find(optionalSelector);
			else
				return $('#test-container');
		};
	},
	teardown: function(){
//		this.dom()[0].innerHTML = '';
	}
});

test("can simulate drag from source selector to target selector", function() {
	this.dom().append('<dl><dt id="_1"/><dd id="_2"/></dl>');
	this.dom('dt, dd').each(function(index){
		$(this).text('foo ' + index);
	});
	var sortable = this.dom('dl').sortable({revert:false}); // revert for animation that helps debugging
	
	same(sortable.sortable('toArray'), ['_1', '_2']);
	this.dom('dt').simulateDrag('dd');
	same(sortable.sortable('toArray'), ['_2', '_1']);
	this.dom('dd').simulateDrag('dt');
	same(sortable.sortable('toArray'), ['_1', '_2']);
});




module("rendering the backlog", {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.view = new BacklogView();
		this.render = function(shouldAddToDom){
			var dom = $(this.view.htmlForBacklog(this.backlog));
			if (shouldAddToDom) {
				$('#test-container').append(dom);
				this.view.refreshTotallingRow();
			}
			return dom;
		};
		
		this.injectMultiLinkedTask = function() {
			this.story1 = this.injectStory(1);
			this.story2 = this.injectStory(2);
			this.task = this.injectTask(3, this.story1);
			this.task.json.incoming_links.push(2);
			this.story2.linkToChild(this.task);
		};
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = '';
	}
});

// Rendering columns ..................................................

test("can create simple row for backlog task", function() {
	var task = this.injectTask(1);
	var rendered = this.render().find('#ticketID-1');
	equals(rendered.find('.id').text(), task.json.id);
	equals(rendered.find('.summary').text(), task.json.summary);
	equals(rendered.find('.status').text(), task.json.status);
});

test("can create simple row for backlog story", function() {
	var story = this.injectUserStory(1);
	var rendered = this.render().find('#ticketID-1');
	equals(rendered.find('.id').text(), story.json.id);
	equals(rendered.find('.summary').text(), story.json.summary);
	equals(rendered.find('.status').text(), story.json.status);
});

test("makes id a link to the agilo ticket page", function() {
	var story = this.injectUserStory(1);
	var rendered = this.render().find('#ticketID-1');
	equals(rendered.find('.id a').length, 1);
	assertMatches(rendered.find('.id a').attr('href'), story.tracTicketLink());
	// equals(rendered.find('.summary a').length, 1);
	// assertMatches(rendered.find('.summary a').attr('href'), story.tracTicketLink());
});

test("check fake story has no visible link to ticket page", function() {
       this.backlog.addFakeStory();
       var rendered = this.render().find('#ticketID--1');
	   
       ok(rendered.find('.id a').is(':hidden'));
});

test("check non fake story has a visible link to ticket page", function() {
	   var story = this.injectStory(1);
	   var task = this.injectTask(2, story);
	
       var rendered = this.render(true).find('#ticketID-1');
       ok(rendered.find('.id a').is(':visible'));
});

test("does add ticket-status and type as namespaced css classes", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	story.json.status = 'new';
	task.json.status = 'closed';
	var rendered = this.render();
	ok(rendered.find('#ticketID-1').hasClass('tickettype-story'));
	ok(rendered.find('#ticketID-2').hasClass('tickettype-task'));
	ok(rendered.find('#ticketID-1').hasClass('ticketstatus-new'));
	ok(rendered.find('#ticketID-2').hasClass('ticketstatus-closed'));
});

test("escapes ticket status in css classes so we keep namespaces", function() {
    var story = this.injectStory(1);
    story.json.status = 'foo bar';
    var rendered = this.render();
    ok(rendered.find('#ticketID-1').hasClass('ticketstatus-foo-bar'));
});

test("escapes ticket type in css classes so we keep namespaces", function() {
    var ticket = this.injectTicket(1, {type: "foo bar baz"});
    var backlogInfo = this.buildInfo();
    backlogInfo.content.types_to_show = ["foo bar baz"];
    backlogInfo.content.configured_child_types.configured_links_tree = { 'foo bar baz': { task: []} };
    this.backlog.loader.setInfo(backlogInfo);
    var rendered = this.render();
    ok(rendered.find('#ticketID-1').hasClass('tickettype-foo-bar-baz'));
});

test("escapes ticket fields so they don't destroy the generated html", function() {
	var task = this.injectTask(1);
	task.json.summary = '<div id="fnord" />';
	var rendered = this.render().find('#ticketID-1');
	equals(0, rendered.find('#fnord').length);
});

test("empty backlog has no totalling row", function() {
	var rendered = this.render(true);
	equals(rendered.find('[id^=ticketID-]:visible').length, 0);
	equals(rendered.find('[id^=ticketID-]:hidden').length, 1);
});

test("totalling row is added when first item is added to the backlog", function() {
	this.injectStory(1);
	var rendered = this.render(true);
	var ticketViews = rendered.find('[id^=ticketID-]:visible');
	equals(ticketViews.length, 1+1);
	var totallingRow = $(ticketViews[1]);
	equals(totallingRow.find('.summary').text(), "Totals");
});


// Rendering multiple columns .........................................

test("can create html for story with tasks", function() {
	var story = this.injectUserStory(1);
	var task = this.injectTask(2, story);
	var task2 = this.injectTask(4, story);
	
	var rendered = this.render();
	var storyHTML = rendered.find('dl:first');
	equals(storyHTML.children().length, 3);
	equals(storyHTML.find('dt').length, 1);
	equals(storyHTML.find('dd').length, 2);
});

test("can create html for backlog with stories and tasks", function() {
	var story = this.injectUserStory(1);
	var task1 = this.injectTask(2, story);
	var task2 = this.injectTask(3, story);
	
	var story2 = this.injectUserStory(4);
	var task3 = this.injectTask(5, story2);
	var task4 = this.injectTask(6, story2);
	
	var rendered = this.render().children('dl');
	// +1 because of the totalling row
	equals(rendered.length, 2+1);
	equals(rendered.find('.id').eq(0).text(), story.json.id);
	equals(rendered.find('.id').eq(1).text(), task1.json.id);
	equals(rendered.find('.id').eq(2).text(), task2.json.id);
	equals(rendered.find('.id').eq(3).text(), story2.json.id);
	equals(rendered.find('.id').eq(4).text(), task3.json.id);
	equals(rendered.find('.id').eq(5).text(), task4.json.id);
});

test("can create html for three levels", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectUserStory(2, requirement);
	var task = this.injectTask(3, story);
	
	var rendered = this.render();
	equals(rendered.find('dt:first .id').text(), requirement.json.id);
	equals(rendered.find('dd:first > dl > dt .id').text(), story.json.id);
	equals(rendered.find('dd:first > dl > dd .id').text(), task.json.id);
});

test("dd and dt have the task id as id", function() {
	var story = this.injectUserStory(2);
	var task = this.injectTask(3, story);
	
	var rendered = this.render();
	equals(rendered.find('dt').attr('id'), 'ticketID-' + story.json.id);
	equals(rendered.find('dd').attr('id'), 'ticketID-' + task.json.id);
});

test("containers have the container class", function() {
	var requirement = this.injectRequirement(42);
	var story = this.injectUserStory(23);
	var task = this.injectTask(5);
	
	var rendered = this.render();
	ok(rendered.find('#ticketID-'+requirement.json.id).hasClass('container'));
	ok(rendered.find('#ticketID-'+story.json.id).hasClass('container'));
	ok( ! rendered.find('#ticketID-'+task.json.id).hasClass('container'));
});

test("can display status for containers", function() {
	var story = this.injectUserStory(23);
	var rendered = this.render();
	equals(rendered.find('[id$=23] .status').text(), story.json.status);
});

test("each top level item has it's own definition list", function() {
	var requirement = this.injectRequirement(42);
	var story = this.injectUserStory(23);
	
	var rendered = this.render();
	var requirementDOM = rendered.find('dl > dt#ticketID-' + requirement.json.id);
	equals(requirementDOM.length, 1);
	equals(requirementDOM.siblings().length, 0);
	
	var storyDOM = rendered.find('dl > dt#ticketID-' + story.json.id);
	equals(storyDOM.length, 1);
	equals(storyDOM.siblings().length, 0);
});

test("can render top level tasks in the fake story", function() {
	this.injectTask(23);
	this.injectTask(42);
	var rendered = this.render();
	
	equals(rendered.find('dt#ticketID--1').length, 1);
	equals(rendered.find('dd').length, 2);
});

test("each column gets it's level as a class", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	
	var rendered = this.render();
	ok(rendered.find('#ticketID-1').hasClass('level-1'));
	ok(rendered.find('#ticketID-2').hasClass('level-2'));
});


// Drag'n'drop ........................................................

test("can enable drag'n'drop on the backlog", function() {
	var story = this.injectUserStory(1);
	var task1 = this.injectTask(2, story);
	var task2 = this.injectTask(3, story);
	
	$('#test-container').append(this.render());
	ok( ! this.view.isDragAndDropEnabled());
	this.view.enableDragAndDrop();
	ok(this.view.isDragAndDropEnabled());
	
	// can also disable it...
	ok(this.view.isDragAndDropEnabled());
	this.view.disableDragAndDrop();
	ok( ! this.view.isDragAndDropEnabled());
});

test("can enable drag'n'drop to order tasks in stories", function() {
	var story = this.injectUserStory(1);
	var task1 = this.injectTask(2, story);
	var task2 = this.injectTask(3, story);
	
	$('#test-container').append(this.render());
	ok( ! this.view.isDragAndDropEnabled());
	this.view.enableDragAndDrop();
	ok(this.view.isDragAndDropEnabled());
	
	// can also disable it...
	ok(this.view.isDragAndDropEnabled());
	this.view.disableDragAndDrop();
	ok( ! this.view.isDragAndDropEnabled());
});

// Enabling / Disabling .................................................

test("can disable backlog", function() {
	var rendered = this.render(true);
	this.view.setIsEditable(false);
	ok(rendered.hasClass("disabled"), "The backlog has class '.disabled'");
	this.view.setIsEditable(true);
	ok( ! rendered.hasClass("disabled"), "The backlog has class '.disabled'");
});

test("can enable backlog", function() {
	var rendered = this.render(true);
	this.view.setIsEditable(true);
	ok(!rendered.hasClass("disabled"), "The backlog has no class '.disabled'");
	this.view.setIsEditable(false);
	ok(rendered.hasClass("disabled"), "The backlog has no class '.disabled'");
});

test("disabling backlog will also remove all inline editors", function() {
	this.injectTask(1);
	this.view.setConfiguredColumns(['id', 'remaining_time'], {});
	var rendered = this.render(true);
	this.view.setIsEditable(true);
	ok($('.backlog #ticketID-1 .remaining_time').data('events'));
	this.view.setIsEditable(false);
	ok( ! $('.backlog #ticketID-1 .remaining_time').data('events'));
});


// Configuring columns ................................................

test("renderer uses configured columns", function() {
	var task = this.injectTask(1);
	this.view.setConfiguredColumns(["id", "summary", "status"], {});
	var rendered = this.render();
	
	equals(rendered.find('#ticketID-1 > *').length, 3);
	var ticket = rendered.find('#ticketID-1');
	equals(ticket.find('.id').length, 1);
	equals(ticket.find('.summary').length, 1);
	equals(ticket.find('.status').length, 1);
	
	this.view.setConfiguredColumns(["id", "summary", "foo", "bar"], {});
	task.json.foo = "foo";
	task.json.bar = "bar";
	rendered = this.render();
	equals(rendered.find('#ticketID-1 > *').length, 4);
	ticket = rendered.find('#ticketID-1');
	equals(ticket.find('.foo').length, 1);
	equals(ticket.find('.foo').text(), "foo");
	equals(ticket.find('.bar').length, 1);
	equals(ticket.find('.bar').text(), "bar");
});

test("will render columns with null or undefined values as empty string", function() {
	this.view.setConfiguredColumns(["foo", "bar"], {});
	var task = this.injectTask(1);
	task.json.foo = null;
	task.json.bar = undefined;
	var rendered = this.render();
	
	equals(rendered.find('#ticketID-1 > *').length, 2);
	var ticket = rendered.find('#ticketID-1');
	equals(ticket.find('.foo').length, 1);
	equals(ticket.find('.foo').text(), "");
	equals(ticket.find('.bar').length, 1);
	equals(ticket.find('.bar').text(), "");
});

test("can select correct alternative column for ticket", function() {
	var ticket = this.injectStory(1);
	equals(this.view.keyForAlternativeColumnContent(ticket, 'fnord'), 'fnord', "always return single key");
	equals(this.view.keyForAlternativeColumnContent(ticket, ['fnord', 'foo']), 'fnord', "always return first key if no key is found");
	ticket.json.foo = 'foo';
	equals(this.view.keyForAlternativeColumnContent(ticket, ['foo', 'bar']), 'foo');
	equals(this.view.keyForAlternativeColumnContent(ticket, ['bar', 'foo']), 'foo');
});

test("will select total_number_of_tickets as alternative key for fake totalling ticket", function() {
	var ticket = this.injectTicket(-2);
	equals(this.view.keyForAlternativeColumnContent(ticket, 'id'), 'total_number_of_tickets');
});

test("can render columns with alternative values", function() {
	// nested arrays for alternative values
	this.view.setConfiguredColumns([["foo","bar"]], {});
	var foo = this.injectStory(1);
	foo.json.foo = 'foo';
	var baz = this.injectStory(2);
	baz.json.bar = 'bar';
	var bar = this.injectStory(3); // this one has neither
	var rendered = this.render();
	
	equals(rendered.find('#ticketID-1 > *').length, 1, 'one column');
	equals(rendered.find('#ticketID-2 > *').length, 1, 'one column');
	var fooTicket = rendered.find('#ticketID-1');
	equals(fooTicket.find('.foo').text(), "foo");
	var barTicket = rendered.find('#ticketID-2');
	equals(barTicket.find('.bar').text(), "bar");
});

test("class will also always all classes if multiple values are provided", function() {
	this.view.setConfiguredColumns([["foo","bar"]], { bar: 'bar' });
	var story = this.injectStory(1);
	story.json.bar = 'bar';
	var rendered = this.render();
	
	var header = rendered.filter('.backlog-header');
	equals(header.find('span').length, 1);
	equals(header.find('.foo').text(), 'bar');
	equals(header.find('.bar').text(), 'bar');
	equals(rendered.find('#ticketID-1 span').length, 1);
	equals(rendered.find('#ticketID-1 .foo').text(), 'bar');
	equals(rendered.find('#ticketID-1 .bar').text(), 'bar');
});

test("humanReadableColumnName copes with multiple possibilities", function() {
	this.view.setConfiguredColumns([['foo', 'bar']], {bar:'Bar'});
	equals(this.view.humanReadableColumnName(['foo', 'bar']), 'Bar');
});

test("renders a headline that names all the columns", function() {
	var rendered = $(this.view.headerToHTML());
	equals(rendered.attr('class'), "backlog-header");
	equals(rendered.children().length, this.view.configuredColumns.length);
	equals(rendered.find('.id').text(), "id");
	equals(rendered.find('.summary').text(), "summary");
	equals(rendered.find('.status').text(), "status");
	
	rendered = this.render();
	equals(rendered.filter('.backlog-header').length, 1);
});

test("renders headlines in human readable terms if available", function() {
	this.view.setConfiguredColumns(["foo", "bar"], {foo:'fnord'});
	var rendered = $(this.view.headerToHTML());
	
	equals(rendered.find('.foo').text(), "fnord");
	equals(rendered.find('.bar').text(), "bar");
});

test("can update all values from json after rendering", function() {
	var task = this.injectTask(1);
	this.render(true);
	var view = this.view.firstViewForTicket(task);
	
	equals(view.dom().find('.id').text(), 1);
	equals(view.dom().find('.summary').text(), task.json.summary);
	equals(view.dom().find('.status').text(), task.json.status);
	
	task.json.summary = "new summary";
	task.json.status = "new";
	view.updateFromTicket();
	equals(view.dom().find('.summary').text(), task.json.summary);
	equals(view.dom().find('.status').text(), task.json.status);
});

test("can update summary even if it has additional child elements (like an a which the pro inline editor adds)", function() {
	var additionalStuff = [
		'<div class=​"inlineEditorButtons">',
			'<a href=​"#" class=​"edit-inline" data=​"{ ticketID:​278}​">​edit​</a>',
		'</div>'
	].join('');
	var story = this.injectStory(1);
	var rendered = this.render(true).find('#ticketID-1');
	rendered.find('.summary').append(additionalStuff);
	equals(rendered.find('.summary a').length, 1);
	assertMatches(rendered.find('.summary').text(), 'story #1.edit'); // need the . to match some invisible thingy jquery inserts
	story.json.summary = 'fnord';
	this.view.firstViewForTicket(story).updateFromTicket();
	equals(rendered.find('.summary a').length, 1);
	assertMatches(rendered.find('.summary').text(), 'fnord.edit'); // need the . to match some invisible thingy jquery inserts
});

test("will not destroy ticket link when updating from json", function() {
	var task = this.injectTask(1);
	this.render(true);
	var view = this.view.firstViewForTicket(task);
	view.updateFromTicket();
	equals(view.dom().find('.id a').length, 1);
	equals(view.dom().find('.id').text(), '1');
	assertMatches(view.dom().find('.id a').attr('href'), 'ticket/1');
});

test("knows if all entries in a column are numbers", function() {
	var story = this.injectUserStory(1);
	var task = this.injectTask(2, story);
	story.json.allNumbers = task.json.allNumbers = 23;
	this.render();
	ok(this.view.isNumericColumn('allNumbers'));
	
	story.json.partiallyNumbers = 23;
	ok(this.view.isNumericColumn('partiallyNumbers'));
	
	story.json.notNumber = task.json.notNumber = 'fnord';
	ok( ! this.view.isNumericColumn('notNumber'));

	story.json.partialNotNumber = 'fnord';
	ok( ! this.view.isNumericColumn('partialNotNumber'));
});

test("knows all entries are numeric even if alternative column content is used", function() {
	this.view.setConfiguredColumns([['foo', 'bar']], {});
	var story = this.injectUserStory(1);
	var task = this.injectTask(2, story);
	story.json.foo = story.json.bar = 1;
	this.render();
	ok(this.view.isNumericColumn(['foo', 'bar']));
});

test("columns with all numbers get .numeric class", function() {
	var story = this.injectUserStory(1);
	var task = this.injectTask(2, story);
	story.json.allNumbers = task.json.allNumbers = 23;
	this.view.setConfiguredColumns(['allNumbers'], {});
	var rendered = this.render();
	
	ok(rendered.find('#ticketID-1 .allNumbers').hasClass('.numeric'));
});

test("if no backlog is set, rendering will just make all columns non numeric", function() {
	var ticket = this.injectUserStory(1);
	var rendered = this.render().find('#ticketID-1');
	equals(rendered.attr('id'), 'ticketID-1');
});

test("totalling row can display total remaining time", function() {
	this.view.setConfiguredColumns(['id', 'summary', 'remaining_time'], {});
	var task = this.injectTask(1);
	task.json.remaining_time = 21;
	
	var totallingRow = this.render().find('[id^=ticketID-]:last');
	equals(totallingRow.find('.summary').text(), "Totals");
	equals(totallingRow.find('.remaining_time').text(), '21');
});

test("totalling row can display totals for all numeric columns even when alternative columns are specified", function() {
	this.view.setConfiguredColumns(['id', 'summary', ['actual_time', 'remaining_time'], 'sprint'], {});
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	// can't sum the sprint field even if one is just a number
	story.json.sprint = '1';
	task.json.sprint = 'A Sprint';
	task.json.actual_time = '11';
	
	var totallingRow = this.render().find('[id^=ticketID-]:last');
	equals(totallingRow.find('.actual_time').text(), 11);
	equals(totallingRow.find('.sprint').text(), '');
});

test("totalling row can count tickets", function() {
	this.view.setConfiguredColumns(['id', 'summary'], {});
    var task1 = this.injectTask(2);
    var task2 = this.injectTask(3);
    var task3 = this.injectTask(4);

	var totallingRow = this.render(true).find('[id^=ticketID-]:last');
    var ticket_count_dom = totallingRow.find('.id');
    ok( ! ticket_count_dom.is('has(a)'));
    ok(ticket_count_dom.is(':visible'));
	equals(totallingRow.find('.id').text(), '3');
});

test("fake ticket includes total number of tickets", function() {
    var task1 = this.injectTask(2);
    var task2 = this.injectTask(3);

    this.view.setBacklog(this.backlog);
    var fakeTicket = this.view.fakeTicketForTotallingRow();
    ok(fakeTicket.hasKey('total_number_of_tickets'));
    equals(fakeTicket.valueForKey('total_number_of_tickets'), 2);
});


// Have other objects participate in rendering .......................................................

test("can register callback for column rendering", function() {
	expect(8);
	var story = this.injectUserStory(1);
	this.view.setConfiguredColumns(['foo', 'bar'], {});
	this.view.registerCallbackForColumnRendering(function(ticket, columnIDName) {
		if (1 === ticket.json.id)
			ok(ticket === story , 'story');
		ok(-1 !== $.inArray(columnIDName, ['foo', 'bar']), 'inArray');
	});
	this.render();
});

test("html added via callbacks is enclosed in div to group it", function() {
	var task = this.injectUserStory(1);
	this.view.setConfiguredColumns(['foo'], {});
	this.view.registerCallbackForColumnRendering(function(ticket, columnIDName) {
		return '<div id="foo" />';
	});
	// totalling row also might have buttons
	equals(this.render().find('dl:first .inlineEditorButtons #foo').length, 1);
});

test("container not there if callbacks return nothing or are not there", function() {
	var task = this.injectUserStory(1);
	this.view.setConfiguredColumns(['foo'], {});
	equals(this.render().find('.inlineEditorButtons').length, 0);
});

// Adding new ticket views after rendering the backlog ................................................

test("can add subview for new ticket after rendering", function() {
	var story = this.injectUserStory(1);
	var rendered = this.render(true);
	
	var task = this.injectTask(2, story);
	var taskView = new LeafView(this.view, task);
	var storyView = this.view.firstViewForTicket(story);
	
	equals(storyView.subviews.length, 0);
	equals(taskView.dom().length, 0);
	storyView.addSubView(taskView);
	equals(storyView.subviews.length, 1);
	equals(taskView.dom().length, 1);
});

test("can add new container views to superviews", function() {
	var requirement = this.injectRequirement(1);
	var rendered = this.render(true);
	
	var story = this.injectUserStory(2, requirement);
	var requirementView = this.view.firstViewForTicket(requirement);
	var storyView = new ContainerView(this.view, story);
	
	equals(requirementView.dom().next().length, 0);
	requirementView.addSubView(storyView);
	ok(requirementView.dom().next().is('dd.childcontainer'));
	equals(rendered.find('.childcontainer > dl > dt#ticketID-2').length, 1);
});

test("can add container after all children of an existing container", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectStory(2, requirement);
	var task = this.injectTask(3, story);
	var rendered = this.render(true);
	
	var newStory = this.injectStory(4, requirement);
	var newStoryView = new ContainerView(this.view, newStory);
	var requirementView = this.view.firstViewForTicket(requirement);
	equals(requirementView.dom().siblings().length, 1);
	requirementView.addSubView(newStoryView);
	equals(requirementView.dom().siblings().length, 2);
	
	
});


test("new subviews are added after all existing subviews (both in .subviews and in the dom)", function() {
	var story = this.injectUserStory(1);
	var firstTask = this.injectTask(2, story);
	var rendered = this.render(true);
	
	var secondTask = this.injectTask(3, story);
	var firstTaskView = this.view.firstViewForTicket(firstTask);
	var secondTaskView = new LeafView(this.view, secondTask);
	var storyView = this.view.firstViewForTicket(story);
	
	storyView.addSubView(secondTaskView);
	equals($.inArray(firstTaskView, storyView.subviews), 0);
	equals($.inArray(secondTaskView, storyView.subviews), 1);
	
	var ticketViews = rendered.find('[id^=ticketID-]');
	equals(ticketViews.eq(0).attr('id'), 'ticketID-1');
	equals(ticketViews.eq(1).attr('id'), 'ticketID-2');
	equals(ticketViews.eq(2).attr('id'), 'ticketID-3');
});



test("can tell the view to render a new task at the right position", function() {
	var story = this.injectUserStory(1);
	var firstTask = this.injectTask(2, story);
	var rendered = this.render(true);
	
	var secondTask = this.injectTask(3, story);
	equals(rendered.find('dl > dd#ticketID-3').length, 0);
	this.view.addNewTicket(secondTask);
	equals(rendered.find('dl > dd#ticketID-3').length, 1);
});

test("can tell the view to render a new container", function() {
	var requirement = this.injectRequirement(1);
	var rendered = this.render(true);
	
	var story = this.injectUserStory(2, requirement);
	equals(rendered.find('.childcontainer > dl > dt#ticketID-2').length, 0);
	this.view.addNewTicket(story);
	equals(rendered.find('.childcontainer > dl > dt#ticketID-2').length, 1);
});

test("views register for ticket change notifications for their ticket", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	this.render(true);
	var dom = this.view.firstViewForTicket(story).dom();
	ok( ! (/fnord/).test(dom.text()));
	story.setValueForKey('fnord', 'summary');
	ok((/fnord/).test(dom.text()));
	
	dom = this.view.firstViewForTicket(task).dom();
	ok( ! (/fnord/).test(dom.text()));
	task.setValueForKey('fnord', 'summary');
	ok((/fnord/).test(dom.text()));
});

// tickets with multiple parents ...............................................

test("can create view hierarchy for tasks linked to multiple stories", function() {
	this.injectMultiLinkedTask();
	var views = this.view.createViewHierarchy(this.backlog.topLevelContainers());
	equals(views.length, 2);
	equals(views[0].subviews.length, 1);
	equals(views[1].subviews.length, 1);
});

test("tickets rendered multiple times are tagged as .multi-linked-item", function() {
	this.injectMultiLinkedTask();
	var rendered = this.render();
	ok(rendered.find('dl:first dd').hasClass('multi-linked-item'));
	ok(rendered.find('dl:eq(1) dd').hasClass('multi-linked-item'));
});

test("each multi linked item has a unique id to access by", function() {
	// ticketID-1 ticketID-1-1
	this.injectMultiLinkedTask();
	var rendered = this.render();
	var views = this.view.subviews;
	equals(views[0].subviews[0].idSelector(), 'ticketID-3');
	equals(views[1].subviews[0].idSelector(), 'ticketID-3-1');
});

test("can render tasks linked to multiple stories", function() {
	this.injectMultiLinkedTask();
	var rendered = this.render();
	// +1 is totalling row
	equals(rendered.find('dl').length, 2+1);
	equals(rendered.find('dl:first dd').attr('id'), 'ticketID-3');
	equals(rendered.find('dl:eq(1) dd').attr('id'), 'ticketID-3-1');
});

test("will also render tasks as multilinked if only one of their parents is in the sprint", function() {
	var task = this.injectTask(2, this.injectStory(1));
	task.json.incoming_links.push(3);
	ok(this.render().find('#ticketID-2').hasClass('multi-linked-item'));
});


test("can render stories and requirements as multilinked", function() {
	var story = this.injectStory(2, this.injectRequirement(1));
	story.json.incoming_links.push(3);
	ok(this.render(true).find('#ticketID-2').hasClass('multi-linked-item'));
});


// navigating view parent / child relationships ........................................

test("can navigate to children", function() {
	this.injectMultiLinkedTask();
	this.render();
	var views = this.view.subviews;
	equals(views[0].subviews[0].idSelector(), 'ticketID-3');
	equals(views[1].subviews[0].idSelector(), 'ticketID-3-1');
});

test("can navigate to parents", function() {
	this.injectMultiLinkedTask();
	var rendered = this.render();
	var views = this.view.subviews;
	ok(views[0].subviews[0].superview() === views[0]);
});



// each view can still access it's dom element (ids need to be unique)
// TODO: view for task could return multiple times
// TODO: look over complete backlogView api to see what needs to be changed




module("drag and drop tests", { //  that I don't want to write as acceptance tests
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.controller = new BacklogController();
		this.controller.model = this.backlog;
		this.view = this.controller.view;
		this.backlog.loader.sendPositionsUpdateToServer = function(){};
		
		this.render = function(){
			var dom = $(this.view.htmlForBacklog(this.backlog));
			$('#test-container').append(dom);
			this.view.enableDragAndDrop();
			// delay is in place to help distinguish between inline editing and dragging
			$('.backlog').sortable('option', 'delay', 0);
			$('.backlog dl').sortable('option', 'delay', 0);
			return dom;
		};
		this.domFor = function(aTicket){
			return $('#ticketID-' + aTicket.json.id);
		};
		
		this.injectFixture();
		this.render();
		// Workaround for the problem that the area where the tests are executed may scroll out of visibility
		// which makes the scrolling offsets wrong
		$('.backlog').css({top:0, position: 'absolute', backgroundColor: 'white'});
		same(this.view.orderOfTickets(), this.originalOrder);
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = '';
	}
});

// Checking only the order is actually not good enough, because some situations lead to
// the dom nesting being wrong, while still the order is correct. So think about a better way to verify this...

test("sends position update to backend on drop (and also updates child positions on drop)", function() {
	this.domFor(this.story1).simulateDrag(this.domFor(this.task2));
	equalArrays(this.backlog.orderOfTickets(), [1,4,5,2,3,6,7]);
});

test("can reorder whole requirement at once", function() {
	this.domFor(this.requirement).simulateDrag(this.domFor(this.task3));
	same(this.view.orderOfTickets(), [6,7,1,2,3,4,5]);
	
});

test("can't nest top level items accidentally ", function() {
	this.domFor(this.story3).simulateDrag(this.domFor(this.story2));
	same(this.view.orderOfTickets(), this.originalOrder);
});

test("can't nest stories in requirement in other stories", function() {
	/* prevent nesting that would be
	req
		us1
			us2
				t2
			t1
	...
	*/
	this.domFor(this.story1).simulateDrag(this.domFor(this.task2));
	same(this.view.orderOfTickets(), [1,4,5,2,3,6,7]);
	
	/*
	This test fails when the browser window is too small (i.e. when too many tests are executed before it).
	To reproduce the problem when the test is run individually - just make the window small enough.
	
	We (MH & FS) have traced the problem to this:
	jquery-ui simulate does not work correctly if the browser window scrolls
	when the drag starts. This is due to the placeholder being much smaller 
	than the dragged elements which makes jquery calculate the overlap incorrectly
	This might have something to do with bug: http://dev.jqueryui.com/ticket/4990
	However I don't quite understand how they interact.
	*/
});



module("inline editing tests", {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.view = new BacklogView();
		this.view.setConfiguredColumns(['id', 'remaining_time', 'sprint', 'businessvalue', 'rd_points', 'calculated_fnord'], {});
		this.view.ticketFieldOptionGenerator.setBacklogInfo({ticket_fields: {
			businessvalue: {
				optional: true,
				options: ['300', '800']
			},
			calculated_fnord: {is_calculated: true}
		}});
		this.render = function(){
			var dom = $(this.view.htmlForBacklog(this.backlog));
			$('#test-container').html(dom);
			return dom;
		};
		this.domFor = function(aTicket){
			return $('#ticketID-' + aTicket.json.id);
		};
		this.isEditorActiveFor = function(aTicket, fieldClass) {
			return !! this.domFor(aTicket).find(fieldClass).data('events');
		};
		this.isRemainingTimeEditorActiveFor = function(aTicket) {
			return this.isEditorActiveFor(aTicket, '.remaining_time');
		};
		this.isSprintEditorActiveFor = function(aTicket) {
			return this.isEditorActiveFor(aTicket, '.sprint');
		};
		// REFACT: consider moving this to the addBacklog... methods
		this.sprintListFixture = [{"options":[["SprintWithoutTeam",false],["Sprint with Empty Team",false],["Sprint",false],["Short Sprint",false],["Initial Commitment Test",false]],"label":"Running (by Start Date)"},{"options":[],"label":"To Start (by Start Date)"},{"options":[["Entirely different",false],["Sprint #2",false],["Closed Sprint",false]],"label":"Closed (by End Date)"}];
		
		this.backlog.loader.sprintListLoader.json = this.sprintListFixture;
		this.backlog.registerErrorSink(function(){});
		this.injectFixture();
		this.render();
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = '';
	}
});

test("can enable inline editing of tickets", function() {
	ok( ! this.isRemainingTimeEditorActiveFor(this.task1));
	ok( ! this.isSprintEditorActiveFor(this.story1));
	this.view.enableInlineEditing();
	ok(this.isRemainingTimeEditorActiveFor(this.task1));
	ok(this.isSprintEditorActiveFor(this.story1));
});

test("will only add inline editor to rows that have a remaining time", function() {
	this.view.enableInlineEditing();
	ok( ! this.isRemainingTimeEditorActiveFor(this.requirement));
});

test("will only add inline editor to rows that have a sprint column", function() {
	this.view.enableInlineEditing();
	ok(this.isSprintEditorActiveFor(this.requirement));
	ok(this.isSprintEditorActiveFor(this.story1));
	ok(this.isSprintEditorActiveFor(this.task1));
});

test("can make alternative columns editable", function() {
	this.view.setConfiguredColumns([ ["remaining_time", "total_remaining_time"], 'sprint'], {});
	ok( ! this.isRemainingTimeEditorActiveFor(this.task1));
	this.view.enableInlineEditing();
	ok(this.isRemainingTimeEditorActiveFor(this.task1));
});

test("will not make id field editable", function() {
	ok( ! this.isEditorActiveFor(this.task1, '.id'));
	this.view.enableInlineEditing();
	ok( ! this.isEditorActiveFor(this.task1, '.id'));
});

test("will not make calculated field editable", function() {
	this.task1.json.calculated_fnord = '3';
	ok( ! this.isEditorActiveFor(this.task1, '.calculated_fnord'));
	this.view.enableInlineEditing();
	ok( ! this.isEditorActiveFor(this.task1, '.calculated_fnord'));
});

test("tasks with an empty remaining time (not yet set) still get the inline editor", function() {
	this.task1.json.remaining_time = '';
	this.render();
	this.view.enableInlineEditing();
	ok(this.isRemainingTimeEditorActiveFor(this.task1));
});

test("can show correct value by default in popup for business value", function() {
	// TODO: sometimes this test fails - with strange values for the val() - find out why this is and where they come from
	this.view.enableInlineEditing();
	var view = this.view.firstViewForTicket(this.requirement);
	var actual = view.dom('.businessvalue').click().find(':input').val();
	equals(actual, this.requirement.json.businessvalue);
});

test("will send changed method to backend for submitting to the server", function() {
	expect(1);
	this.task1.submitToServer = function() {ok(true);};
	var view = this.view.firstViewForTicket(this.task1);
	view.didEndInlineEditForField(2, 'remaining_time');
});

test("will revert value if submit to server was not successful", function() {
	var json = copyJSON(this.task1.json);
	var view = this.view.firstViewForTicket(this.task1);
	view.didEndInlineEditForField(1000, 'remaining_time');
	equals(view.dom('.remaining_time').text(), '1000');
	
	this.task1.handleErrorFromServer(JSON.stringify({errors:[], current_data:json}));
	equals(view.dom().find('.remaining_time').text(), '23');
});

test("does not submit to server if nothing has changed", function() {
	expect(0);
	this.view.enableInlineEditing();
	var view = this.view.firstViewForTicket(this.task1);
	this.task1.submitToServer = function(){ ok(false); };
	
	view.dom('.remaining_time')
		.click()
		.find(':input').val(this.task1.json.remaining_time)
			.submit();
	
});

test("will only enable inline editing for remaining time if task has can_edit attribute", function() {
	this.task1.json.can_edit = true;
	this.task2.json.can_edit = false;
	this.task3.json.can_edit = undefined;
	// task3 is left undefined to make the code deal with that and fall back gracefully
	
	ok( ! this.isRemainingTimeEditorActiveFor(this.task1));
	ok( ! this.isRemainingTimeEditorActiveFor(this.task2));
	ok( ! this.isRemainingTimeEditorActiveFor(this.task3));
	
	this.view.enableInlineEditing();
	
	ok(this.isRemainingTimeEditorActiveFor(this.task1));
	ok( ! this.isRemainingTimeEditorActiveFor(this.task2));
	ok( ! this.isRemainingTimeEditorActiveFor(this.task3));
	
});

test("can set the value to empty with inline editor", function() {
	expect(2);
	this.view.enableInlineEditing();
	var view = this.view.firstViewForTicket(this.task1);
	view.didEndInlineEditForField = function(newValue, field){
		equals(newValue, '');
		equals(field, 'remaining_time');
		return newValue;
	};
	view.dom('.remaining_time')
		.click()
		.find(':input').val('')
			.submit();
});

test("will show inline editor on click and hide (submit) it when it looses focus", function() {
	this.view.enableInlineEditing();
	var view = this.view.firstViewForTicket(this.task1);
	var inlineEditor = function() { return view.dom('.sprint :input'); };
	var isInlineEditorVisible = function() { return inlineEditor().length == 1; };
	
	ok(! isInlineEditorVisible());
	view.dom('.sprint').click();
	ok(isInlineEditorVisible());
	inlineEditor().mouseleave();
	ok(isInlineEditorVisible(), 'inline editor must be visible');
	inlineEditor().blur();
	ok(! isInlineEditorVisible(), 'inline editor must be hidden');
});

test("will show inline editing possibility on mouseenter and hide it on mouse leave", function() {
	this.view.enableInlineEditing();
	var view = this.view.firstViewForTicket(this.task1);
	var isShownAsEditable = function() { return view.dom('.sprint').hasClass('inlineEditable'); };
	
	ok(! isShownAsEditable());
	ok(view.dom('.sprint').length == 1);
	view.dom('.sprint').mouseover();
	ok(isShownAsEditable());
	view.dom('.sprint').mouseout();
	ok(! isShownAsEditable());
});

test("view can validate and reject empty strings", function() {
	// TODO: need to allow empty strings
	var view = new View();
	equals(view.stringNormalizingParser('fnord'), 'fnord');
	equals(view.stringNormalizingParser(' bar '), ' bar ');
	equals(view.stringNormalizingParser(''), '');
	equals(view.stringNormalizingParser('    '), '');
});

test("does show 'please select' as first item in all selects", function() {
	this.view.enableInlineEditing();
	var view = this.view.firstViewForTicket(this.requirement);
	var actual = view.dom('.businessvalue').click().find(':input option:first').text();
	equals(actual, 'Please select:');
});

test("does submit if changing between 0 and '' as value", function() {
	expect(6);
	this.story1.json.rd_points = 10;
	this.render();
	this.view.enableInlineEditing();
	var view = this.view.firstViewForTicket(this.story1);
	this.story1.submitToServer = function(callback) { 
		ok(true); 
		callback();
	}.bind(this); 
	equals(view.dom('.rd_points').click().find(':input').val(), 10);
	view.dom('.rd_points').click().find(':input').val('').submit();
	view.dom('.rd_points').click().find(':input').val(0).submit();
	view.dom('.rd_points').click().find(':input').val('').submit();
	view.dom('.rd_points').click().find(':input').val('0').submit();
	view.dom('.rd_points').click().find(':input').val('').submit();
});

test("will enable inline editing on newly appended tasks", function() {
	this.view.enableInlineEditing();
	ok(this.isSprintEditorActiveFor(this.requirement));
	
	var story = this.injectUserStory(23, this.requirement);
	this.view.addNewTicket(story);
	ok(this.isSprintEditorActiveFor(story));
});

test("will move extra dom nodes to the side during inline editing", function() {
	$('#ticketID-1 .sprint').append('<div id="fnord">fnordfoo</div>');
	this.view.enableInlineEditing();
	var view = this.view.firstViewForTicket(this.requirement);
	view.didEndInlineEditForField = function(identity) { return identity; };
	var input = $('#ticketID-1 .sprint').click().find(':input');
	equals(input.val(), '');
	input.val('foo').blur();
	equals($('#ticketID-1 .sprint #fnord').length, 1);
});

test("does not share extraDOMNodes storage between instances", function() {
	var view1 = this.view.firstViewForTicket(this.task1);
	var view2 = this.view.firstViewForTicket(this.story1);
	var view3 = this.view.firstViewForTicket(this.task2);
	view1.extraDOMNodes.fnord = 'fnord';
	ok( ! ('fnord' in view2.extraDOMNodes));
	ok( ! ('fnord' in view3.extraDOMNodes));
});

test("can make text in input selectable", function() {
	this.view.setConfiguredColumns(['summary'], {});
	this.render();
	this.view.enableInlineEditing();
	this.controller = new BacklogController();
	this.view.setController(this.controller);
	this.controller.disableSelectionOfSummaryField();
	
	var summary1 = $('#ticketID-1 .summary');
	equals(summary1.attr('unselectable'), 'on');
	summary1.click();
	equals(summary1.attr('unselectable'), 'off');
	summary1.find('input').blur();
	equals(summary1.attr('unselectable'), 'on');
});

// existing dom element should not be visible in editor




module("backlog inline editor option generator", {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.generator = new TicketFieldOptionGenerator();
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = '';
	}
});

test("can set ticket_fields from backlog_info", function() {
	same(this.generator.ticketFields, {});
	this.generator.setBacklogInfo({
		ticket_fields: 'fnord'
	});
	same(this.generator.ticketFields, 'fnord');
});

test("can check which fields are select-like", function() {
	this.generator.setBacklogInfo({
		ticket_fields: {
			select_field: {options: ['a', 'b']},
			empty_field: {options: []},
			text_field: {}
		}
	});
	same(this.generator.isSelectLikeField('select_field'), true);
	same(this.generator.isSelectLikeField('empty_field'), true);
	same(this.generator.isSelectLikeField('text_field'), false);
	same(this.generator.isSelectLikeField('unknown_field'), undefined);
});

test("can retrieve options from a field", function() {
	this.generator.setBacklogInfo({
		ticket_fields: {
			select_field: {options: ['a', 'b']},
			empty_field: {options: []},
			text_field: {}
		}
	});
	same(this.generator.optionsForField('select_field'), ['a', 'b']);
	same(this.generator.optionsForField('empty_field'), []);
	same(this.generator.optionsForField('text_field'), undefined);
});

test("can generate editor select_options", function() {
	this.generator.setBacklogInfo({
		ticket_fields: {
			first_non_optional: {options: ['a', 'b']},
			second_non_optional: {optional: false, options: ['a', 'b']},
			optional: {optional: true, options: ['a', 'b']}
		}
	});
	same(this.generator.editorSelectOptionsForField('first_non_optional'), [['a', 'a'], ['b', 'b']]);
	same(this.generator.editorSelectOptionsForField('second_non_optional'), [['a', 'a'], ['b', 'b']]);
	same(this.generator.editorSelectOptionsForField('optional'), [['', ''], ['a', 'a'], ['b', 'b']]);
});

test("can convert checkbox into select field", function() {
	this.generator.setBacklogInfo({
		ticket_fields: {
			checkbox_field: {type: "checkbox", value: "should_not_be_used_but_may_be_set"},
			text_field: {}
		}
	});
	same(this.generator.isSelectLikeField('checkbox_field'), true);
	same(this.generator.editorSelectOptionsForField('checkbox_field'), [['True', '1'], ['False', '0']]);
});




module("computing column offsets and widths", {
	setup: function() {
		this.layouter = new BacklogColumnLayouter();
	}
});

test("one column will always take up all space (from start to finish)", function() {
	this.layouter.setNumberOfColumns(1);
	same(this.layouter.cssForColumnAtIndex(0), { right: '0%', left:'0px' });
});

test("first column always starts at left:0px", function() {
	this.layouter.setNumberOfColumns(2);
	same(this.layouter.cssForColumnAtIndex(0), { right: '50%', left:'0px' });
});

test("can space out many columns regularly", function() {
	this.layouter.setNumberOfColumns(5);
	same(this.layouter.cssForColumnAtIndex(0), { right: '80%', left:'0px' });
	same(this.layouter.cssForColumnAtIndex(1), { right: '60%', width:'18%' });
	same(this.layouter.cssForColumnAtIndex(2), { right: '40%', width:'18%' });
	same(this.layouter.cssForColumnAtIndex(3), { right: '20%', width:'18%' });
	same(this.layouter.cssForColumnAtIndex(4), { right: '0%', width:'18%' });
});

test("can anchor first column to the left", function() {
	this.layouter.setNumberOfColumns(2);
	this.layouter.setLeftAnchoredColumnsWithWidths(1, [20]);
	same(this.layouter.cssForColumnAtIndex(0), {left:'0px', width:'14px'}); // -6px padding and border
});

test("can anchor two columns to the left", function() {
	this.layouter.setNumberOfColumns(4);
	this.layouter.setLeftAnchoredColumnsWithWidths(2, [20, 30]);
	same(this.layouter.cssForColumnAtIndex(0), {left:'0px', width:'14px'});  // -6px padding and border
});

test("first column after left anchored columns fills up the gap between even distribution", function() {
	this.layouter.setNumberOfColumns(5);
	this.layouter.setLeftAnchoredColumnsWithWidths(1, [20]);
	same(this.layouter.cssForColumnAtIndex(1), {left:'20px', right:'60%'});
});

test("last column will always extend till right:0%", function() {
	this.layouter.setNumberOfColumns(2);
	this.layouter.setLeftAnchoredColumnsWithWidths(2, [20, 30]);
	same(this.layouter.cssForColumnAtIndex(0), {left:'0px', width:'14px'}); // -6px padding and border
	same(this.layouter.cssForColumnAtIndex(1), {left:'20px', right:'0%'});
});

test("can limit ammount that is alloted with percent widths", function() {
	this.layouter.setNumberOfColumns(5);
	this.layouter.setPercentSizedColumnsLimit(50);
	same(this.layouter.cssForColumnAtIndex(0), { right:'40%', left:'0px' });
	same(this.layouter.cssForColumnAtIndex(1), { right:'30%', width:'8%' });
	same(this.layouter.cssForColumnAtIndex(2), { right:'20%', width:'8%' });
	same(this.layouter.cssForColumnAtIndex(3), { right:'10%', width:'8%' });
	same(this.layouter.cssForColumnAtIndex(4), { right:'0%', width:'8%' });
});

test("can generate css for backlog with three columns, id column and dynamic sizing", function() {
	this.layouter.setNumberOfColumns(3);
	this.layouter.setLeftAnchoredColumnsWithWidths(1, [23]);
	this.layouter.setPercentSizedColumnsLimit(90);
	var firstCSS = [
		'span.first {',
		'	left: 0px;',
		'	width: 17px;',
		'}'
	].join('\n');
	equals(this.layouter.generateCSSAtColumnWithIndexAndClassName(0, 'first'), firstCSS);
	
	var secondCSS = [
		'span.second {',
		'	left: 23px;',
		'	right: 30%;',
		'}'
	].join('\n');
	equals(this.layouter.generateCSSAtColumnWithIndexAndClassName(1, 'second'), secondCSS);

	var thirdCSS = [
		'span.third {',
		'	right: 0%;',
		'	width: 28%;',
		'}'
	].join('\n');
	equals(this.layouter.generateCSSAtColumnWithIndexAndClassName(2, 'third'), thirdCSS);
	
	
	var css = [
		'<style type="text/css" media="all">',
		firstCSS + '\n',
		secondCSS + '\n',
		thirdCSS,
		'</style>'
	].join('\n');
	equals(this.layouter.generateCSSWithColumnNames(['first', 'second', 'third']), css);
});

test("can generate css for two class-names at once", function() {
	this.layouter.setNumberOfColumns(1);
	var expected = [
		'span.foo, span.bar {',
		'	right: 0%;',
		'	left: 0px;',
		'}'
	].join('\n');
	equals(this.layouter.generateCSSAtColumnWithIndexAndClassName(0, ['foo', 'bar']), expected);
});




// quite acceptance test like
module("backlogview updates", {
	setup: function() {
		$('#test-container').append('<div id="backlog"/>');
		addBacklogAndTestDataCreationMethods(this);
		this.view = new BacklogView();
		this.view.setBacklog(this.backlog);
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = '';
		$.observer.removeObserver();
	}
});

test("can add top level ticket after rendering", function() {
	this.view.renderBacklog(this.backlog);
	var story = this.injectStory(1);
	this.view.addNewTicket(story);
	ok(this.view.dom().is(':has(> dl > dt#ticketID-1)'));
});

test("can add task without story", function() {
	this.view.renderBacklog(this.backlog);
	var task = this.injectTask(1);
	this.backlog.addFakeStoryIfNecessary();
	this.view.addNewTicket(task);
	ok(this.view.dom().is(':has(> dl > dt#ticketID--1)'), 'fake story rendered');
	// how to test that its inside the fake story?
	ok(this.view.dom().is(':has(> dl > dd#ticketID-1)'), 'task without story rendered');
});

test("adding a task with story that is not already rendered renders both", function() {
	this.view.renderBacklog(this.backlog);
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	this.view.addNewTicket(task);
	ok(this.view.dom().is(':has(> dl > dt#ticketID-1)'), 'story rendered');
	ok(this.view.dom().is(':has(> dl > dd#ticketID-2)'), 'child task rendered');
});

test("adding something already rendered does nothing", function() {
	var story = this.injectStory(1);
	this.view.renderBacklog(this.backlog);
	// +1 because of totalling row
	equals(this.view.dom().find('[id^=ticketID]').length, 1+1);
	this.view.addNewTicket(story);
	equals(this.view.dom().find('[id^=ticketID]').length, 1+1);
});

test("add ticket with multiple parents of which one already exists", function() {
	function arrayContains(array, value) {
		return -1 !== $.inArray(value, array);
	}
	
	var firstParent = this.injectStory(1);
	this.view.renderBacklog(this.backlog);
	// +1 because of totalling row
	equals(this.view.dom().find('[id^=ticketID]').length, 1+1);
	
	var task = this.injectTask(2, firstParent);
	var secondParent = this.injectStory(3);
	this.linkChildToParent(task, secondParent);
	
	this.view.addNewTicket(task);
	equals(this.view.dom().find('[id^=ticketID]').length, 4+1);
	equals(this.view.subviews.length, 2+1);
	
	// the totalling column is not the last item but that's ok as we did not 
	// call updateOrdering
	var ticketIDsForTopLevelContainers = $.map(this.view.subviews, function(view) { return view.ticket.id(); });
	ok(arrayContains(ticketIDsForTopLevelContainers, 1));
	ok(arrayContains(ticketIDsForTopLevelContainers, 3));
	ok(this.view.dom().is(':has(> dl > dt#ticketID-3)'), 'task rendered');
	equals(this.view.dom('[id^=ticketID-2]').length, 2);
});

test("adding a child to a multilinked parent will add it in all places", function() {
	var firstParent = this.injectRequirement(1);
	var secondParent = this.injectRequirement(2);
	var multilinkedStory = this.injectStory(3, firstParent);
	this.linkChildToParent(multilinkedStory, secondParent);
	this.view.renderBacklog(this.backlog);
	// +1 for totalling column
	equals(this.view.dom().find('[id^=ticketID]').length, 4+1);
	
	var task = this.injectTask(4, multilinkedStory);
	this.view.addNewTicket(task);
	equals(this.view.dom().find('[id^=ticketID]').length, 6+1);
});

test("updating a ticket updates totals", function() {
	this.view.setConfiguredColumns(['id', 'summary', 'remaining_time'], {});
	var task = this.injectTask(1);
	this.view.renderBacklog(this.backlog);
	
	task.json.remaining_time = 4;
	task.postNotification(false);
	var totallingRow = this.view.dom('[id^=ticketID]:last');
	equals(totallingRow.find('.summary').text(), 'Totals');
	equals(totallingRow.find('.remaining_time').text(), 4);
});

test("adding a ticket through the inline additor updates totals", function() {
	// the container for the newly added task must not exist - otherwise the 
	// refresh will be triggered by other mechanisms
	var story = this.injectStory(1);
	this.view.setConfiguredColumns(['id', 'summary', 'remaining_time'], {});
	this.view.renderBacklog(this.backlog);
	
	var task = this.injectTask(2, story);
	task.json.remaining_time = 7;
	this.view.didAddOrRemoveTicketFromBacklog(this.backlog, task);
	
	var totallingRow = this.view.dom().find('[id^=ticketID-]:last');
	equals(totallingRow.find('.remaining_time').text(), 7, 'remaining time');
	
});

// --- merging -----------------------------------------------------------------
test("merging can remove tickets", function() {
	var story = this.injectStory(1);
	this.view.renderBacklog(this.backlog);
	this.backlog.mergeUpdatedBacklogJSON([]);
	same(this.view.orderOfTickets(), []);
});

test("merging can remove tickets with children (if children are removed too)", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	this.view.renderBacklog(this.backlog);
	this.backlog.mergeUpdatedBacklogJSON([]);
	same(this.view.orderOfTickets(), []);
});

test("merging can remove tickets but retain their children as top level items)", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectStory(2, requirement);
	this.view.renderBacklog(this.backlog);
	this.backlog.mergeUpdatedBacklogJSON([story.json]);
	same(this.view.orderOfTickets(), [2]);
	// should be direct children, not anymore in a childcontainer
	ok(this.view.dom().is('div:has( > dl > dt#ticketID-2)'), 'rendering task');
	// todo check superviews are correct
});

test("merging removal of container with container as child will relink child as top level item", function() {
	var requirement = this.injectRequirement(1);
	var story = this.injectStory(2, requirement);
	this.view.renderBacklog(this.backlog);
	var view = this.view.firstViewForTicket(requirement);
	this.backlog.mergeUpdatedBacklogJSON([story.json]);
	ok(this.view.dom().is('div:has( > dl dt#ticketID-2)'), 'rendering story');
});

test("merging removal of story with task will relink task as task without story", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	this.view.renderBacklog(this.backlog);
	this.backlog.mergeUpdatedBacklogJSON([task.json]);
	// TODO: find a better way to express what is nested in what
	ok(this.view.dom().is('div:has( > dl > dt#ticketID--1)'), 'rendering fake story');
	ok(this.view.dom().is('div:has( > dl > dd#ticketID-2)'), 'rendering task');
});

test("merging removal of container with child removes both", function() {
	// was bug: if task was first in array, then it was re-added by the remove logic of its parent
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	var anotherStory = this.injectStory(3);
	this.view.renderBacklog(this.backlog);
	this.backlog.setOrderOfTickets([2, 1]);
	this.backlog.mergeUpdatedBacklogJSON([anotherStory.json]);
	equals(this.view.dom('[id^=ticketID]').length, 1+1);
});

test("merging removal of top level container will remove it's view", function() {
	this.injectStory(1);
	var anotherStory = this.injectStory(2);
	this.view.renderBacklog(this.backlog);
	this.backlog.mergeUpdatedBacklogJSON([anotherStory.json]);
	// +1 for the totalling column
	equals(this.view.subviews.length, 1+1);
});

test("merging removal of last top level container will remove totalling column", function() {
	this.injectStory(1);
	this.view.renderBacklog(this.backlog);
	this.backlog.mergeUpdatedBacklogJSON([]);
	equals(this.view.visibleSubViews().length, 0);
});

test("merging new tickets will add them to the backlog", function() {
	this.view.renderBacklog(this.backlog);
	
	var storyJSON = this.buildJSON(1, 'story');
	this.backlog.mergeUpdatedBacklogJSON([storyJSON]);
	// +1 for totalling column
	equals(this.view.dom('[id^=ticketID]').length, 1+1, 'has story and totalling row');
	ok(this.view.dom().is(':has(> dl > dt#ticketID-1)'));
});

test("merging new ticket updates totals", function() {
	this.view.setConfiguredColumns(['id', 'summary', 'remaining_time'], {});
	this.view.renderBacklog(this.backlog);
	
	var taskJSON = this.buildJSON(1, 'task');
	taskJSON.remaining_time = 4;
	this.backlog.mergeUpdatedBacklogJSON([taskJSON]);
	var totallingRow = this.view.dom('[id^=ticketID]:last');
	equals(totallingRow.find('.remaining_time').text(), 4);
});

test("merging ticket deletion updates totals", function() {
	var task1 = this.injectTask(1);
	var task2 = this.injectTask(2);
	this.view.setConfiguredColumns(['id', 'summary', 'remaining_time'], {});
	this.view.renderBacklog(this.backlog);
	var totallingRow = this.view.dom('[id^=ticketID]:last');
	equals(totallingRow.find('.remaining_time').text(), 2*23);
	
	this.backlog.mergeUpdatedBacklogJSON([task1.json]);
	totallingRow = this.view.dom('[id^=ticketID]:last');
	equals(totallingRow.find('.remaining_time').text(), 23);
});

test("merging ticket update updates totals", function() {
	var task = this.injectTask(1);
	this.view.setConfiguredColumns(['id', 'summary', 'remaining_time'], {});
	this.view.renderBacklog(this.backlog);
	
	var taskJSON = this.buildJSON(1, 'task');
	taskJSON.remaining_time = 2;
	this.backlog.mergeUpdatedBacklogJSON([taskJSON]);
	var totallingRow = this.view.dom('[id^=ticketID]:last');
	equals(totallingRow.find('.remaining_time').text(), 2);
});

test("can apply ordering to rendered backlog", function() {
	this.injectStory(1);
	this.injectStory(2);
	this.injectStory(3);
	this.view.renderBacklog(this.backlog);
	this.backlog.setOrderOfTickets([2,1,3]);
	this.view.updateOrdering();
	equals(this.view.subviews[0].ticket.id(), 2);
	equals(this.view.subviews[1].ticket.id(), 1);
	equals(this.view.subviews[2].ticket.id(), 3);
	same(this.view.orderOfTickets(), [2,1,3]);
	
	// fs: When adding the totalling row, I experienced a bug with the order of
	// rendered HTML so we better check that the sort order is reflected in the
	// DOM as well.
	var extractTicketID = function(index, domElement) {
		var regexResult = /\-(-?\d+)$/.exec($(domElement).attr('id'));
		return parseInt(regexResult[1], 10);
	};
	function compareArrays(anArray, anotherArray) {
		equals(anArray.length, anotherArray.length);
		$.each(anArray, function(index, item) { equals(anotherArray[index], item); });
	}
	var orderOfRenderedTickets = this.view.dom('[id^="ticketID-"]').map(extractTicketID);
	// this simple solution did not work for Chromium 6.0.476.0
	// same(orderOfRenderedTickets, [2,1,3,-2]);
	compareArrays([2,1,3,-2], orderOfRenderedTickets);
});

test("can apply ordering to rendered backlog with child tickets", function() {
	var story = this.injectStory(1);
	this.injectTask(2, story);
	this.injectTask(3, story);
	this.view.renderBacklog(this.backlog);
	this.backlog.setOrderOfTickets([1,3,2]);
	this.view.updateOrdering();
	
	var view = this.view.firstViewForTicket(story);
	equals(view.subviews[0].ticket.id(), 3);
	equals(view.subviews[1].ticket.id(), 2);
	same(this.view.orderOfTickets(), [1,3,2]);
});

test("will trigger backlog reload after editing ticket", function() {
	// kind of nasty, with lots of mocking...
	expect(2);
	var story = this.injectStory(1);
	this.view.renderBacklog(this.backlog);
	var view = this.view.firstViewForTicket(story);
	var callback;
	story.submitToServer = function(aCallback) { callback = aCallback; };
	view.didEndInlineEditForField('fnord', 'sprint');
	ok(callback);
	this.backlog.triggerUpdateFromServer = function() {
		ok(true, 'callback called');
	};
	callback();
});

test("will unregister from notifications if removed from backlog", function() {
	var originalUpdateFromTicket = View.prototype.updateFromTicket;
	View.prototype.updateFromTicket = function() { ok(false, 'should have removed the observer'); };
	
	var ticket = this.injectStory(1);
	this.view.renderBacklog(this.backlog);
	var view = this.view.firstViewForTicket(ticket);
	this.backlog.tickets().splice(0,1); // remove ticket
	
	view.removeFromDOM();
	ticket.postNotification();
	
	View.prototype.updateFromTicket = originalUpdateFromTicket;
});

test("will always let the fake story be the element before last", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	var freeTask = this.injectTask(3);
	
	this.view.renderBacklog(this.backlog);
	this.backlog.mergeUpdatedBacklogJSON([story.json, task.json, freeTask.json, this.buildJSON(4, 'story')]);
	same(this.view.orderOfTickets(), [1,2,4,3]); // fake story not counted
});

test("will always ignore totalling row for ticket order", function() {
	var task = this.injectTask(1);
	this.view.renderBacklog(this.backlog);
	this.backlog.mergeUpdatedBacklogJSON([task.json]);
	same(this.view.orderOfTickets(), [1]); // totalling row not counted
});

test("can update type and status css classes", function() {
	var story = this.injectStory(1);
	var task = this.injectTask(2, story);
	task.json.status = 'new';
	
	this.view.renderBacklog(this.backlog);
	story.setValueForKey('bug', 'type');
	ok( ! this.view.dom('#ticketID-1').hasClass('tickettype-story'));
	ok(this.view.dom('#ticketID-1').hasClass('tickettype-bug'));
	task.setValueForKey('closed', 'status');
	ok( ! this.view.dom('#ticketID-2').hasClass('ticketstatus-new'));
	ok(this.view.dom('#ticketID-2').hasClass('ticketstatus-closed'));
});



// TODO: add nice animations for adding and removing?
// consider to trigger a full position save after such an update (to get correct board order of children)






module("global backlog page stuff", {
	setup: function() {
		this.view = new BacklogView();
		// Fixture to append notices to
		$('#test-container').append('<div id="backlog"><h1/></div>');
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = '';
	}
});

test("can display a message above the backlog", function() {
	this.view.setMessage('fnord');
	equals($('#notice').text(), 'fnord');
});

test("can change message without adding additional markup", function() {
	this.view.setMessage('foo');
	equals($('#notice').text(), 'foo');
	this.view.setMessage('bar');
	equals($('#notice').text(), 'bar');
});



// FIXME: (AT) if needed for the OptionGroup we should think about creating a
// generic function and not only for the Sprint, might also be needed for the
// milestones. The hierarchy for the OptionGroups can come from the server in
// form of a JSON nested dictionary.
