function BacklogFiltering(aBacklog, anApplyFilteringCallback) {
	this.backlog = aBacklog;
	this.applyFilteringCallback = anApplyFilteringCallback;
	
	// REFACT: we would like to remove these variables - the value
	//  is needed by the burndown chart to create the correct url though.
	this._attributeFilteringKey = undefined;
	this._attributeFilteringValue = undefined;
	
	this.filterClosures = {
		alwaysShowTotallingRow: this.showTotallingRowFilter
	};
}

//Sent after a new filter was applied so other components can adapt
BacklogFiltering.DID_CHANGE_FILTER_SETTINGS = 'DID_CHANGE_FILTER_SETTINGS';
BacklogFiltering.MUST_SHOW_ITEM = "MUST_SHOW_ITEM";
BacklogFiltering.SHOULD_NOT_SHOW_ITEM = "SHOULD_NOT_SHOW_ITEM";
BacklogFiltering.CAN_SHOW_ITEM = "CAN_SHOW_ITEM";

$.extend(BacklogFiltering.prototype, {
	
	// Public entry point to the filtering .....................
	
	applyFiltering: function() {
		// REFACT: consider to switch the actual filtering implementation to also use DID_CHANGE_FILTER_SETTINGS - which means enhancing it to also transport the attributeFilteringKey()
		if (this.applyFilteringCallback)
			this.applyFilteringCallback(this);
		
		$.observer.postNotification(BacklogFiltering.DID_CHANGE_FILTER_SETTINGS, this);
	},
	
	shouldShow: function(aTicket) {
		var mustNotShow = false;
		var mustShow = false;
		$.each(this.filterClosures, function(aName, aClosure) {
			if (aClosure(aTicket) === BacklogFiltering.SHOULD_NOT_SHOW_ITEM)
				mustNotShow = true;
			else if (aClosure(aTicket) === BacklogFiltering.MUST_SHOW_ITEM)
				mustShow = true;
		});
		
		if (mustShow)
			return true;
		else 
			return ! mustNotShow;
	},
	
	addToDOM: function() {
		this.addFilterPopupIfNecessary();
		this.addFilterButtons();
	},
	
	// Filters .......... ............................
	
	setShouldShowOnlyMyItems: function(shouldShow) {
		if ( ! shouldShow)
			this.filterClosures.showMyItems = this.noopFilter;
		else {
			var loggedInUser = this.backlog.loader.loggedInUser();
			this.filterClosures.showMyItems = function(aTicket) {
				var canShow = loggedInUser === aTicket.json.owner;
				if (aTicket.json.drp_resources !== undefined)
					canShow = canShow || aTicket.json.drp_resources.indexOf(loggedInUser) > -1;
				
				if (canShow)
					return BacklogFiltering.CAN_SHOW_ITEM;
				else
					return BacklogFiltering.SHOULD_NOT_SHOW_ITEM;
			};
		}
	},
	
	setShouldHideClosedItems: function(shouldHide) {
		if ( ! shouldHide)
			this.filterClosures.hideClosedItems = this.noopFilter;
		else
			this.filterClosures.hideClosedItems = function(aTicket) {
				var ticketIsClosed = aTicket.hasKey("status") && aTicket.isSameValueForKey("closed", "status");
				
				if (ticketIsClosed)
					return BacklogFiltering.SHOULD_NOT_SHOW_ITEM;
				else
					return BacklogFiltering.CAN_SHOW_ITEM;
			};
	},
	
	genericAttributeFilter: function(aTicket) {
		if ('' === this.attributeFilteringValue()) // special '' means no filter
			return BacklogFiltering.CAN_SHOW_ITEM;
		
		if (aTicket.hasKey(this.attributeFilteringKey())
			&& aTicket.isSameValueForKey(this.attributeFilteringValue(),  this.attributeFilteringKey()))
			return BacklogFiltering.CAN_SHOW_ITEM;
		else
			return BacklogFiltering.SHOULD_NOT_SHOW_ITEM;
	},
	
	noopFilter: function(unusedTicket) {
		return BacklogFiltering.CAN_SHOW_ITEM;
	},
	
	showTotallingRowFilter: function(aTicket) {
		if (aTicket.isSameValueForKey('story', 'type') && aTicket.id() === -2)
			return BacklogFiltering.MUST_SHOW_ITEM;
		else
			return BacklogFiltering.CAN_SHOW_ITEM;
	},
	
	// Serialization ...........................................................
	
	toJSON: function() {
		var filters = {};
		$.each(this.filterClosures, function(aName, aClosure) {
			if (aClosure === this.noopFilter || 'alwaysShowTotallingRow' === aName)
				return;
			
			if ('attributeFilter' === aName)
				filters[this.attributeFilteringKey()] = this.attributeFilteringValue();
			else
				filters[aName] = true;
		}.bind(this));
		return JSON.stringify(filters);
	},
	
	fromJSON: function(json) {
		this.resetAllFilters();
		
		try {
			var filterSpecification = JSON.parse(json);
		} catch(error) {
			// silently ignore errors from invalid cookies
			return;
		}
		$.each(filterSpecification, this.activateFilterForKey.bind(this));
	},
	
	// Helper methods ...........................................
	
	possibleFilterCriterias: function() {
		return this.backlog.possibleFilterCriteriaForAttribute(this.attributeFilteringKey());
	},
	
	attributeFilteringValue: function() {
		if (-1 === $.inArray(this._attributeFilteringValue, this.possibleFilterCriterias()))
			return '';
		
		return this._attributeFilteringValue;
	},

	setAttributeFilteringValue: function(aValue) {
		this._attributeFilteringValue = aValue;
		this.filterClosures.attributeFilter = this.genericAttributeFilter.bind(this);
	},
		
	attributeFilteringKey: function() {
		return this._attributeFilteringKey;
	},

	setAttributeFilteringKey: function(aTicketAttributeName) {
		this._attributeFilteringKey = aTicketAttributeName;
	},
	
	isAttributeFilteringActive: function() {
		return !! this.attributeFilteringKey();
	},
	
	isAttributeFilteringDisabled: function() {
		return ! this.isAttributeFilteringActive();
	},
	
	isFilterActive: function(key) {
		var filterClosure = this.filterClosures[key];
		return (undefined !== filterClosure) && (this.noopFilter !== filterClosure);
	},
	
	isShowMyItemsFilterActive: function() {
		return this.isFilterActive('showMyItems');
	},
	
	isHideClosedItemsFilterActive: function() {
		return this.isFilterActive('hideClosedItems');
	},
	
	activateFilterForKey: function(filterKey, filterValue) {
		if ('showMyItems' === filterKey && this.backlog.loader.isUserLoggedIn()) {
			this.setShouldShowOnlyMyItems(true);
		} else if ('hideClosedItems' === filterKey)
			this.setShouldHideClosedItems(true);
		else if (this.attributeFilteringKey() === filterKey) {
			this.setAttributeFilteringValue(filterValue);
		}
	},
	
	resetAllFilters: function() {
		this.setAttributeFilteringValue(null);
		this.filterClosures = {
			alwaysShowTotallingRow: this.showTotallingRowFilter
		};
	},
	
	registerForCallbackAfterEachTicketChange: function() {
		Ticket.registerCallbackAfterEachServerReturn(this.didChangeTickets.bind(this));
	},
	
	// GUI for filter by attribute .......................................
	 
	addFilterPopupIfNecessary: function(optionalTarget) {
		if (this.isAttributeFilteringDisabled())
			return;
		
		this.addFilterPopup(optionalTarget);
	},
	
	addFilterPopup: function(optionalTarget) {
		this.registerForCallbackAfterEachTicketChange();
		
		var popup = $('<form id="filter-attribute"><select id="filter-attribute-popup"></select></form>');
		var that = this;
		popup.find('select').change(function(anEvent){
			that.setAttributeFilteringValue($(this).val());
			that.applyFiltering();
		});
		
		$(optionalTarget || '.toolbar').append(popup);
		this.updateFilterPopupValues();
	},
	
	didChangeTickets: function() {
		if (this.isAttributeFilteringDisabled())
			return;
		
		this.updateFilterPopupValues();
		this.applyFiltering();
	},
	
	updateFilterPopupValues: function() {
		if (this.isAttributeFilteringDisabled())
			return;
		
		var options = this.possibleFilterCriterias();
		var htmlizedOptions = '<option value="">Filter by…</option>' + $.map(options, function(element){
			var selectedHTML = '';
			if (this.attributeFilteringValue() === element)
				selectedHTML = ' selected="selected"';
			return '<option value="' + element + '" ' + selectedHTML + '>' + element + '</option>';
		}.bind(this)).join('');
		this.popUpDOM().html(htmlizedOptions);
	},
	
	// GUI for filtering by open/closed and mine/others .......................................
	
	popUpDOM: function() {
	    return $('#filter-attribute-popup');
	},
	
	addFilterButtons: function() {
		var that = this;

		var onlymineOptions = {
				id : 'show-onlymine-button',
				tooltip : 'Hide or Show my tickets',
				title : 'My Tickets',
				isEnabled: that.backlog.loader.isUserLoggedIn(),
				isActive: that.isShowMyItemsFilterActive(),
				clickCallback: function(isActive){
					that.setShouldShowOnlyMyItems(isActive);
					that.applyFiltering();
				 }
			 };

		var hideClosedOptions = {
				id : 'hide-closed-button',
				tooltip : 'Show or Hide closed tickets',
				title : 'Done Tickets',
				isActive: that.isHideClosedItemsFilterActive(),
				clickCallback: function(isActive){
					that.setShouldHideClosedItems(isActive);
					that.applyFiltering();
				}
			 };

		agilo.createToolbarButtons(
				[onlymineOptions, hideClosedOptions],
				{id: "filter-button-container"});
	},

	missingCommaErrorPreventer:''
});