module("backlog filtering: without rendering", {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.backlog = new Backlog();
		this.filter = new BacklogFiltering(this.backlog);

		this.story = this.injectUserStory(1);
		this.task1 = this.injectTask(2, this.story);
		this.task2 = this.injectTask(3, this.story);
		this.task3 = this.injectTask(3, this.story);
		$.extend(this.task1.json, { component: 'component1', status: 'new', foo: 'bar'});
		$.extend(this.task2.json, { component: 'component2', status: 'new' });
		$.extend(this.task3.json, { component: 'component2', status: 'new' });
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = "";
		$.observer.removeObserver();
	}
});

test("can set attribute to filter whiteboard by", function() {
	this.filter.setAttributeFilteringKey('type');
	equals(this.filter.attributeFilteringKey(), 'type', 'should filter by type');
});


test("registers for callback after each change on a ticket", function() {
	expect(1);
	var filter = new BacklogFiltering(this.backlog, function(){});
	filter.setAttributeFilteringKey('foo');
	filter.didChangeTickets = function() { ok(true); };
	
	filter.addFilterPopupIfNecessary('#test-container');
	Ticket.didChangeTicketFromServer();
});

test("sends notifications after each filter change", function() {
	expect(1);
	$.observer.addObserver(BacklogFiltering.DID_CHANGE_FILTER_SETTINGS,
		function(filter) {
			equals(filter.attributeFilteringValue(), 'component1');
		});
	this.filter.setAttributeFilteringKey('component');
	this.filter.addFilterPopup('#test-container');
	$('#filter-attribute-popup').val('component1').trigger('change');
});

test("can add filter that hides closed items", function() {
	this.filter.setShouldHideClosedItems(false);
	ok(this.filter.filterClosures.hideClosedItems === this.filter.noopFilter, "default: is always true");
	this.filter.setShouldHideClosedItems(true);
	
	ok(this.filter.filterClosures.hideClosedItems !== undefined, "after setting, it is actually set");
	ok(this.filter.filterClosures.hideClosedItems !== this.filter.noopFilter, "after setting, is not always true");
});

test("can filter with multiple criteria", function() {
	var ticket = this.injectTask(23);
	ok(this.filter.shouldShow(ticket));
	ticket.json.component = "component1";
	this.filter.setAttributeFilteringKey('component');
	this.filter.setAttributeFilteringValue('component2');
	ok( ! this.filter.shouldShow(ticket));
	
	this.filter.setShouldHideClosedItems(true);
	ok( ! this.filter.shouldShow(ticket));
	ticket.json.component = "component2";
	ticket.json.status = "closed";
	ok( ! this.filter.shouldShow(ticket));
	ticket.json.status = undefined;
	ok(this.filter.shouldShow(ticket));
});

test("can filter my tickets by owner", function () {
	var backlog_info = wrapContentInInfo({"username": "person1"});
	this.backlog.loader.setInfo(backlog_info);

	var ticket = this.injectTask(23);
	ticket.json.owner = "person1";
	ok(this.filter.shouldShow(ticket));
	this.filter.setShouldShowOnlyMyItems(true);
	ok(this.filter.shouldShow(ticket));
	ticket.json.owner = "person2";
	ok(! this.filter.shouldShow(ticket));
	this.filter.setShouldShowOnlyMyItems(false);
	ok(this.filter.shouldShow(ticket));
});

test("can filter my tickets by resource", function () {
	var backlog_info = wrapContentInInfo({"username": "person1"});
	this.backlog.loader.setInfo(backlog_info);

	var ticket = this.injectTask(23);
	ticket.json.owner = "person2";
	ticket.json.drp_resources = "jim, jack, person1, frank";
	this.filter.setShouldShowOnlyMyItems(true);
	ok(this.filter.shouldShow(ticket));
	ticket.json.drp_resources = "jim, jack";
	ok(! this.filter.shouldShow(ticket));
});

