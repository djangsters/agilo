function emptyContingentsFixture() {
	return { permissions:[], content_type:'contingent_list', content:[] };
}

function contingentFixture(contingent) {
	return {
		permissions:['AGILO_CONTINGENT_ADD_TIME'], // REFACT: have a permissions object where the permissions are centralized
		content_type:'contingent',
		content:$.extend({
			name:'aContingentName', sprint:'aSprintName',
			amount:0, actual:0, exists:true // exists means is in the db - can be ignored
		}, contingent)
	};
}
function contingentsFixture() {
	var firstContingent = contingentFixture({
		name:'firstContingent', sprint:'sprintName',
		amount:20, actual:15, exists:true // exists means is in the db - can be ignored
	});
	var secondContingent = copyJSON(firstContingent);
	secondContingent.content.name = 'secondContingent';
	return {
		permissions: ['AGILO_CONTINGENT_ADMIN'],
		content_type: 'contingent_list',
		content: [firstContingent, secondContingent]
	};
}

module('contingents model', {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.loader = new BacklogServerCommunicator({});
		this.loader.stubEverything();
		this.model = new Contingents(this.loader);
		this.wrapper = contingentsFixture();
		this.contingentJSON = this.wrapper.content[0];
		
		this.messages = [];
		this.model.registerErrorSink(function(message) {
			this.messages.push(message);
		}.bind(this));
		
		this.setFixture = function(aFixture) {
			this.loader.contingentsLoader.setFixture(aFixture);
			this.loader.startLoadingContingents();
			this.model._contingents = [];
		};
		this.setFixture(this.wrapper);
		this.contingent = this.model.contingents()[0];
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = "";
	}
});

test("can instantiate contingents model", function() {
	ok(this.model);
	equals(this.loader, this.model.loader);
});

test("can return list of contingents", function() {
	this.loader.contingentsLoader.json = undefined;
	equals(this.model.contingents().length, 0);
	this.setFixture(this.wrapper);
	equals(this.model.contingents().length, 2);
	this.wrapper.content.push(copyJSON(this.wrapper.content[0]));
	this.setFixture(this.wrapper);
	equals(this.model.contingents().length, 3);
});

test("knows if contingents are available", function() {
	ok(this.model.hasContingents());
	this.setFixture(emptyContingentsFixture());
	ok( ! this.model.hasContingents());
});

test("contingent can access all needed values of the contingent", function() {
	var contingent = new Contingent(this, this.contingentJSON);
	equals(contingent.name(), 'firstContingent');
	equals(contingent.sprintName(), 'sprintName');
	equals(contingent.availableTime(), 20);
	equals(contingent.spentTime(), 15);
	equals(contingent.remainingTime(), 5);
	equals(contingent.percentDone(), 75);
});

test("availableTime() normalizes value to digit", function() {
	var contingent = new Contingent(this, this.contingentJSON);
	this.contingent.contingent.amount = null;
	equals(this.contingent.availableTime(), 0);
});

test("percentDone() can work with pathological values", function() {
	var contingent = new Contingent(this, this.contingentJSON);
	
	this.contingent.contingent.actual = 0;
	equals(this.contingent.percentDone(), 0);
	
	this.contingent.contingent.actual = 0;
	this.contingent.contingent.amount = 0;
	equals(this.contingent.percentDone(), 0);
	
	this.contingent.contingent.amount = null;
	equals(this.contingent.percentDone(), 0);
});

test("returning wrapper objects for contingents", function() {
	equals(this.contingent.constructor, Contingent);
});

test("knows if it can submit to the server", function() {
	ok(this.contingent.canEdit());
	this.contingent.json.permissions = [];
	ok( ! this.contingent.canEdit());
});

test("can submit to server via the BacklogServerCommunicator", function() {
	expect(1);
	this.model.loader.post = function(unsuedURL, json, callback) {
		same(json, this.contingent.contingent);
	}.bind(this);
	this.contingent.submitToServer();
});

