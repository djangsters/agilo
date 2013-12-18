/*
Target: We want to have one widget-instance per row, so we have a place to stick functionality that doesn't belong into the controller or the model.

The BacklogView should be able to map between an arbitrary dom element and the view item this belongs to.
Each View should know the backlog item it belongs to.
*/

// IE-Fix for jquery ui issue: http://dev.jqueryui.com/ticket/4333
// This fixes the problem that nested draggables always drag together with their parents
// This workaround should not be necessary from jquery ui 1.8 forward
$.extend($.ui.sortable.prototype, {
	_mouseCapture: (function (orig) {
		return function (event) {
			var result = orig.call(this, event);
			if (result && $.browser.msie)
				event.stopPropagation();
			return result;
		};
	})($.ui.sortable.prototype._mouseCapture)
});

// REFACT: this either needs another object to encapsulate the whole page, or methods that handle 
// stuff outside of the actual ticket list. I'd actually prefer to move that into it's own object.
BacklogView = function(){
	// REFACT: consider to move the subviews / superviews relation to a root view object
	this.subviews = [];
	this.configuredColumns = ['id', 'summary', 'status'];
	this.columnTitles = {};
	this.callbacksForColumnRendering = [];
	this.isInlineEditingActive = false;
	this.ticketFieldOptionGenerator = new TicketFieldOptionGenerator();
	this.backlog = null;
};

