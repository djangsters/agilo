module('message', {
	setup: function(){
		this.message = new Message();
	},
	teardown: function(){
		this.message.hideMessage();
		$('#test-container *').remove();
	}
});

test("can display error", function() {
	this.message.error('fnord');
	equals($('#message p').text(), 'fnord');
});

test("can display notice", function() {
	this.message.notify('fnord');
	equals($('#message p').text(), 'fnord');
});

test("will remove itself from the dom when no longer needed", function() {
	this.message.error('fnord');
	this.message.hideMessage();
	equals($('#message').length, 0);

	this.message.notify('fnord');
	this.message.hideMessage();
	equals($('#message').length, 0);
});

test("if a message is shown, every other message is scraped", function() {
	this.message.error('fnord');
	this.message.error('fnordifnord');
	equals($('#message p').text(), 'fnord');
	this.message.hideMessage();
	
	this.message.notify('fnordifnord');
	this.message.error('fnord');
	equals($('#message p').text(), 'fnordifnord');
});

test("doesn't try to render html in messages", function() {
	var html = '<div><p>oh yeah</p></div>';
	this.message.error(html);
	equals($('#message p').text(), html);
});

test("can retrieve past messages", function() {
	equals(this.message.pastMessages().length, 0);
	this.message.error('fnord');
	equals(this.message.pastMessages().length, 1);
	var past_message = this.message.pastMessages()[0];
	equals(past_message.text, 'fnord');
	this.message.notify('notify fnord');
	equals(this.message.pastMessages().length, 2);
});

test("can clear past messages", function() {
	this.message.error('fnord');
	equals(this.message.pastMessages().length, 1);
	this.message.clearPastMessages();
	equals(this.message.pastMessages().length, 0);
});

test("can prevent message display", function() {
	this.message.preventDisplay();
	this.message.error('fnord');
	equals($('#message').length, 0);
});