test("knows what a bad input value would be", function() {
	equals(this.contingent.spentTime(), 15);
	equals(this.contingent.availableTime(), 20);
	ok( ! this.contingent.isInvalidBurnValue(4), 4);
	ok( ! this.contingent.isInvalidBurnValue(-3), -3);
	ok( ! this.contingent.isInvalidBurnValue(5), 5);
	ok( ! this.contingent.isInvalidBurnValue(-15), -15);
	ok(this.contingent.isInvalidBurnValue(6), 6);
	ok(this.contingent.isInvalidBurnValue(5.1), 5.1);
	ok(this.contingent.isInvalidBurnValue(-16), -16);
	ok(this.contingent.isInvalidBurnValue(''), 'empty string');
	ok(this.contingent.isInvalidBurnValue('14'), 14);
	
	ok( ! this.contingent.isInvalidBurnValue('-3'), -3);
	ok( ! this.contingent.isInvalidBurnValue('4'), 4);

	ok(this.contingent.isInvalidBurnValue(NaN), 'NaN');
});

test("throws if invalid input is set", function() {
	expect(1);
	try {
		this.contingent.addOrRemoveTimeFromContingent(6);
	}
	catch (exception) {
		assertMatches(exception, "Invalid burn value");
	}
});

test("didEndInlineEditing saves value", function() {
	this.contingent.didEndInlineEditing(1);
	equals(this.contingent.delta(), 1);
	this.contingent.didEndInlineEditing(6);
	equals(this.contingent.delta(), 1);
});

test("didEndInlineEditing returns correct intermediate value", function() {
	equals(this.contingent.didEndInlineEditing(1), 1);
	same(this.contingent.didEndInlineEditing(15), '');
});

test("didEndInlineEditing will start submit to server", function() {
	expect(1);
	this.model.loader.post = function(){ ok(true); };
	this.contingent.didEndInlineEditing(3);
});

test("didEndInlineEditing will call animation callbacks on the inline editor", function() {
	expect(2);
	this.model.loader.post = function(unusedUrl, unusedJson, optionalDataSinkCallback) {
		optionalDataSinkCallback();
	};
	var animationCallbacks = {
		didStartSaving: function(){
			ok(true, 'didStartSaving');
		},
		didEndSaving: function(){
			ok(true, 'didEndSaving');
		}
	};
	this.contingent.didEndInlineEditing(3, function(){}, animationCallbacks);
});

test("updated values from server will be applied", function() {
	var sensedCallback = null;
	this.model.loader.post = function(url, json, callback) {
		sensedCallback = callback;
	};
	this.contingent.didEndInlineEditing(1, function(){});
	ok(sensedCallback);
	equals(this.contingent.delta(), 1);
	var responseJSON = copyJSON(this.contingent.json);
	responseJSON.content.actual = 18;
	sensedCallback(responseJSON);
	equals(this.contingent.spentTime(), 18);
});

test("only accepts callback value from server if it is not undefined", function() {
	var sensedCallback = null;
	this.model.loader.post = function(url, json, callback) {
		sensedCallback = callback;
	};
	this.contingent.didEndInlineEditing(1, function(){});
	ok(sensedCallback);
	sensedCallback(undefined);
	equals(this.contingent.name(), 'firstContingent');
	sensedCallback({});
	equals(this.contingent.name(), 'firstContingent');
});

test("can create new contingent entry from json", function() {
	equals(this.model.contingents().length, 2);
	this.model.addContingentFromJSON(contingentsFixture({
		name: 'fnord', amount: '23'
	}));
	equals(this.model.contingents().length, 3);
});

test("model knows if user can add contingents", function() {
	ok(this.model.canAddContingents());
	
	var noAdminRights = emptyContingentsFixture();
	noAdminRights.permissions = []; // not 'AGILO_CONTINGENT_ADMIN'
	this.setFixture(noAdminRights);
	
	ok( ! this.model.canAddContingents());
});

test("can push errors to error sink", function() {
	this.model.showError('fnord');
	same(['fnord'], this.messages);
});

// --------------------------------------------------------------


module('contingents view', {
	setup: function() {
		addBacklogAndTestDataCreationMethods(this);
		this.loader = new BacklogServerCommunicator();
		this.loader.stubEverything();
		this.wrapper = contingentsFixture();
		this.contingentJSON = this.wrapper.content[0];
		
		this.model = new Contingents(this.loader);
		this.view = new ContingentsView(this.model);
		
		this.messages = [];
		this.model.registerErrorSink(function(message) {
			this.messages.push(message);
		}.bind(this));
		
		this.setFixture = function(aFixture) {
			this.loader.contingentsLoader.setFixture(aFixture);
			this.loader.startLoadingContingents();
			this.model._contingents = [];
		};
		
		this.setFixture(this.wrapper);
		// Create appropriate containers for the elements tested here
		$('#test-container').html('<div class="toolbar top" /><div id="content" />');
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = "";
		$.fx.off = false;
	}
});

