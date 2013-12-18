module('toggle view', {
	setup: function(){
		var info = {"sprint_or_release": "Foo", "type": "sprint", "name": "Sprint Backlog"};
		this.loader = new BacklogServerCommunicator(wrapContentInInfo(info));
		this.loader.stubEverything();
		this.view = new ToggleView(this.loader);
		$('#test-container').html('<div class="toolbar top" />');
	},
	teardown: function() {
		// REFACT: this should become a function of the tester or even an automatism that has to be disabled if it is unwanted...
		$('#test-container')[0].innerHTML = '';
	}
});

test("can set active views", function() {
	same(this.view.allowedViews(), []);
	this.view.allowedViews(['new_backlog']);
	same(this.view.allowedViews(), ['new_backlog']);
});

test("does only accept backlog views it knows about", function() {
	this.view.allowedViews(['foo', 'new_backlog', 'whiteboard', 'bar']);
	same(this.view.allowedViews(), ['new_backlog', 'whiteboard']);
});

test("knows which backlogs switcher parts to show", function() {
	equals(this.view.shouldShowSwitcherPart('whiteboard'), false);
	this.view.allowedViews(['whiteboard']);
	equals(this.view.shouldShowSwitcherPart('whiteboard'), true);
});

test("generates only backlog-targets it should show", function() {
	this.view.allowedViews(['new_backlog']);
	var buttons = this.view.generateButtonOptions();
	equals(buttons.length, 1);
});

test("display will display the switcher only if it is necessary", function() {
	this.view.display();
	equals($('#toggle-button-container').length, 0);
	this.view.allowedViews(['whiteboard']);
	this.view.display();
	equals($('#toggle-button-container').length, 0);
	this.view.allowedViews(['whiteboard', 'new_backlog']);
	this.view.display();
	equals($('#toggle-button-container').length, 1);
});

test("generates correct urls for sprints", function() {
	var urls = this.view.urls();
	equals(urls.new_backlog, '/backlog/Sprint%20Backlog/Foo');
	equals(urls.whiteboard, '/agilo-pro/sprints/Foo/whiteboard');
	
	// TODO: this is not fit yet for the product backlog or other global backlogs
});

test("generates correct urls for global backlogs", function() {
	// {"sprint_or_release": "global", "type": "global", "name": "Product Backlog"};
	this.loader.setInfo(wrapContentInInfo({"sprint_or_release": "global", "type": "global", "name": "Bug Backlog"}));
	var urls = this.view.urls();
	ok(urls);
	equals(urls.new_backlog, '/backlog/Bug%20Backlog');	
});

test("can generate correct urls for milestone scoped backlogs", function() {
	this.loader.setInfo(wrapContentInInfo({"sprint_or_release": "milestone1", "type": "milestone", "name": "Milestone Backlog"}));
	var urls = this.view.urls();
	ok(urls);
	equals(urls.new_backlog, '/backlog/Milestone%20Backlog/milestone1');	
});

test("uses generated urls for the buttons", function() {
	this.view.sprintName = 'Foo';
	this.view.allowedViews(['new_backlog', 'whiteboard']);
	this.view.display();
	assertMatches($('#backlog-button a').attr('href'), this.view.urls().new_backlog);
	assertMatches($('#whiteboard-button a').attr('href'), this.view.urls().whiteboard);
});

test("can add button to toolbar to toggle views", function() {
	this.view.sprintName = 'Foo';
	this.view.allowedViews(['new_backlog', 'whiteboard']);
	equals($('#toggle-button-container').length, 0);
	this.view.addToolbarButtons();
	equals($('#toggle-button-container').length, 1);
});

test("global or milestone backlogs never get a whiteboard", function() {
	this.view.allowedViews(['new_backlog', 'whiteboard']);
	equals(this.view.shouldShowSwitcherPart('whiteboard'), true);
	
	this.loader.info().type = 'global';
	equals(this.view.shouldShowSwitcherPart('whiteboard'), false);
	
	this.loader.info().type = 'milestone';
	equals(this.view.shouldShowSwitcherPart('whiteboard'), false);
});

test("knows not to show the switcher on global milestone backlogs even when pro is active", function() {
	this.loader.setInfo(wrapContentInInfo({"sprint_or_release": "milestone1", "type": "milestone", "name": "Milestone Backlog"}));
	this.view.allowedViews(['whiteboard']);
	equals(this.view.shouldShowSwitcher(), false);
});


test("switcher does not show if no or incorrect backlog info has been set", function() {
	this.view.allowedViews(['new_backlog', 'whiteboard']);
	equals(this.view.shouldShowSwitcher(), true);
	
	this.loader.info().type = undefined;
	equals(this.view.shouldShowSwitcher(), false);
});