test("can override decision to filter", function() {
	ok(this.filter.shouldShow(this.task1));
	this.filter.filterClosures.denyFilter = function() {
		return BacklogFiltering.SHOULD_NOT_SHOW_ITEM;
	};
	ok( ! this.filter.shouldShow(this.task1));
	this.filter.filterClosures.acceptingFilter = function() {
		return BacklogFiltering.MUST_SHOW_ITEM;
	};
	ok(this.filter.shouldShow(this.task1));
});

test("can serialize filter to string", function() {
	this.filter.setShouldShowOnlyMyItems(true);
	equals(this.filter.toJSON(), '{"showMyItems":true}');
});

test("ignore noop filters during serialization", function() {
	this.filter.setShouldShowOnlyMyItems(false);
	equals(this.filter.filterClosures.showMyItems, this.filter.noopFilter, 'filterClosures contain a noop filter');
	
	equals(this.filter.toJSON(), '{}');
});

test("can serialize generic attribute filter", function() {
	this.filter.setAttributeFilteringKey('foo');
	this.filter.setAttributeFilteringValue('bar');
	
	equals(this.filter.toJSON(), '{"foo":"bar"}');
});

test("reset attribute filter before loading filters", function() {
	this.backlog.loader.setLoggedInUser('someone');
	this.filter.setAttributeFilteringKey('foo');
	this.filter.setAttributeFilteringValue('bar');
	ok(this.filter.isAttributeFilteringActive());
	
	this.filter.fromJSON('{"showMyItems":true}');
	ok(this.filter.isShowMyItemsFilterActive());
	equals('', this.filter.attributeFilteringValue());
	ok(this.filter.isAttributeFilteringActive(), 'attribute filter is still enabled but without filter value');
});

test("reset all previous filters before loading filters", function() {
	this.filter.setShouldShowOnlyMyItems(true);
	this.backlog.loader.setInfo(wrapContentInInfo({"username": "person1"}));
	var ticket = this.injectTask(23);
	ticket.json.owner = "someoneElse";
	ok( ! this.filter.shouldShow(ticket), 'ticket should be hidden');
	
	this.filter.fromJSON('{}');
	ok( ! this.filter.isShowMyItemsFilterActive());
	ok(this.filter.shouldShow(ticket), 'ticket will be displayed');
});

test("can load filter from serialized string", function() {
	this.backlog.loader.setLoggedInUser("person1");
	var ticket = this.injectTask(23);
	ticket.json.owner = "someoneElse";
	ok(this.filter.shouldShow(ticket), '"show my items" filter is not active');
	
	this.filter.fromJSON('{"showMyItems":true}');
	ok( ! this.filter.shouldShow(ticket), '"show my items" filter is active now');
	ok(this.filter.isShowMyItemsFilterActive());
});

test("ignores 'show only my items' filter during deserialization when no one is logged", function() {
	ok( ! this.backlog.loader.isUserLoggedIn());
	ok( ! this.filter.isShowMyItemsFilterActive());
	
	this.filter.fromJSON('{"showMyItems":true}');
	ok( ! this.filter.isShowMyItemsFilterActive());
});

test("can load attribute filter from serialized string", function() {
	this.filter.setAttributeFilteringKey('foo');
	var ticket = this.injectTask(23);
	ticket.json.foo = "baz";
	ok(this.filter.shouldShow(ticket), 'attribute filter is not active');
	
	this.filter.fromJSON('{"foo":"bar"}');
	ok( ! this.filter.shouldShow(ticket), 'attribute filter is active');
});

test("ignores attribute filter if different than backlog info", function() {
	this.filter.setAttributeFilteringKey('foo');
	var ticket = this.injectTask(23);
	ticket.json.foo = "baz";
	ok(this.filter.shouldShow(ticket), 'attribute filter is not active');
	
	this.filter.fromJSON('{"invalid":"bar"}');
	ok(this.filter.shouldShow(ticket), 'attribute filter is still not active');
});

test("ignores invalid json filter strings", function() {
	this.filter.fromJSON('"""');
});


