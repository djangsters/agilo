function DragManager() {
	this.loader = new BacklogServerCommunicator(window.BACKLOG_INFO);
};

$.extend(DragManager.prototype, {
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
		var order = this.orderOfTickets();
		this.loader.sendPositionsUpdateToServer(order);
	},
	
	orderOfTickets: function() {
		return $('.backlog').find('dl, dt, dd').map(function(index, element){
			return parseInt($(element).attr('id').substring(9), 10);
		}).filter(function(){
			return undefined !== this
				&& ! isNaN(this)
				&& -1 != this
				&& -2 != this;
		}).get();
	}
});

function TicketViewUpdater() {};

$.extend(TicketViewUpdater.prototype, {
	
	updateViewForTicket: function(ticketId, recursive){
		var ticket = new Ticket({'id':ticketId});
		ticket.reloadFromServer(function(someJSON){
			var ticketJSON = someJSON.json[0];
			if (!ticketJSON)
				return;
			
			var ticketView = $("#ticketID-" + ticketJSON.id + ", [id^=ticketID-" + ticketJSON.id + "-]");
			
			for (var key in ticketJSON) {
				if (key == 'id')
					continue;
				
				if (ticketJSON.hasOwnProperty(key) && key !== '') {
					ticketView.find('.'+key).html(ticketJSON[key]);
					ticketView.metadata()[key] = ticketJSON[key];
				}
			}
			
			if (recursive) {
				var that = this;
				$.each(ticketJSON.incoming_links, function(index, item){
					that.updateViewForTicket(item, recursive);
				})	
			}
			
			new TotalsRowController().recalculateTotals();
			// this is needed to hide tickets that might have been closed during editing
			Agilo.filterController.applyFiltering(); 	

		}.bind(this));
	}
	
});

function TotalsRowController() {};

$.extend(TotalsRowController.prototype, {
	
	recalculateTotals: function() {
		var totalsRowDOM = $('#ticketID--2');
		var totalsFields = totalsRowDOM.find('span').map(function(index, item){
			var field = $(item).metadata().field;
			if (field)
				return field;
		});
		totalsFields.each(function(index, item){
			var total = 0;
			$("."+item+":visible").each(function(index, item){
				var value = parseFloat($(item).text());
				if (!isNaN(value) && $(item).parent().metadata().id && $(item).parent().attr('id').indexOf('-',9) < 0)
					total += value;
			});
			var dest = totalsRowDOM.find('span.'+item+':not(.summary)');
			dest.text(total || "");
			if (total)
				$("."+item+":visible").each(function(index, item){
					$(item).addClass('numeric');
				});
		});
				
		var tickets = $("[id^=ticketID-]:visible").map(function(index, element){
			return parseInt($(element).attr('id').substring(9), 10);
		})
		
		tickets = uniquedArrayFromArray(tickets);
		
		// for some reason jQuery.filter doesn't work here in IE
		var total = 0;
		
		for (var i = 0; i < tickets.length; i++) {
			var item = tickets[i];
			if (undefined !== item
				&& ! isNaN(item)
				&& -1 != item
				&& -2 != item)
			total++;
			
		}
		totalsRowDOM.find('span.id').text(total);
	}
});

function FilterController() {
	var cookie = $.cookie('agilo-backlog-filter');
	var cookieAsJson = null;
	if (cookie !== null)
		cookieAsJson = JSON.parse(cookie);
	this.onlyMine = cookieAsJson != null ? cookieAsJson.showMyItems || false : false;
	this.hideClosed = cookieAsJson != null ? cookieAsJson.hideClosedItems || false : false;
	this.filterKey = BACKLOG_INFO && BACKLOG_INFO.content ? BACKLOG_INFO.content.should_filter_by_attribute : null;
	this.filterValue = cookieAsJson != null ? cookieAsJson[this.filterKey] || '' : '';
	this.loader = new BacklogServerCommunicator(window.BACKLOG_INFO);
};