$.extend(BacklogView.prototype, {
	
	setBacklog: function(aBackog) {
		this.backlog = aBackog;
		this.backlog.addTicketAddingOrRemovingObserver(this, this.didAddOrRemoveTicketFromBacklog);
		this.backlog.addSortingChangedObserver(this, this.didChangeOrderOfTickets);
		this.ticketFieldOptionGenerator.setBacklogInfo(this.backlog.loader.info());
	},
	
	setController: function(aController) {
		this.controller = aController;
	},
	
	// Traversing the view hierarchy .....................................
	
	traversePreOrder: function(aFunction) {
		$.each(this.subviews, function(index, subview){
			subview.traversePreOrder(aFunction);
		});
	},
	
	firstViewForTicket: function(aTicket) {
		return this.viewsForTicket(aTicket)[0];
	},
	
	viewsForTicket: function(aTicket) {
		var foundViews = [];
		this.traversePreOrder(function(aView){
			if (aView.ticket === aTicket)
				foundViews.push(aView);
		});
		return foundViews;
	},
	
	// Generic helpers ....................................................
	
	dom: function(optionalChildSelector) {
		// REFACT: consider to extract .backlog to a method, instance variable - is used about 5 to 6 times now
		if (optionalChildSelector)
			return $('.backlog').find(optionalChildSelector);
		else
			return $('.backlog');
	},
	
	// copied from ContainerView, because I can't easily make that a superclass for BacklogView
	removeSubView: function(aChildView) {
		var index = $.inArray(aChildView, this.subviews);
		if ( -1 === index)
			return;
		
		this.subviews.splice(index, 1); // remove it
		this.showOrHideTotallingRowIfNecessary();
	},
	
	// Dealing with Columns
	
	setConfiguredColumns: function(arrayOfIdentifiers, dictionaryOftranslations) {
		this.configuredColumns = arrayOfIdentifiers;
		this.columnTitles = dictionaryOftranslations;
	},
	
	keyForAlternativeColumnContent: function(aTicket, keyOrKeys) {
        // REFACT: add infrastructure for special casing?
        if ('id' === keyOrKeys && -2 === aTicket.id())
            return 'total_number_of_tickets';

		if ( ! $.isArray(keyOrKeys))
			return keyOrKeys;
		
		var candidates = $.grep(keyOrKeys, aTicket.hasKey.bind(aTicket));
		if (candidates.length >= 1)
			return candidates[0];
		
		// If nothing matches, first key is the fallback
		return keyOrKeys[0];
	},
	
	/// performance critical method, called very often during rendering
	isNumericColumn: function(aColumnKey) {
		if ( ! this.backlog || ! this.backlog.tickets())
			return false; // No way to tell - so it's not numeric
		
		function isNotNumeric(aValue) {
			if ( ! aValue)
				return false; // empty fields are always ok
			
			if ('number' === typeof aValue)
				return false;
			
			if ('string' === typeof aValue && aValue.length > 0)
				return isNaN(parseFloat(aValue));
			
			return true;
		}
		
		function isNumericColumn(aColumn) {
			for (var i = 0; i < this.backlog.tickets().length; i++) {
				var ticket = this.backlog.tickets()[i];
				var key = this.keyForAlternativeColumnContent(ticket, aColumnKey);
				if (isNotNumeric(ticket.valueForKey(key)))
					return false;
			}
			return true;
		}
		
		// Without this cache we hit the slow script warning on ie 7 & 8 for bigger backlogs. :-)
		if ( ! this.isNumericCache)
			this.isNumericCache = {};
		
		if (undefined !== this.isNumericCache[aColumnKey])
			return this.isNumericCache[aColumnKey];
		
		this.isNumericCache[aColumnKey] = isNumericColumn.bind(this)(aColumnKey);
		return this.isNumericCache[aColumnKey];
	},
	
	// Rendering a backlog ...................................
	
	renderBacklog: function(aBackog) {
		$("#backlog").append(this.htmlForBacklog(aBackog));
		this.refreshTotallingRow();
		$('head').append(this.cssForBacklog());
		$("#loader").remove();
		// Fix for the overlapped drawing of rows after loading the backlog (on fairly small resolutions 1024x768)
		forceIE7Redraw('[id^=ticketID] .id');
		
		// Fixes drawing issue that would move cell inline editable fields a few pixel to the right when mousing out of them (ie7 only)
		if ($.browser.msie && $.browser.version < 8)
			$('[id^="ticketID"]').live('mouseout', function() { forceIE7Redraw(this); });
	},
	
	cssForBacklog: function() {
		// configured columns need to be set before this call!
		// Assumes: 1. Column: id, 2. Column: Stretchy, rest takes up 70% of all space
		var columnSizer = new BacklogColumnLayouter();
		columnSizer.setNumberOfColumns(this.configuredColumns.length);
		columnSizer.setLeftAnchoredColumnsWithWidths(1, [40]);
		columnSizer.setPercentSizedColumnsLimit(70);
		return columnSizer.generateCSSWithColumnNames(this.configuredColumns);
	},
	
	htmlForBacklog: function(aBacklog) {
		// REFACT: this should go - but currently quite some tests depend on this (though production does not)
		this.setBacklog(aBacklog);
		this.subviews = this.createViewHierarchy(this.backlog.topLevelContainers());
		this.addTotallingRow();
		return this.headerToHTML() + this.hierarchyToHTML();
	},
	
	headerToHTML: function() {
		return '<div class="backlog-header">'
			+ $(this.configuredColumns).map(function(index, each){
				var columnClass = each;
				if ($.isArray(each))
					columnClass = each.join(' ');
				return '<span class="' + columnClass +'">' + this.humanReadableColumnName(each) + '</span>';
			}.bind(this)).get().join('')
			+ '</div>';
	},
	
	humanReadableColumnName: function(aKeyOrKeys) {
		if (undefined !== this.columnTitles[aKeyOrKeys])
			return this.columnTitles[aKeyOrKeys];
		
		if ($.isArray(aKeyOrKeys)) {
			var titles = $.map(aKeyOrKeys, function(key) { return this.columnTitles[key]; }.bind(this));
			if (titles.length > 0)
				return titles[0];
		}
		
		// Fallback
		return aKeyOrKeys;
	},
	
	createViewHierarchy: function(backlogItems) {
		var subviews = [];
		$.each(backlogItems, function(index, ticket){
			var subview = this.createViewForTicket(ticket);
			if (ticket.isContainer() && ticket.hasChildren())
				subview.setSubviews(this.createViewHierarchy(ticket.children()));
			subviews.push(subview);
		}.bind(this));
		return subviews;
	},
	
	createViewForTicket: function(aTicket) {
		var viewClass = (aTicket.isContainer()) ? ContainerView : LeafView;
		return new viewClass(this, aTicket);
	},
	
	hierarchyToHTML: function() {
		var html = [];
		html.push('<div class="sprint backlog">');
		$.each(this.subviews, function(index, subview){
			html.push(subview.toHTML());
		});
		html.push('</div>');
		return html.join('');
	},
	
	// --- totalling row -------------------------------------------------------
	
	preferredColumnName: function(columnSpecification) {
		if (typeof columnSpecification === "string")
			return columnSpecification;
		return columnSpecification[0];
	},
	
	columnNamesForTotalling: function(ticketJSON) {
		var columnNames = [];
		for (var i=0; i < this.configuredColumns.length; i++) {
			var column = this.preferredColumnName(this.configuredColumns[i]);
			if (undefined !== ticketJSON[column])
				continue;
			columnNames.push(column);
		}
		return columnNames;
	},
	
	fakeTicketForTotallingRow: function(optionalFilter) {
		var fakeJSON = {
			id: -2, type: 'story', 
			// all trac standard fields should be listed here so there are 
			// never summed up. It would be nice if we could get this list from
			// a central place (or even better actually *know* if a column might
			// contain numbers instead of checking every single value.
			summary: 'Totals', description: '', owner: '', 
			priority: '', severity: '', component: '', milestone: '',
			drp_resources: '', sprint: '',  
			outgoing_links: [], incoming_links: [], total_number_of_tickets: 0
		};
		var columnNames = this.columnNamesForTotalling(fakeJSON);
		for (var i=0; i < columnNames.length; i++) {
			var columnName = columnNames[i];
			fakeJSON[columnName] = this.backlog.computeTotal(columnName , optionalFilter);
		}
        fakeJSON['total_number_of_tickets'] = this.backlog.numberOfTicketsWithParentsMatchingFilter(optionalFilter);
		return this.backlog.ticketFromJSON(fakeJSON);
	},
	
	totallingRow: function() {
		return $.grep(this.subviews, function(item, index) { return item.ticket.id() === -2; })[0];
	},
	
	updateTotals: function(optionalFilter) {
		var totallingRow = this.totallingRow();
		if ( ! totallingRow )
			return;
		totallingRow.ticket = this.fakeTicketForTotallingRow(optionalFilter);
		totallingRow.updateRenderedValuesFromTicket();
	},
	
	addTotallingRow: function() {
		this.addNewTopLevelTicket(this.fakeTicketForTotallingRow());
	},
	
	refreshTotallingRow: function(optionalFilter) {
		this.showOrHideTotallingRowIfNecessary();
		this.updateTotals(optionalFilter);
	},
	
	visibleSubViews: function() {
		return _.filter(this.subviews, function(aView) {
			return aView.dom().is(':visible');
		});
	},
	
	showOrHideTotallingRowIfNecessary: function() {
		var totallingRow = this.totallingRow();
		var visibleSubViews = this.visibleSubViews();
		
		if (undefined === totallingRow)
			return;
		
		var showTotallingRow = ! (visibleSubViews.length === 1 && totallingRow === visibleSubViews[0]);
		this.totallingRow().dom().toggle(showTotallingRow);
	},
	
	// --- column rendering callbacks ------------------------------------------
	
	registerCallbackForColumnRendering: function(aCallback) {
		this.callbacksForColumnRendering.push(aCallback);
	},
	
	doCallbackForColumnRendering: function(aTicket, aColumnIDName) {
		var htmlFromCallbacks = $.map(this.callbacksForColumnRendering, function(callback) {
			return callback(aTicket, aColumnIDName);
		}).join('');
		
		if ('' === htmlFromCallbacks)
			return '';
		
		return '<div class="inlineEditorButtons">' + htmlFromCallbacks + '</div>';
	},
	
	/**
	 * Will not do anything if the ticket is already rendered
	 * Will add all missing parent tickets
	 * Will handle multi-linked tickets
	 */
	addNewTicket: function(aTicket) {
		if ( ! aTicket.hasParents())
			this.addNewTopLevelTicket(aTicket);
		this.addNewChildTicket(aTicket);
	},
	
	addNewTopLevelTicket: function(aContainer) {
		if (this.isRenderingTicket(aContainer))
			return;
		
		var view = this.createViewForTicket(aContainer);
		// fs: When we add the ability to add top-level items to a backlog
		// we need to change this so the totalling row is always at the end
		this.subviews.push(view);
		this.dom().append(view.toHTML());
	},
	
	isRenderingTicket: function(aTicket) {
		// FIXME: this should use the parent-id of this ticket to always get the correct view
		// See idSelector on View
		return this.dom().is(':has(#ticketID-' + aTicket.id() + ')');
	},
	
	addNewChildTicket: function(aTicket) {
		$.each(aTicket.parents(), function(index, parent) {
			// ensure parent is rendered correctly
			this.addNewTicket(parent);
			$.each(this.viewsForTicket(parent), function(index, parentView) {
				if (parentView.isRenderingChildTicket(aTicket))
					return;
				
				parentView.addSubView(this.createViewForTicket(aTicket));
			}.bind(this));
		}.bind(this));
	},
	
	didAddOrRemoveTicketFromBacklog: function(aBacklog, aTicket, wasRemoved) {
		if (aBacklog !== this.backlog)
			return;
		
		if (wasRemoved)
			; /* REFACT: trigger removal, currently implemented via the ticketChanged notification (updateFromTicket), but would be simpler here */
		else
			this.addNewTicket(aTicket);
		
		this.refreshTotallingRow();
	},
	
	didChangeOrderOfTickets: function(aBacklog) {
		if (aBacklog !== this.backlog)
			return;
		this.updateOrdering();
	},
	
	// Handling drag and drop ........................................
	
	isDragAndDropEnabled: function() {
		var outerSorting = undefined !== this.dom().data('sortable')
			&& ! this.dom().data('disabled.sortable');
		var innerSorting = undefined !== this.dom('dl').data('sortable')
			&& ! this.dom('dl').data('disabled.sortable');
		return outerSorting && innerSorting;
	},
	
	enableDragAndDrop: function() {
		// REFACT: this should probably move down to the individual view objects
		// REFACT: this.selector is probably a bad idea, try to compute it if possible
		this.enableSorting('.backlog', '> dl:not(.no_drag)'); // sorting of top level containers
		this.enableSorting('.backlog dl', '> dd'); // sorting all the nested containers
	},
	
	enableSorting: function(sortableBaseSelector, draggableItemsSelector, handle) {
		// REFACT: change to this.dom().add...
		$(sortableBaseSelector).addClass('enabled').removeClass('disabled')
			.sortable({
				appendTo: 'body',
				items: draggableItemsSelector, // what to sort
				placeholder: 'sortable-highlight-ticket-drop-target', // this visualizes the drop location
				// BUG: Revert doesn't work if the window is scrolled, it then animates everything somewhere to the top of the page.
				// BUG in jquery-ui: the revert animation will always go up to twice the scroll ammount
				// (i.e. more too far up the more the window is scrolled)
				
				delay: 250,
				
				start: function(event, ui) {
					$(ui.helper).addClass("dragging");
					// This fixes a problem with IE 7 when the starting the first drag the content view collapses to 1 px height.
					// This only happens with certain view sizes so it's a bit hard to reproduce.
					// Fixes #1010 https://dev.agile42.com/ticket/1010
					// This is one of the issues that doesn't work if the timeout for the redraw is 0 :(
					forceIE7Redraw('.main', 10);
					// There is also a different collapse that starts after the drag 
					// we need multiple timeouts here as depending on how fast your computer is,
					// ie will trigger the bug after different timespans....
					forceIE7Redraw('.main', 500);
					forceIE7Redraw('.main', 1000);
					// Fixes a bug where ie 7 draws the rows scrolled out of the screen on top of the ones on the screen
					// This needs to happen after the forceRedraw of .main as that also triggers this bug...
					// So we schedule it here. :-(
					forceIE7Redraw('[id^=ticketID] .id', 1010);
				},
				change: function(event, ui) {
					// Fixes a bug where ie 7 draws the rows scrolled out of the screen on top of the ones on the screen
					forceIE7Redraw('[id^=ticketID] .id');
				},
				update: function(event, ui) {
					forceIE7Redraw('[id^=ticketID] .id');
				},
				stop: function(event, ui) {
					// Fixes bug in Firefox & IE 7/8 where the dragstop would not cause the mouseleve
					// event not to be sent to the clicked element in jquery ui 1.7.2
					if ($.browser.msie || $.browser.mozilla)
						$(event.originalTarget || event.srcElement).mouseleave();
					
					// only remove after stack has cleared, so that inlin editor 
					setTimeout(function() { $(ui.item).removeClass("dragging"); }, 1);
					// IE 7 blanks the display of a story and its subtasks when the story is dropped
					forceIE7Redraw(ui.item);
					this.positionsDidChange();
					// IE 7: sometimes blanks all of .main on starting the drag
					forceIE7Redraw('.main');
					// Fixes a bug where ie 7 draws the rows scrolled out of the screen on top of the ones on the screen
					forceIE7Redraw('[id^=ticketID] .id');
				}.bind(this),
				over: function(event, ui) {
					$(event.target).toggleClass("sortover");
				},
				out: function(event, ui) {
					$(event.target).toggleClass("sortover");
				}
			});
	},
	
	positionsDidChange: function() {
		if (this.controller)
			this.controller.positionsDidChange();
	},
	
	disableDragAndDrop: function() {
		this.dom().sortable('disable').removeClass("enabled").addClass("disabled");
		this.dom('dl').sortable('disable').removeClass("enabled").addClass("disabled");
	},
	
	setIsEditable: function(shouldEnable) {
		if(shouldEnable) {
			this.enableDragAndDrop();
			this.enableInlineEditing();
		}
		else {
			this.disableDragAndDrop();
			this.disableInlineEditing();
		}
	},
	
	orderOfTickets: function() {
		return this.dom().find('dl, dt, dd').map(function(index, element){
			return parseInt($(element).attr('id').substring(9), 10); 
		}).filter(function(){
			return undefined !== this
				&& ! isNaN(this) // synthetic nodes
				&& -1 != this // Fake story - need the auto-coercion somehow. :/
				&& -2 != this;
		}).get();
	},
	
	/// expects that the order is tree normalized
	/// i.e. that all children are sorted behind their parents and that the fake story and it's children are at the end.
	/// also expects that all tickets mentioned are already rendered
	updateOrdering: function() {
		this.sortViews(this.subviews, this.backlog.topLevelContainers()); 
	},
	
	// REFACT: I would like to move this to the view class, but...
	sortViews: function(views, orderedTickets) {
		if (0 === orderedTickets.length)
			return;
		
		var totallingRow = this.totallingRow();
		if (totallingRow)
			orderedTickets.push(totallingRow.ticket);
		var orderOnThisLevel = $.map(orderedTickets, function(ticket){ return ticket.id(); });
		views.sort(function(first, second) {
			var firstTargetPosition = $.inArray(first.ticket, orderedTickets);
			var secondTargetPosition = $.inArray(second.ticket, orderedTickets);
			return firstTargetPosition - secondTargetPosition;
		});
		
		// create jquery collection of all elements in right order
		// then append (move) that anew to the parent
		var orderedDOMNodes = $.map(views, function(view) { return view.domForSorting()[0]; });
		$(orderedDOMNodes).appendTo(views[0].domForSorting().parent());
		
		// sort subviews
		for (var i = 0; i < orderedTickets.length; i++) {
			if ( ! orderedTickets[i].hasChildren())
				continue;
			
			this.sortViews(views[i].subviews, orderedTickets[i].children());
		}
	},
	
	// Handling inline editing ...........................................
	
	// REFACT: it would be really nice if this could be done with live-queries, 
	// so that I don't have to remember to re-enable this after each change
	// As far as I understand live queries in jquery, it is not yet possible
	enableInlineEditing: function() {
		this.isInlineEditingActive = true;
		this.traversePreOrder(this.enableInlineEditingOfTicketViewIfPossible.bind(this));
	},
	
	enableInlineEditingOfTicketViewIfPossible: function(ticketView) {
		if ( ! ticketView.ticket.json.can_edit)
			return;
		
		$(this.configuredColumns).each(function(index, column) {
			var fieldName = this.keyForAlternativeColumnContent(ticketView.ticket, column);
			if ( ! this.isEditableFieldForTicket(fieldName, ticketView.ticket))
				return;
			
			this.enableInlineEditingOfFieldInTicketView(fieldName, ticketView);
		}.bind(this));
		
	},
	
	isEditableFieldForTicket: function(fieldName, ticket) {
		if ( ! ticket.hasKey(fieldName))
			return false;
		
		if ('id' === fieldName)
			return false;
		
		if (this.ticketFieldOptionGenerator.isCalculatedField(fieldName))
			return false;
		
		return true;
	},
	
	enableInlineEditingOfFieldInTicketView: function(fieldName, ticketView) {
		var arguments = {
			hover_class: 'inlineEditable',
			saving_animation_color: '#ECF2F8',
			default_text: ' ',
			cancel: 'div.inlineEditorButtons',
			callback: function(unusedElementID, newContent, oldContent, unusedParams, callbacks){
				return ticketView.didEndInlineEditForField(
					newContent, fieldName, 
					ticketView.stringNormalizingParser.bind(ticketView),
					callbacks);
			},
			preinit: function(editorDOM) {
				// if we're in a drag operation, we don't want to open the inline editor
				if (editorDOM.parents(':has(.dragging)').length > 0)
					return false;
				
				ticketView.enableSelectionOfSummaryField();
				ticketView.removeExtraDomNodes(editorDOM);
				return true;
			},
			postclose: function(editorDOM) {
				ticketView.restoreExtraDomNodes(editorDOM);
				ticketView.disableSelectionOfSummaryField();
			}
		};
		
		if (this.ticketFieldOptionGenerator.isSelectLikeField(fieldName)) {
			var options = this.ticketFieldOptionGenerator.editorSelectOptionsForField(fieldName);
			$.extend(arguments, {
				select_text: "Please select:", // default text to show in the popups
				field_type: 'select',
				select_options: options
			});
		}
		
		ticketView.dom('.' + fieldName).editInPlace(arguments);
	},
	
	disableInlineEditing: function() {
		$('*').unbind('.editInPlace');
		this.isInlineEditingActive = false;
	},
	
	reEnableInlineEditingIfNecessary: function() {
		if ( ! this.isInlineEditingActive)
			return;
		
		this.enableInlineEditing();
	},
	
	// Support for filtering the list .......................................
	
	applyFiltering: function(filter) {
		this.traversePreOrder(function(view){
			var shouldShow = filter.shouldShow(view.ticket);
			view.dom().toggle(shouldShow);
			if (shouldShow)
				view.showAllParents();
		}.bind(this));
		this.refreshTotallingRow(filter);
	},
	
	// Showing messages ....................................................
	
	// REFACT: this is actually not shown in the table but above it, so it doesn't really belong in this object
	setMessage: function(aMessage) {
		if (0 === $('#notice').length)
			// somehow h1:first doesn't work in webkit right now?
			$('#backlog h1:eq(0)').after('<span id="notice"></span>');
		
		$('#notice').text(aMessage);
	}
});