module("backlog filtering: with rendering", {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.view = new BacklogView();
		this.filter = new FilterController();
		this.injectFixture();
		this.render = function(){
            $('#test-container')[0].innerHTML = '';
			var dom = $(this.view.htmlForBacklog(this.backlog));
			$('#test-container').html(dom);
			return dom;
		};
		this.render();
		this.filter.filterKey = 'fnord';
		this.filter.filterValue = 'fnord';
		$('#test-container').append("<div id='toolbar' class='toolbar top'></div>");
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = '';
		$.observer.removeObserver();
	}
});

test("will add filter popup to whiteboard if filter attribute is set", function() {
	expect(2);
	this.filter.filterKey = null;
	this.filter.initializeFilter();
	equals($('#filter-attribute-popup').length, 0);

	$('#test-container')[0].innerHTML = '';
	$('#test-container').append("<div id='toolbar' class='toolbar top'></div>");
	this.filter.filterKey = 'type';
	this.filter.initializeFilter();
	equals($('#filter-attribute-popup').length, 1);
});

test("pre-fills attribute filter popup correctly", function() {
	this.filter.filterKey = 'type';
	this.filter.renderPopup();
	var criteria = this.backlog.possibleFilterCriteriaForAttribute('type');
	var options = $('#filter-attribute-popup option');
	equals(options.length, criteria.length + 1); // + empty value
	equals(options.eq(0).text(), 'Filter by...');
	equals($('#filter-attribute-popup').val(), '');
	equals(options.eq(0).val(), '');
	equals(options.eq(1).text(), 'requirement');
	equals(options.eq(1).val(), 'requirement');
});

test("selects correct option in attribute filter popup if filter is active", function() {
	this.filter.filterKey = 'type';
	this.filter.filterValue = 'requirement';
	var criteria = this.backlog.possibleFilterCriteriaForAttribute('type');
	ok(-1 !== $.inArray('requirement', criteria));
	
	this.filter.renderPopup();
	equals($('#filter-attribute-popup').val(), 'requirement');
});

test("select no option in attribute filter popup if non-existing option was set", function() {
	this.filter.filterKey = 'type';
	this.filter.filterValue = 'invalid';
	var criteria = this.backlog.possibleFilterCriteriaForAttribute('type');
	ok(-1 === $.inArray('invalid', criteria));
	
	this.filter.renderPopup('#test-container');
	equals($('#filter-attribute-popup').val(), '');
});

test("can add buttons for hiding closed or other items", function(){
	var backlog_info = wrapContentInInfo({"type": "sprint"});
	this.filter.loader.setInfo(backlog_info);
	this.filter.addFilterButtons();
	ok($('ul#filter-button-container').is(":has(#hide-closed-button)"));
	ok($('ul#filter-button-container').is(":has(#show-onlymine-button)"));
});

test("disables button for hiding closed items when backlog is global", function(){
	var backlog_info = wrapContentInInfo({"type": "global"});
	this.filter.loader.setInfo(backlog_info);
	this.filter.addFilterButtons();
    ok($('#hide-closed-button.disabled'));
});

test("'hide closed items' button shows correct initial state", function() {
	var backlog_info = wrapContentInInfo({"type": "sprint"});
	this.filter.loader.setInfo(backlog_info);

	this.filter.hideClosed = true;

	this.filter.addFilterButtons();
	var showMineButton = $('ul#filter-button-container #hide-closed-button');
	ok(showMineButton.hasClass('active'), 'button is active');
});

test("hide closed button sends correct event", function() {
	var backlog_info = wrapContentInInfo({"type": "sprint"});
	this.filter.loader.setInfo(backlog_info);
	this.filter.addFilterButtons();
	ok( ! this.filter.hideClosed);
	$('#hide-closed-button').click();
	ok($('#hide-closed-button').hasClass('active'));
	ok(this.filter.hideClosed);
	$('#hide-closed-button').click();
	ok( ! this.filter.hideClosed);
});

test("'show only my items' button shows correct initial state", function() {
	this.filter.onlyMine = true;
	
	this.filter.addFilterButtons();
	var showMineButton = $('ul#filter-button-container #show-onlymine-button');
	ok(showMineButton.hasClass('active'), 'button is active');
});

