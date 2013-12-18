module("Confirm Commitment", {
	setup: function() {
		var info = wrapContentInInfo({});
		info.permissions.push('AGILO_CONFIRM_COMMITMENT');
		this.loader = new BacklogServerCommunicator(info);
		this.loader.stubEverything();
		
		this.controller = new agilo.CommitmentConfirmation(this.loader);
		this.controller.message.preventDisplay();
		
		$('#test-container').append('<div class="toolbar top" />');
	},
	teardown: function() {
		BacklogController.callbacksForDidLoad = [];
		BacklogController.callbacksForAfterRendering = [];
		$('#test-container')[0].innerHTML = '';
	}
});

test("can add button to confirm commitment", function() {
	equals($('#commit-button-container').length, 0);
	this.controller.addToDOM();
	equals($('#commit-button-container li').length, 1);
	ok( ! $('#commit-button-container li').hasClass('disabled'));
	ok(-1 === $('#commit-button-container li a').attr('title').indexOf('more than 24h ago'));
});

test("can add disabled button when not allowed to confirm commitment", function() {
	this.loader.permissions().pop();
	this.controller.addToDOM();
	equals($('#commit-button-container li').length, 1);
	ok($('#commit-button-container li').hasClass('disabled'));
	ok(-1 !== $('#commit-button-container li a').attr('title').indexOf('more than 24h ago'));
});

test("can send confirm request to server on click", function() {
	this.controller.addToDOM();
	
	expect(1);
	this.loader.post = function(url, json, callback) {
		ok(true);
	}.bind(this);

	$('#commit-button-container a').click();
});

test("callback posts burndown reload notification", function() {
	expect(1);
	$.observer.addObserver('DID_CHANGE_BURNDOWN_DATA', function() {
		ok(true);
	});
	this.controller.didConfirmCommitmentCallback();
});


test("callback can display message on success", function() {
	equals(this.controller.message.pastMessages().length, 0);
	this.controller.didConfirmCommitmentCallback();
	var pastMessages = this.controller.message.pastMessages();
	equals(pastMessages.length, 1);
	equals(pastMessages[0].text, "You have confirmed the commitment for this sprint.");
});