test("can add button to toolbar to show contingents", function() {
	expect(5);
	equals(this.view.toolbarButtonDOM().length, 0);
	equals($('#contingents-button-container').length, 0);
	this.view.addToolbarButton();
	equals($('#contingents-button-container').length, 1);
	equals(this.view.toolbarButtonDOM().length, 1);
	this.view.toggleContingentsDisplay = function(){ ok(true); };
	this.view.toolbarButtonDOM().click();
});

test("toggles class on button if clicked", function() {
	this.view.addToolbarButton();
	ok( ! this.view.toolbarButtonDOM().hasClass('active'));
	this.view.toolbarButtonDOM().click();
	ok(this.view.toolbarButtonDOM().hasClass('active'));
	this.view.toolbarButtonDOM().click();
	ok( ! this.view.toolbarButtonDOM().hasClass('active'));
});

test("can hide div if button is clicked", function() {
	// REFACT: consider to disable animations globally for the testsuite?
	$.fx.off = true;
	
	this.view.addToolbarButton();
	this.view.addContingentsView();
	ok( ! this.view.toolbarButtonDOM().hasClass('active'));
	this.view.toolbarButtonDOM().click();
	ok(this.view.dom().is(':visible'));
	ok(this.view.toolbarButtonDOM().hasClass('active'));
	$('#contingents-close').click();
	
	ok( ! this.view.toolbarButtonDOM().hasClass('active'));
	ok(this.view.dom().is(':hidden'));
});

test("show contingents button is enabled even when no contingents are available", function() {
	this.view.addToolbarButton();
	ok( ! this.view.toolbarButtonDOM().hasClass('disabled'));
	
	$('.toolbar').html('');
	this.setFixture(emptyContingentsFixture());
	this.view.addToolbarButton();
	ok( ! this.view.toolbarButtonDOM().hasClass('disabled'));
});

test("can show contingents div", function() {
	equals(this.view.dom().length, 0);
	this.view.addContingentsView();
	equals(this.view.dom().length, 1);
});

test("can show and hide contingents table", function() {
	// REFACT: consider to disable animations globally for the testsuite
	$.fx.off = true;
	
	this.view.addToolbarButton();
	equals(this.view.dom().length, 0);
	this.view.addContingentsView();
	this.view.toggleContingentsDisplay(true);
	ok(this.view.dom().is(':visible'));
	this.view.toggleContingentsDisplay(false);
	ok(this.view.dom().is(':hidden'));
	this.view.toggleContingentsDisplay(true);
	ok(this.view.dom().is(':visible'));
	this.view.toggleContingentsDisplay(false);
	ok(this.view.dom().is(':hidden'));
});

test("shows all the values for the contingent table", function() {
	this.view.addContingentsView();
	equals(this.view.dom().find('thead tr td').length, 6);
	equals(this.view.dom().find('tbody tr').length, 2);
	var line = this.view.dom().find('tbody tr:first');
	equals(line.find('.name').text(), 'firstContingent');
	equals(line.find('.availableTime').text(), '20');
	equals(line.find('.spentTime').text(), '15');
	same(line.find('.burnTime').text(), "");
	equals(line.find('.remainingTime').text(), '5');
	equals(line.find('.bar').css('width'), '75%');
	equals(line.find('.progressText').text(), '75%');
});

test("can update the contingents view values", function() {
	this.view.addContingentsView();
	this.contingentJSON.content.name = 'foo';
	this.contingentJSON.content.amount = 40;
	this.contingentJSON.content.actual = 10;
	
	this.view.updateView();
	var line = this.view.dom().find('tbody tr:first');
	equals(line.find('.name').text(), 'foo');
	equals(line.find('.availableTime').text(), '40');
	equals(line.find('.spentTime').text(), '10');
	same(line.find('.burnTime').text(), "");
	equals(line.find('.remainingTime').text(), '30');
	equals(line.find('.bar').css('width'), '25%');
	equals(line.find('.progressText').text(), '25%');
});

test("will show error if entered value is invalid", function() {
	this.view.addContingentsView();
	this.view.dom('.burnTime:first').click().find(':input').val('fnord').submit();
	same(this.messages.length, 1);
	assertMatches(this.messages[0], /Invalid value/);
});

