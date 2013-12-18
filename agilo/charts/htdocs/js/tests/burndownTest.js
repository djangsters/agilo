module('burndown chart', {
	setup: function() {
		var info = wrapContentInInfo({"type": "sprint", "name": "aBacklogName", "sprint_or_release": "aSprintName"});
		this.loader = new BacklogServerCommunicator(info);
		this.burndown = new Burndown(this.loader);
		
		this.originalPlot = window.plotBurndown;
		this.burndown.rewirePlotBurndown();
		// stub out the plot plugin which is not available in unit tests
		this.burndown.plotBurndown = function(){};

	},
	teardown: function() {
		$('#old-backlog-offscreen-loading-area').remove();
		$.observer.removeObserver();
		window.plotBurndown = this.originalPlot;
		$('#test-container')[0].innerHTML = '';
	}
});

test("has access to loader", function() {
	ok(this.burndown.loader);
});

test("can replace burndown chart", function() {
	var sensedSelector, sensedComponent;
	this.burndown.plotBurndown = function(selector, data) { sensedSelector = selector; sensedComponent = data; };
	$(this.burndown.toHTML()).appendTo('#test-container');
	this.burndown.updateBurndownWithValues('fnord');
	assertMatches(sensedSelector, '#chart-container');
	equals(sensedComponent, 'fnord');
});

test("sets up bundown reloading with correct parameters and starts data get", function() {
	var wasCalled;
	this.loader.burndownValuesLoader.startLoading = function() { wasCalled = true; };
	
	this.burndown.reloadBurndownChartFilteredByComponent({
		attributeFilteringValue:function() { return 'fnord'; }
	});
	equals(this.loader.burndownValuesLoader.filter_by, 'fnord');
	ok(wasCalled);
});

test("will remove prior burndown chart before drawing the new one", function() {
	$('#test-container')
		.append(this.burndown.toHTML())
		.find('#chart-container').append('<div id="extra" />');
	
	this.burndown.updateBurndownWithValues('irrelevant');
	equals($('#chart-container #extra').length, 0);
});

test("can trigger reload via generic notification", function() {
	expect(1);
	this.burndown.reloadBurndownChart = function() { ok(true); };
	this.burndown.registerForDataChangeNotification();
	$.observer.postNotification(agilo.DID_CHANGE_BURNDOWN_DATA);
});

test("can trigger reload via filter notification", function() {
	var sensor;
	this.burndown.reloadBurndownChartFilteredByComponent = function(aFilter) { sensor = aFilter; };
	this.loader.info().should_filter_by_attribute = "component";
	this.loader.info().should_reload_burndown_on_filter_change_when_filtering_by_component = true;
	
	this.burndown.registerForBacklogFilteringChanges();
	$.observer.postNotification(BacklogFiltering.DID_CHANGE_FILTER_SETTINGS, 'fnord');
	equals(sensor, 'fnord');
});

test("reloadBurndownChartFilteredByComponent will only register for reloading if reloading burndown options are set", function() {
	var sensor;
	this.burndown.reloadBurndownChartFilteredByComponent = function() { sensor = true; };
	this.burndown.registerForBacklogFilteringChanges();
	$.observer.postNotification(BacklogFiltering.DID_CHANGE_FILTER_SETTINGS);
	ok( ! sensor);
	
	this.loader.info().should_filter_by_attribute = "component";
	this.loader.info().should_reload_burndown_on_filter_change_when_filtering_by_component = true;
	this.burndown.registerForBacklogFilteringChanges();
	$.observer.postNotification(BacklogFiltering.DID_CHANGE_FILTER_SETTINGS);
	ok(sensor);
});

test("auto-registers on creation if options good options are set", function() {
	$.extend(this.loader.info(), {
		should_filter_by_attribute: "component",
		should_reload_burndown_on_filter_change_when_filtering_by_component: true
	});
	var originalReload = Burndown.prototype.reloadBurndownChartFilteredByComponent;
	var sensor;
	Burndown.prototype.reloadBurndownChartFilteredByComponent = function() { sensor = true; };
	var burndown = new Burndown(this.loader);
	
	$.observer.postNotification(BacklogFiltering.DID_CHANGE_FILTER_SETTINGS);
	ok(sensor);
	
	Burndown.prototype.reloadBurndownChartFilteredByComponent = originalReload;
});