$.extend(FilterController.prototype, {
	
	attributeFilteringValue: function() {
		return this.filterValue;
	},
	
	shouldHideTicket: function(item) {
		if (item.attr('id') === 'ticketID--2') return false;
	
		
		if ((item.get(0).tagName.toLowerCase() !== 'dd' &&
				item.get(0).tagName.toLowerCase() !== 'dl' &&
				item.get(0).tagName.toLowerCase() !== 'dt')
		)
			return true;
		
		var shouldHide = true;
		if (item.attr('tagName').toLowerCase() == 'dd' || item.attr('tagName').toLowerCase() == 'dt'){
			var shouldHide = false;
			if (item.metadata().owner !== this.loader.loggedInUser())
				shouldHide = shouldHide || this.onlyMine; 
			if (item.metadata().status === 'closed')
				shouldHide = shouldHide || this.hideClosed || (BACKLOG_INFO && BACKLOG_INFO.content.type === 'global'); 
			if (this.filterValue !== '' && this.filterKey !== '' && item.metadata()[this.filterKey] !== this.filterValue)
				shouldHide = true;
		}
		
		for (var i =0 ; i < item.children().length; i++)
			shouldHide = shouldHide && this.shouldHideTicket($(item.children()[i]));
		
		return shouldHide;
	},
	
	applyFiltering: function() {
		var that = this;
		$('dl, dd').each(function(index, item){
			var shouldHide = that.shouldHideTicket($(item))
			$(item).toggle(!shouldHide);
		});
		$.observer.postNotification(BacklogFiltering.DID_CHANGE_FILTER_SETTINGS, this);
		var totalsRowController = new TotalsRowController(); 
		totalsRowController.recalculateTotals();
	},
	
	toJSON: function() {
		var filters = {};
		if ( this.filterKey && this.filterValue && this.filterValue !== '')
			filters[this.filterKey] = this.filterValue;
		if (this.onlyMine)
			filters['showMyItems'] = true;
		if (this.hideClosed)
			filters['hideClosedItems'] = true;

		return JSON.stringify(filters);
	},

	
	renderPopup: function() {
		var popup = $('<form id="filter-attribute"><select id="filter-attribute-popup"></select></form>');
		var select = popup.find('select'); 
		var that = this;
		var criteriaWithDuplicates = $('[id^=ticketID]').map(function(index, item){
			var value = $(item).metadata()[that.filterKey];
			if (value)
				return value;
		});
		
		var options = uniquedArrayFromArray(criteriaWithDuplicates);
		
		var htmlizedOptions = '<option value="">Filter by...</option>' + $.map(options, function(element){
			var selectedHTML = '';
			if (this.filterValue === element){
				selectedHTML = ' selected="selected"';
			}
				
			return '<option value="' + element + '" ' + selectedHTML + '>' + element + '</option>';
		}.bind(this)).join('');
		$('.toolbar').append(popup);
		// the options have to be added after the container is added to the DOM
		// otherwise this will fail in IE
		$('#filter-attribute-popup').html(htmlizedOptions);
		$('#filter-attribute-popup').change(function(anEvent){
			that.filterValue = $(this).val();
			that.applyFiltering();
		});

	},
	
	addFilterButtons: function(){
		var onlymineOptions = {
				id : 'show-onlymine-button',
				tooltip : 'Hide or Show my tickets',
				title : 'My Tickets',
				isActive: this.onlyMine,
				isEnabled: this.loader.isUserLoggedIn(),
				clickCallback: function(isActive){
					this.onlyMine = isActive;
					this.applyFiltering();
				}.bind(this)
			 };

		var hideClosedOptions = {
				id : 'hide-closed-button',
				tooltip : 'Show or Hide closed tickets',
				title : 'Done Tickets',
				isActive: this.hideClosed,
				clickCallback: function(isActive){
					this.hideClosed = isActive;
					this.applyFiltering();
				}.bind(this)
			 };

        if (this.loader.info() && this.loader.info().type == "global"){
            hideClosedOptions.isEnabled = false;
            hideClosedOptions.tooltip = "Cannot hide closed tickets in global backlogs";
        }

		agilo.createToolbarButtons(
				[onlymineOptions, hideClosedOptions],
				{id: "filter-button-container"});
	},
	
	initializeFilter: function() {
		if (this.filterKey)
			this.renderPopup();
		this.addFilterButtons();
		this.applyFiltering();
	}
});


var Agilo = Agilo || {};

Agilo.applyBacklogInlineEditingButtons = function() {
	$("dt:not(.total):not(.unreferenced) span:not(.id), dd span:not(.id)").hover(
			function(event){
				if($(this).metadata().field !== "")
					$(this).addClass("inlineEditable");
				if (!$(this).hasClass('summary'))
					return;
				var id = $(this).parent().metadata().id || $(this).parent().metadata().ticketID;
	   			var ticketType = $(this).parent().metadata().type;
				var addEditButtonsHtml = "<div class='inlineEditorButtons'>" +
	   				"<a href='#' class='edit-inline' data='{ id:" + id + "}'>edit</a>";

	   			var permittedLinks = BACKLOG_INFO.content.configured_child_types.permitted_links_tree;

	   			if ( permittedLinks && permittedLinks[ticketType]){
		   			var childCount = 0;
		   			for (var child in permittedLinks[ticketType])
		   				childCount++;
		   			if (0 !== childCount)
			   			addEditButtonsHtml += "<a href='#' class='add-inline' data='{ id:" + id + "}'>add</a>";
	   			}

	   			addEditButtonsHtml += "</div>";
				$(this).append(addEditButtonsHtml)
   			},
			function(event){
				$(this).removeClass("inlineEditable");
				$('.inlineEditorButtons').remove();
			});
}

