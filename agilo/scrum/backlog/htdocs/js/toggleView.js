
/// Toggle between Sprint Backlog, the new Backlog and the Whiteboard.
function ToggleView(aBacklogLoader) {
	this.loader = aBacklogLoader;
	this._allowedViews = [];
};

$.extend(ToggleView.prototype, {
	
	initialize: function() {
		this.loader.startLoadingAlternativeViews(function(returnedData) {
			this.allowedViews(returnedData);
			this.display();
		}.bind(this));
	},
	
	backlogInfo: function() {
		return this.loader.info();
	},
	
	isBadBacklogInfo: function() {
		// {"sprint_or_release": "Foo", "type": "sprint", "name": "Sprint Backlog"};
		var info = this.backlogInfo();
		return ! (
			info
			&& info.sprint_or_release
			&& info.type
			&& info.name
		);
	},
	
	allowedViews: function(optionalSetAllowedViews) {
		if (optionalSetAllowedViews)
			this._allowedViews = this.filterOutUnwantedViews(optionalSetAllowedViews);
		
		return this._allowedViews;
	},
	
	filterOutUnwantedViews: function(someViewNames) {
		return $.grep(someViewNames, function(view) {
			if ('sprint' !== this.backlogInfo().type
				&& 'whiteboard' === view)
				return false;
			
			return -1 !== $.inArray(view, ['new_backlog', 'whiteboard']);
		}.bind(this));
	},
	
	shouldShowSwitcher: function() {
		if (this.isBadBacklogInfo())
			return false;
		
		var views = this.allowedViews();
		
		if (0 === views.length)
			return false;

		if (1 === views.length)
			return false;
		
		return true;
	},
	
	shouldShowSwitcherPart: function(aViewName) {
		if ('sprint' !== this.backlogInfo().type
			&& 'whiteboard' === aViewName)
			return false;
		
		return -1 !== $.inArray(aViewName, this.allowedViews());
	},
	
	urls: function() {
		return (new URLGenerator(this.backlogInfo())).backlogViewURLs();
	},
	
	display: function() {
		if ( ! this.shouldShowSwitcher())
			return;
		
		this.addToolbarButtons();
		this.setInitialState();
	
		// dwt: why should this go? it is empty anyway afaik
		// g: probably because of IE 7
		$("#ctxtnav").remove();
	},
	
	generateButtonOptions: function() {
		var buttonOptions = [];
		
		if (this.shouldShowSwitcherPart('new_backlog'))
			buttonOptions.push({
				id : 'backlog-button',
				tooltip : 'Sprint Backlog view',
				isPushButton: true,
				allowDefaultAction: true,
				href: this.urls().new_backlog
			 });
		
		if (this.shouldShowSwitcherPart('whiteboard'))
			buttonOptions.push({
				id : 'whiteboard-button',
				tooltip : 'Sprint White Board view',
				isPushButton: true,
				allowDefaultAction: true,
				href: this.urls().whiteboard
			 });

		return buttonOptions;
	},
	
	addToolbarButtons: function() {
		agilo.createToolbarButtons(this.generateButtonOptions(), {
			id: 'toggle-button-container',
			isComposed: true
		});
	},
	
	setInitialState: function() {
		var button = this.currentActiveToggleState();
		$(button).addClass("active");
	},
	
	currentActiveToggleState: function() {
		if (this.isPlanBoard())
			return '#whiteboard-button';
		else
      return '#backlog-button';
	},
	
	isPlanBoard: function() {
		return true === window.IS_WHITEBOARD;
	},
	
	isBacklog: function() {
		return true === window.IS_BACKLOG;
	},
	
	missingCommaErrorPreventer:''
});