test("can edit inline the spent time", function() {
	this.view.addContingentsView();
	equals(this.view.dom(':input').length, 0);
	this.view.dom('tbody tr:first .burnTime').click();
	equals(this.view.dom(':input').length, 1);
});

test("does not add editor if you have insufficient rights", function() {
	this.contingentJSON.permissions = []; // only for the first editor
	this.setFixture(this.wrapper);
	this.view.addContingentsView();
	this.view.dom('.burnTime:eq(0)').click();
	equals(this.view.dom(':input').length, 0);
	this.view.dom('.burnTime:eq(1)').click();
	equals(this.view.dom(':input').length, 1);
});

test("can update contingent via gui", function() {
	expect(2);
	this.view.addContingentsView();
	var contingent = this.model.contingents()[0];
	contingent.didEndInlineEditing = function(newValue, unusedUpdateGUICallback) {
		equals(newValue, 2);
		return newValue;
	}.bind(this);
	
	this.view.dom('.burnTime:first').click();
	same(this.view.dom(':input').val(), '');
	
	this.view.dom(':input').val(2).submit();
});

test("can update gui values after callback", function() {
	this.view.addContingentsView();
	var contingent = this.model.contingents()[0];
	var savedCallback = null;
	contingent.didEndInlineEditing = function(newValue, callback) {
		savedCallback = callback;
		return newValue;
	};
	
	this.view.dom('.burnTime:first').click();
	equals(this.view.dom(':input').val(), '');
	this.view.dom(':input').val(2).submit();
	
	contingent.contingent.actual = 18;
	savedCallback();
	equals(this.view.dom('.spentTime:first').text(), 18);
});

test("can expose add contingent window", function() {
	this.view.showAddNewContingentDialog();
	assertMatches(agilo.exposedDOM('form h1').text(), /Add a contingent/);
});

test("can cancel add contingent window", function() {
	this.view.showAddNewContingentDialog();
	agilo.exposedDOM('#cancel').click();
	equals(agilo.exposedDOM().children().length, 0);
});

test("can submit new contingents to json call", function() {
	expect(1);
	this.view.showAddNewContingentDialog();
	agilo.exposedDOM()
		.find('#name').val('fnord').end()
		.find('#amount').val('23');
	this.loader.putCreateContingent = function(json) {
		same(json, { name: 'fnord', amount: '23' });
	}.bind(this);
	agilo.exposedDOM(':submit').click();
});

test("can add new line after initial rendering", function() {
	this.view.addContingentsView();
	var contingent = this.model.addContingentFromJSON(contingentFixture({
		name: 'fnord', amount: '23'
	}));
	equals($('.contingent-container tbody tr').length, 2);
	this.view.addContingent(contingent);
	equals($('.contingent-container tbody tr').length, 3);
	var dom = $('.contingent-container tbody tr:last');
	equals(dom.find('.name').text(), 'fnord');
	equals(dom.find('.availableTime').text(), '23');
});

test("new lines added later will also be inline editable", function() {
	this.view.addContingentsView();
	var contingent = this.model.addContingentFromJSON(contingentFixture({
		name: 'fnord', amount: '23'
	}));
	this.view.addContingent(contingent);
	ok(this.view.dom('.burnTime:last').data('events').click, "should have events attached");
});


test("submit hides exposed window", function() {
	this.view.showAddNewContingentDialog();
	this.view.handleSubmitAddNewContingentsDialog();
	equals(agilo.exposedDOM().children().length, 0);
});

test("will only enable add button if user has the required rights", function() {
	var noAdminRights = emptyContingentsFixture();
	noAdminRights.permissions = []; // not 'AGILO_CONTINGENT_ADMIN'
	this.setFixture(noAdminRights);
	this.view.addContingentsView();
	var button = this.view.dom().find('#buttonBottomAdd');
	ok(button.is('.disabled'), "should be disabled");
});

test("can enable/disable contingents view", function() {
	this.view.addContingentsView();
	
	this.view.setIsEditable(true);
	ok( ! this.view.dom('#buttonBottomAdd').is('.disabled'));
	ok(this.view.dom('.burnTime:first').data('events').click);
	
	this.view.setIsEditable(false);
	ok(this.view.dom('#buttonBottomAdd').is('.disabled'));
	equals(this.view.dom('.burnTime:first').data('events'), undefined);
});


// test("will show error message if invalid value is set", function() {
// 	ok(false);
// });
// 
// test("will reset to correct default values after an error", function() {
// 	ok(false);
// });