$(function(){
	new TotalsRowController().recalculateTotals();
	Agilo.filterController = new FilterController();
	
	Agilo.filterController.initializeFilter(); 	
	var ticketViewUpdater = new TicketViewUpdater();
	
	var dragManager = new DragManager();
	
	var commitmentConfirmation = new agilo.CommitmentConfirmation(Agilo.filterController.loader);
	commitmentConfirmation.addToDOM();
		
	var csvExportButtonOptions = {
			id : 'csv-button',
			isPushButton: true,
			tooltip : 'Export backlog as CSV',
			clickCallback: function(isActive){
				var currentLocation = document.location;
				document.location = (""+currentLocation).indexOf("?") >= 0 ? currentLocation + "&format=csv" : currentLocation + "?format=csv"; 
			 }.bind(this)
		 };
	
	agilo.createToolbarButtons([csvExportButtonOptions ], {id : 'csv-export-button-container'});

	
	if (!BACKLOG_INFO || BACKLOG_INFO.content.access_control.is_read_only)
		return;
	
	dragManager.enableDragAndDrop();

    Agilo.applyBacklogInlineEditingButtons();

	$("#backlog").click(function(event){
		var field = $(event.target).metadata().field;
		var ticketField = BACKLOG_INFO.content.ticket_fields[field];
		if ( field === 'id' || field === 'time' || field === 'changetime' ||
				$(event.target).parents('.id').length != 0 ||
				$(event.target).parents('.total').length != 0 ||
				$(event.target).parents('.unreferenced').length != 0 ||
				$(event.target).parents('.backlog.sprint').length == 0 ||
				ticketField === undefined || ticketField.is_calculated) {
			return;
		}

		$('.inlineEditorButtons').remove();
		
		var ticketId = $(event.target).parent().metadata().id;
		var ticketTimestamp = $(event.target).parent().metadata().ts;
		var ticketView = $(event.target).parent().metadata().view_time || undefined;
		var timeOfLastChange = $(event.target).parent().metadata().time_of_last_change;
		
		var divHtml = $(event.target).html();
		var oldElement = $(event.target);
		var editableText = $("<input/>");
		editableText.val(divHtml);
		
		if ('checkbox' === ticketField.type || 'options' in ticketField) {
			editableText = "<select>";
			var options = BACKLOG_INFO.content.ticket_fields[field].options;
			
			var ticketOptions = [];
			
			ticketOptions.push(['Please select:','']);
			if (true === ticketField.optional)
				ticketOptions.push(['', '']);
			
			if ('checkbox' === ticketField.type)
				return [['True', '1'], ['False', '0']];
			
			$.each(options, function(index, value) {
				ticketOptions.push([value, value]);
			});
			
			
			for (var i = 0; i < ticketOptions.length;i++) {
				editableText += '<option value="'+ticketOptions[i][0] + '"';
				if ( i == 0 ) {
					editableText += 'disabled';
				}
				if (ticketOptions[i][0] === divHtml) {
					editableText += 'selected';
				}
				editableText += '>'+ticketOptions[i][0]+'</option>';
			}
			editableText += '</select>';
			editableText = $(editableText);
		}
		
		$(event.target).html("");
		$(event.target).append(editableText);
		editableText.focus();
		
		editableText.blur(function(event){
			if (divHtml == $(this).val()){
                oldElement.html($(this).val());
                $(this).remove();
                return;
            }

			var ticket_json = {
					'id': ticketId,
					'ts': ticketTimestamp,
					'view_time': ticketView,
					'time_of_last_change': timeOfLastChange,
					'submit': true
			};
			ticket_json[field] = $(this).val();
			var ticket = new Ticket(ticket_json);
			ticket.submitToServer(function(someJSON){
				ticketViewUpdater.updateViewForTicket(someJSON.json.id, true);
			});
			oldElement.html($(this).val());
			$(this).remove();
		});
		
		editableText.keydown(function(e){
			var code = (e.keyCode ? e.keyCode : e.which);
			if (code == 27) {
				$(this).remove();
				$(event.target).html(divHtml);
			}
		});
		
		editableText.keypress(function(e){
			var code = (e.keyCode ? e.keyCode : e.which);
			if ( code == 13 ) {
				$(this).blur();
			}
		});
	});
});