test("show-onlymine button sends correct event", function() {
	this.filter.loader.setLoggedInUser('someone');
	ok(this.filter.loader.isUserLoggedIn(), 'user should be logged in');
	
	this.filter.addFilterButtons();
	ok( ! this.filter.onlyMine);
	$('#show-onlymine-button').click();
	ok($('#show-onlymine-button').hasClass('active'));
	ok(this.filter.onlyMine, 'filter should be active now');
	$('#show-onlymine-button').click();
	ok( ! $('#show-onlymine-button').hasClass('active'));
	ok( ! this.filter.onlyMine);
});

test("'show only my items' button is disabled if not logged in", function() {
	ok( ! this.filter.loader.isUserLoggedIn());
	
	this.filter.addFilterButtons();
	var showMineButton = $('ul#filter-button-container #show-onlymine-button');
	ok(showMineButton.hasClass('disabled'), 'button is disabled');
});

test("all tickets are visible by default", function() {
	// +1 because of the totalling row
	equals($('[id^=ticketID]:visible').length, 7+1);
});

test("can show all tickets that have a matching json key", function() {
	this.task1.json.fnord = 'fnord';
	this.task2.json.fnord = 'fnord';
	this.render();
	this.filter.applyFiltering();
	equals($('[id^=ticketID]:visible').length, 5+1);
});

test("can hide closed tickets", function() {
	equals(7+1, $('[id^=ticketID]:visible').length);
	this.task1.json.status = 'closed';
	this.render();
	this.filter.filterValue = '';
	this.filter.hideClosed = true;
	this.filter.applyFiltering();
	equals(6+1, $('[id^=ticketID]:visible').length);
	ok($('#ticketID-3').is(':hidden'), "closed ticket is hidden");
	this.filter.hideClosed = false;
	this.filter.applyFiltering();
	equals(7+1, $('[id^=ticketID]:visible').length);
});

test("does show all parents even if they do not match", function() {
	this.task1.json.fnord = 'fnord';
	this.render();
	this.filter.applyFiltering();
	equals(3+1, $('[id^=ticketID]:visible').length);
});

test("row is visible after clicking a filter button", function() {
	this.task1.json.fnord = 'fnord';
	this.render();
	ok(this.view.totallingRow().dom().is(':visible'));
	this.filter.applyFiltering();
	ok(this.view.totallingRow().dom().is(':visible'), 'totalling row is still shown');
});

test("only sums up attributes from visible tickets if filter was applied", function() {
	this.view.setConfiguredColumns(['remaining_time'], {});
	this.task1.json.fnord = 'fnord';  // this task will be shown even when filter is active
	this.task1.json.remaining_time = 3;
	this.render();
	new TotalsRowController().recalculateTotals();
	ok(this.view.totallingRow().dom().is(':visible'));
	equals($("#ticketID--2 span.remaining_time").text(), 3+2*23);
	
	this.filter.applyFiltering();
	ok(this.view.totallingRow().dom().is(':visible'));
	equals($("#ticketID--2 span.remaining_time").text(), 3);
});

test("calculates total number of tickets based on filter", function() {
	this.task1.json.fnord = 'fnord';  // this task will be shown even when filter is active
	$("#ticketID-" + this.task1.json.id).metadata().fnord = "fnord";
	new TotalsRowController().recalculateTotals();
    equals($('#ticketID--2 .id').text(), 7);
    this.filter.applyFiltering();
    equals($('#ticketID--2 .id').text(), 1 /*task*/ + 2 /*parents*/);
});

test("can remove total attribute if all numeric tickets are filtered out", function() {
	this.view.setConfiguredColumns(['id', 'remaining_time'], {});
    this.task1.json.fnord = 'fnord';  // this task will be shown even when filter is active
    this.task1.json.remaining_time = undefined;
    // need to re-render in order to apply column changes
    this.render();

    this.filter.filteringValue = "fnord";
    this.filter.applyFiltering();
    equals($('#ticketID--2 .remaining_time').text(), "");
});