test("sets moving up after loading for next time burndown is shown if area is not visible", function() {
	this.burndown.hasPlottedBurndownChart = true;
	$('#test-container').append('<div id="burndown" style="display:none;">');
	this.burndown.updateBurndownWithValues('notused');
	ok( ! this.burndown.hasPlottedBurndownChart);
});

test("moves chart over immediately if window is shown", function() {
	$('#test-container').append('<div id="burndown">');
	this.burndown.updateBurndownWithValues('notused');
	ok(this.burndown.hasPlottedBurndownChart);
});

test("stores burndown chart values in updateBurndownWithValues", function() {
	this.burndown.updateBurndownWithValues('fnord');
	equals(this.burndown.burndownValues, 'fnord');
});

test("plots burndown initially when opening chart", function() {
	var sensedData;
	this.burndown.plotBurndown = function(selector, data) { sensedData = data; };

	$(this.burndown.toHTML()).appendTo('#test-container');
	this.burndown.toggleBurndown();
	
	this.burndown.updateBurndownWithValues("used later");
	equals(sensedData, undefined);
	
	this.burndown.toggleBurndown();
	equals(sensedData, "used later");
});

test("can rewire plotBurndown to store the values like an ajax call", function() {
	window.plotBurndown = this.originalPlot;
	this.burndown.plotBurndown = undefined;
	this.burndown.rewirePlotBurndown();
	equals(this.burndown.plotBurndown, this.originalPlot);
	plotBurndown('#notused', 'fnord');
	equals(this.burndown.burndownValues, 'fnord');
});

test("will only trigger reload if component value did change since last time", function() {
	var mockFilter = {
		value: 'foo',
		attributeFilteringValue: function() { return this.value; }
	};
	// initial call always returns yes
	ok(this.burndown.didChangeAttributeValue(mockFilter));
	ok( ! this.burndown.didChangeAttributeValue(mockFilter));
	mockFilter.value = 'bar';
	ok(this.burndown.didChangeAttributeValue(mockFilter));
	ok( ! this.burndown.didChangeAttributeValue(mockFilter));
});

test("can add buttons toggling burndown display", function(){
	$('#test-container').append("<div id='toolbar' class='toolbar top'></div>");
	this.burndown.addToggleButton();
	ok($('ul#burndown-button-container').is(":has(#burndown-button)"));
});

test("show burndown button can hide and show burndown", function() {
	$('#test-container').append("<div id='toolbar' class='toolbar top'></div>");
	$('#test-container').append("<div id='burndown' style='display:none'></div>");
	this.burndown.addToggleButton();
	
	ok($('#burndown').is(':hidden'));
	$('#burndown-button').click();
	ok($('#burndown').is(':visible'));
	ok($('#burndown-button').hasClass('active'));
	$('#burndown-button').click();
	ok($('#burndown').is(':hidden'));
	ok( ! $('#burndown-button').hasClass('active'));
});

test("can close burndown with window close button", function() {
	$('#test-container').append("<div id='toolbar' class='toolbar top'></div>");
	$('#test-container').append("<div id='burndown' style='display:none'><p class='close'></p></div>");
	this.burndown.addToggleButton();
	this.burndown.connectCloseButton();
	$('#burndown-button').click();
	ok($('#burndown-button').hasClass('active'));
	
	$('#burndown .close').click();
	ok($('#burndown').is(':hidden'));
	ok( ! $('#burndown-button').hasClass('active'));
});

test("only loads burndown chart if on sprint backlog", function() {
    var didStartLoading = false;
    this.loader.burndownValuesLoader.startLoading = function() { didStartLoading = true; };
    
    this.loader.info().type = 'global';
    this.burndown.reloadBurndownChart();
    ok( ! didStartLoading, 'should not start loading');
    
    this.loader.info().type = 'milestone';
    this.burndown.reloadBurndownChart();
    ok( ! didStartLoading, 'should not start loading');
    
    this.loader.info().type = 'sprint';
    this.burndown.reloadBurndownChart();
    ok(didStartLoading, 'should start loading');
});

// may need to load burndown chart in the other container (that is also used during initial load) and then move it as needed (making sure to trigger the IE fix logic)