// can only share methods with this for now...
// REFACT: extract container view logic into superclass and make that the view class
View = function() {};
$.extend(View.prototype, {
	
	initialize: function(aBacklogView, aTicket) {
		this.extraDOMNodes = {};
		this.backlogView = aBacklogView;
		this.ticket = aTicket;
		this.ticket.addObserver(this, this.updateFromTicket.bind(this));
	},
	
	// TODO: add init function if I need to share state also and initialize it in there then
	dom: function(optionalSelector) {
		var dom = $('#' + this.idSelector());
		if (optionalSelector)
			return dom.find(optionalSelector);
		else
			return dom;
	},
	
	domForSorting: function() {
		return this.dom();
	},
	
	// REFACT: remove aTicket argument and use this.ticket instead
	htmlForTicket: function(aTicket) {
		// REFACT: need to get rid of the type in the classes so we can support arbitrary ones here
		// REFACT: handling the alternative columns like this all over the place is actually quite a bad idea. 
		// However I'm not sure I have a better one just now. :/
		var htmlForColumn = function(aColumnKeyOrKeys) {
			var columnKey = this.backlogView.keyForAlternativeColumnContent(aTicket, aColumnKeyOrKeys);
			var columnClass = aColumnKeyOrKeys;
			if ($.isArray(aColumnKeyOrKeys))
				columnClass = aColumnKeyOrKeys.join(' ');
			var shouldLink = 'id' === columnKey;
			var shoudHideAnker = aTicket.isFakeTicket();
			var additionalHTML = this.backlogView.doCallbackForColumnRendering(aTicket, columnKey);
			var numericClass = (this.backlogView.isNumericColumn(columnKey)) ? ' numeric ' : '';
			var styleVisibilityAnker = shoudHideAnker ? 'hidden' : 'visible';
			// REFACT: consider switching to html5 style data-contains attributes for easier generation
			return '<span class="' + columnClass + numericClass + '" data="{ \'field\': \'' + columnKey + '\' }">' 
				+ ((shouldLink) ? '<a href="' + aTicket.tracTicketLink() + '" style="visibility:' + styleVisibilityAnker + '" >' : '')
				+ agilo.escape.html(aTicket.valueForKey(columnKey))
				+ ((shouldLink) ? '</a>' : '')
				+ additionalHTML
				+ '</span>';
		}.bind(this);
		
		var multiLinkTag = (aTicket.hasMultipleParentLinks()) ? ' multi-linked-item ' : '';
		var levelTag = 'level-' + this.numberOfParentViews();
		var typeAndStatusTag = this.typeClassForTicket(aTicket) + this.statusClassForTicket(aTicket);
		var rowContent =  ' handle ' + multiLinkTag + levelTag + typeAndStatusTag + '" id="' + this.idSelector();
		rowContent +=   '" data="'+JSON.stringify(aTicket.json).replace(/\"/g, "'")+'">';
		$(this.backlogView.configuredColumns).each(function(index, column){
			rowContent += htmlForColumn(column);
		});
		
		// REFACT: This should really go into the subviews to get rid of the if. 
		//         However I don't want to split up the tag generation. :-(
		if (aTicket.isContainer())
			return '<dt class="container'
				+ rowContent
				+ '</dt>';
		else
			return '<dd class="leaf'
				+ rowContent
				+ '</dd>';
	},

    attributeClassForTicket: function(anAttribute, aTicket) {
        return ' ticket' + anAttribute + '-' + aTicket.valueForKey(anAttribute).replace(/ /g,'-') + ' ';
    },

	typeClassForTicket: function(aTicket) {
		return this.attributeClassForTicket("type", aTicket);
	},

	statusClassForTicket: function(aTicket) {
        return this.attributeClassForTicket("status", aTicket);
	},
	
	removeExtraDomNodes: function(columnDOM) {
		var columnName = columnDOM.metadata().field;
		var children = columnDOM.children();
		this.extraDOMNodes[columnName] = children.clone(true);
		children.remove();
	},
	
	restoreExtraDomNodes: function(columnDOM) {
		var columnName = columnDOM.metadata().field;
		columnDOM.append(this.extraDOMNodes[columnName]);
		delete this.extraDOMNodes[columnName];
	},
	
	idSelector: function() {
		var basicSelector = 'ticketID-' + this.ticket.id();
		
		if ( ! this.ticket.hasMultipleParentLinks() || ! this.superview())
			return basicSelector;
		
		var parentIndex = this.ticket.indexOfParent(this.superview().ticket);
		if (0 === parentIndex)
			return basicSelector;
		
		return basicSelector + '-' + parentIndex;
	},
	
	numberOfParentViews: function() {
		var count = 0;
		var currentView = this;
		while (currentView) {
			count++;
			currentView = currentView.superview();
		}
		return count;
	},
	
	setSuperview: function(aSuperView) {
		this.parentView = aSuperView;
	},
	/// performance critical method, called very often during rendering
	superview: function() {
		if (undefined !== this.parentView)
			return this.parentView;
		
		var that = this;
		this.backlogView.traversePreOrder(function(view){
			if (view.subviews && -1 !== $.inArray(this, view.subviews))
				that.parentView = view;
		}.bind(this));
		if ( ! this.parentView)
			this.parentView = null; // marker
		return this.parentView;
	},

	showAllParents: function() {
		this.dom().show();
		
		if (this.superview())
			this.superview().showAllParents();
	},
	
	removeFromDOM: function() {
		this.dom().remove();
		this.ticket.removeObserver(this);
		// need to be able to remove it from the root view too
		var superView = this.superview() || this.backlogView;
		superView.removeSubView(this);
	},
	
	// Inline editing of fields ..............................................
	
	didEndInlineEditForField: function(newValue, fieldName, optionalParser, optionalCallbacks) {
		if (optionalParser) {
			newValue = optionalParser(newValue);
			if (this.rejectedValue === newValue) {
				return this.ticket.valueForKey(fieldName);
			}
		}
		
		// if nothing changed - just stay with the old value
		// need coercing comparison as the numbers are stored as strings in the backend...
		if ( ! this.ticket.wouldChangeValueForKey(newValue, fieldName))
			return this.ticket.valueForKey(fieldName);
		
		if (optionalCallbacks)
			optionalCallbacks.didStartSaving();
		
		this.ticket.setValueForKey(newValue, fieldName);
		
		this.ticket.submitToServer(function(ticket, wasSuccess){
			if (optionalCallbacks)
				optionalCallbacks.didEndSaving();
			this.backlogView.backlog.triggerUpdateFromServer();
			
		}.bind(this));
		
		return this.ticket.valueForKey(fieldName);
	},
	
	enableSelectionOfSummaryField: function() {
		this.dom().find(".summary").enableSelection();
	},
	
	disableSelectionOfSummaryField: function() {
		this.dom().find(".summary").disableSelection();
	},
	
	/// Does not support changing the id of tickets. If you want to do that, remove the element and add a new one!
	updateFromTicket: function(ticket, wasRemoved) {
		if (wasRemoved) {
			// TODO: consider to add animation for prettyness
			this.removeFromDOM();
			return;
		}
		
		this.updateMarkerClassesFromTicket();
		this.updateRenderedValuesFromTicket();
		this.backlogView.updateTotals();
	},
	
	updateMarkerClassesFromTicket: function() {
		this.removeClassStartingWith('tickettype');
		this.removeClassStartingWith('ticketstatus');
		this.dom().addClass(this.typeClassForTicket(this.ticket));
		this.dom().addClass(this.statusClassForTicket(this.ticket));
	},
	
	removeClassStartingWith: function(aString) {
		var classes = this.dom().attr('class');
		if ( ! classes)
			return; // not rendered yet
		
		var newClasses = _(classes.split(' '))
			.reject(function(aClass) { return RegExp('^' + aString).test(aClass); })
			.join(' ');
		this.dom().attr('class', newClasses);
	},
	
	updateRenderedValuesFromTicket: function() {
		this.dom().children('span').each(function(index, element){
			// can't update the id - if that changes, create a new row instead
			var jsonKey = $(element).metadata().field;
			if ('id' === jsonKey)
				return;
			
			if (this.ticket.hasKey(jsonKey)) {
				var updateNode = $(element);
				
				// If we add child-nodes via the callback system - don't overwrite them in an update operation
				var savedChildren = updateNode.children().clone(true);
				updateNode.text(this.ticket.valueForKey(jsonKey));
				updateNode.append(savedChildren);
			}
		}.bind(this));
		
	},
	
	// Validation support ...............................................
	
	stringNormalizingParser: function(aString) {
		if ((/^\s*$/).test(aString))
			return '';
		
		return aString;
	},
	
	missingCommaErrorPreventer:''
});

ContainerView = function(aBacklogView, aContainer){
	this.initialize(aBacklogView, aContainer);
	this.subviews = [];
};
ContainerView.prototype = new View();
$.extend(ContainerView.prototype, {
	
	domForSorting: function() {
		return this.dom().parent();
	},
	
	traversePreOrder: function(aFunction) {
		aFunction(this);
		$(this.subviews).each(function(index, subview){
			subview.traversePreOrder(aFunction);
		});
	},
	
	toHTML: function() {
		var html = [];
		// FIXME fs: That's really a dirty hack to prevent the fake story+
		// totalling row not to be draggable.
		if (this.ticket.isFakeTicket())
            html.push('<dl class="no_drag">');
		else
            html.push('<dl>');
		html.push(this.htmlForTicket(this.ticket));
		$(this.subviews).each(function(index, subview){
			html.push(this.htmlForSubview(subview));
		}.bind(this));
		html.push('</dl>');
		return html.join('');
	},
	
	htmlForSubview: function(aSubview) {
		var html = [];
		var shouldSynthetiseWrappingDD = aSubview.ticket.isContainer();
		if (shouldSynthetiseWrappingDD)
			html.push('<dd class="childcontainer">');
		html.push(aSubview.toHTML());
		if (shouldSynthetiseWrappingDD)
			html.push('</dd>');
		return html.join('');
	},
	
	setSubviews: function(someSubviews) {
		this.subviews = someSubviews;
		var that = this;
		$.each(this.subviews, function(index, subview) {
			subview.setSuperview(that);
		});
	},
	
	addSubView: function(aSubView) {
		this.subviews.push(aSubView);
		this.renderNewAddedSubview(aSubView);
	},
	
	isRenderingChildTicket: function(aTicket) {
		return $.grep(this.subviews, function(childView){
			return childView.ticket === aTicket;
		}).length >= 1;
	},
	
	/// Will fail silently if this view is not already rendered
	renderNewAddedSubview: function(aSubView) {
		this.dom().parent().append(this.htmlForSubview(aSubView));
		this.backlogView.reEnableInlineEditingIfNecessary();
	},
	
	removeFromDOM: function(){
		// supercall
		View.prototype.removeFromDOM.apply(this);
		this.removeOrMoveChildren();
	},
	
	removeOrMoveChildren: function() {
		$.each(_(this.subviews).clone(), function(index, subview) {
			subview.removeFromDOM();
			// still need to render it
			if (this.backlogView.backlog.hasTicket(subview.ticket))
				this.backlogView.addNewTicket(subview.ticket);
		}.bind(this));
		
	},
	
	removeSubView: function(aChildView) {
		var index = $.inArray(aChildView, this.subviews);
		if ( -1 === index)
			return;
		
		this.subviews.splice(index, 1); // remove it
	}
	
});

LeafView = function(aBacklogView, aLeaf){
	this.initialize(aBacklogView, aLeaf);
};
LeafView.prototype = new View();
$.extend(LeafView.prototype, {
	
	traversePreOrder: function(aFunction) {
		aFunction(this);
	},
	
	toHTML: function() {
		return this.htmlForTicket(this.ticket);
	}
	
});


function TicketFieldOptionGenerator() {
	this.ticketFields = {};
}

$.extend(TicketFieldOptionGenerator.prototype, {
	isSelectLikeField: function(fieldName) {
		var ticketField = this.ticketFields[fieldName];
		if (undefined === ticketField)
			return undefined;
		if ('checkbox' === ticketField.type)
			return true;
		
		return 'options' in ticketField;
	},
	
	optionsForField: function(fieldName) {
		var ticketField = this.ticketFields[fieldName];
		return ticketField.options;
	},
	
	editorSelectOptionsForField: function(fieldName) {
		var ticketField = this.ticketFields[fieldName];
		var ticketOptions = [];
		
		// We duplicate each key because the inPlace editor
		// handles values with colons magically
		if (true === ticketField.optional)
			ticketOptions.push(['', '']);
		
		if ('checkbox' === ticketField.type)
			return [['True', '1'], ['False', '0']];
		
		$.each(this.optionsForField(fieldName), function(index, value) {
			ticketOptions.push([value, value]);
		});
		
		return ticketOptions;
	},
	
	setBacklogInfo: function(backlogInfo) {
		if (undefined === backlogInfo || undefined === backlogInfo.ticket_fields)
			return;
		this.ticketFields = backlogInfo.ticket_fields;
	},
	
	isCalculatedField: function(fieldName) {
		var ticketField = this.ticketFields[fieldName];
		if (undefined === ticketField)
			return undefined;
		return true === ticketField.is_calculated;
	},
	
	missingCommaErrorPreventer:''
});


/**
 * Distribute available space with percent sizing to available columns
 * 
 * If you set left aligned columns you need to provide their size in pixels 
 * and the last column will size till the end.
 * 
 * If you make the absolutely sized columns too big, this will fail, so keep them small.
 */
function BacklogColumnLayouter() {
	this.numberOfColumns = 0;
	this.numberOfLeftAnchoredColums = 0;
	this.limitPercentSizingToPercent = 100;
	this.leftAnchoredColumnWidths = [];
}

$.extend(BacklogColumnLayouter.prototype, {
	setNumberOfColumns: function(aNumber) {
		this.numberOfColumns = aNumber;
	},
	setLeftAnchoredColumnsWithWidths: function(aNumber, someWidthsInPixels) {
		this.numberOfLeftAnchoredColums = aNumber;
		this.leftAnchoredColumnWidths = someWidthsInPixels;
	},
	setPercentSizedColumnsLimit: function(aPercentValue) {
		this.limitPercentSizingToPercent = aPercentValue;
	},
	columnWidth: function() {
		return this.limitPercentSizingToPercent / this.numberOfColumns;
	},
	rightOffsetForColumnAtIndex: function(anIndex) {
		return (this.numberOfColumns - 1 - anIndex) * this.columnWidth();
	},
	absoluteLeftOffsetOfCollumnAtIndex: function(anIndex) {
		var leftColumnOffset = 0;
		for (var i = 0; i < anIndex; i++)
			leftColumnOffset += this.leftAnchoredColumnWidths[i];
		return leftColumnOffset;
	},
	
	isLastColumn: function(anIndex) {
		return anIndex === this.numberOfColumns - 1;
	},
	isFirstColumn: function(anIndex) {
		return 0 === anIndex;
	},
	isLeftAnchoredColumnAtIndex: function(anIndex) {
		return this.numberOfLeftAnchoredColums > 0
			&& anIndex <= this.numberOfLeftAnchoredColums;
	},
	cssForLeftAnchoredColumnAtIndex: function(anIndex) {
		var css = {
			left: this.absoluteLeftOffsetOfCollumnAtIndex(anIndex) + 'px'
		};
		
		if (this.isLastColumn(anIndex))
			css.right = '0%';
		else if (anIndex < this.numberOfLeftAnchoredColums)
			css.width = this.leftAnchoredColumnWidths[anIndex] - 6 + 'px';
			// 5px padding + 1 px border - w3c box model...
		else if (anIndex === this.numberOfLeftAnchoredColums)
			css.right = this.rightOffsetForColumnAtIndex(anIndex) + '%';
		
		return css;
	},
	
	cssForRightAnchoredColumnAtIndex: function(anIndex) {
		var css = {
			right: this.rightOffsetForColumnAtIndex(anIndex) + '%'
		};
		
		if (this.isFirstColumn(anIndex))
			css.left = '0px';
		else
			css.width = this.columnWidth() - 2 + '%';
			// 1% padding on each side. w3c box model...
		
		return css;
	},
	
	cssForColumnAtIndex: function(anIndex) {
		if (this.isLeftAnchoredColumnAtIndex(anIndex))
			return this.cssForLeftAnchoredColumnAtIndex(anIndex);
		
		return this.cssForRightAnchoredColumnAtIndex(anIndex);
	},
	
	generateCSSAtColumnWithIndexAndClassName: function(anIndex, aClassNameOrNames) {
		// REFACT: if we need this more often, look at <http://blog.acodingfool.com/2009/07/20/jquery-xcss-plugin-part-2/>
		var cssRules = this.cssForColumnAtIndex(anIndex);
		
		var className = 'span.' + aClassNameOrNames;
		if ($.isArray(aClassNameOrNames))
			className = 'span.' + aClassNameOrNames.join(', span.');
		
		var cssString = [ className + ' {' ];
		for (var key in cssRules)
			cssString.push('\t' + key + ': ' + cssRules[key] + ';');
		cssString.push('}');
		
		return cssString.join('\n');
	},
	
	generateCSSWithColumnNames: function(someColumnNames) {
		var joinedCSS = $.map(someColumnNames, function(className, index) {
			return this.generateCSSAtColumnWithIndexAndClassName(index, className);
		}.bind(this));
		
		return  [
			'<style type="text/css" media="all">',
			joinedCSS.join('\n\n'),
			'</style>'
		].join('\n');
	},
	
	missingCommaErrorPreventer:''
});
