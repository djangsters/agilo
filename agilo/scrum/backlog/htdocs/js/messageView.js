function Message() {
	/**
	 * Display a notification - either an error or a message.
	 */
	this._pastMessages = [];
	this.isCurrentlyShowingAMessage = false;
	this.isDisplayEnabled = true;
	this.wasInModalModeBefore = false;
};

Message.ERROR = 'MESSAGE_ERROR';
Message.NOTIFY = 'MESSAGE_NOTIFY';

$.extend(Message.prototype, {
	
	// Public methods ....................................
	
	error: function(message) {
		this.logMessageAsType(message, Message.ERROR);
		this.showMessageAsError(message, true);
	},
	
	notify: function(message) {
		this.logMessageAsType(message, Message.NOTIFY);
		this.showMessageAsError(message, false);
	},
	
	pastMessages: function() {
		return this._pastMessages;
	},
	
	clearPastMessages: function() {
		this._pastMessages = [];
	},
	
	preventDisplay: function() {
		this.isDisplayEnabled = false;
	},
	
	// Private methods .....................................
	
	showMessageAsError: function(aMessage, asError) {
		if ( ! this.isDisplayEnabled || this.isCurrentlyShowingAMessage)
			return;
		this.isCurrentlyShowingAMessage = true;
		
		this.render(aMessage, asError);
		this.attachBehaviour(asError);
	},
	
	render: function(aMessage, asError) {
		$("body").append(this.template(asError));
		$('#message p').text(aMessage);
	},
	
	template: function(isError) {
		var type = (isError) ? 'error' : 'notification';
		
		var template = '<div id="message" class="' + type + '">';
		if (isError)
			template += '<h3>An error occurred.</h3>';
		template += '<p></p>'; // here goes the message
		if (isError)
			template += '<form><input type="button" value="Ok" /></form>';
		template += '</div>';
		
		return template;
	},
	
	logMessageAsType: function(text, type) {
		var messageToLog = {
			text: text,
			type: type
		};
		this._pastMessages.push(messageToLog);
	},
	
	attachBehaviour: function(asError) {
		if (asError)
			this.errorBehaviour();
		else
			this.notificationBehaviour();
	},
	
	errorBehaviour: function() {
		// An error requires user interaction and a UI lock
		var self = this;
		// Button action
		$("#message input").click(function(anEvent) {
			anEvent.preventDefault();
			self.hideMessage();
		});
		// Display
		this.wasInModalModeBefore = $("#modal").is(':visible');
		$("#modal").show();
		$("#message").show();
	},
	
	notificationBehaviour: function() {
		// A message displays for a period and disappears, requires no user interaction
		var self = this;
		$("#message")
			.slideDown('fast')
			.animate({ pitch: "none" }, 5000)
			.slideUp('fast',function() {
				self.hideMessage();
			});
	},
	
	hideMessage: function() {
		this.isCurrentlyShowingAMessage = false;
		if (this.wasInModalModeBefore === false) {
			$("#modal").hide();
		}
		$("#message").remove();
	}
	
});
