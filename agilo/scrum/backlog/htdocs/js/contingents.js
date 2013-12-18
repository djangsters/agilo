function Contingents(aBacklogLoader) {
	this.loader = aBacklogLoader;
	this._contingents = [];
}	this.errorSink = undefined;
;

$.extend(Contingents.prototype, {
	
	json: function() {
		return this.loader.contingentsLoader.json;
	},
	
	contingents: function() {
		if ( ! this.json())
			return [];
		
		if (isEmpty(this._contingents))
			this.addContingentsFromLoader();
		
		return this._contingents;
	},
	
	hasContingents: function() {
		return 0 !== this.contingents().length;
	},
	
	addContingentsFromLoader: function() {
		this._contingents = $.map(this.json().content, function(contingent) {
			return this.addContingentFromJSON(contingent);
		}.bind(this));
	},
	
	addContingentFromJSON: function(contingentJSON) {
		var contingent = new Contingent(this, contingentJSON);
		this._contingents.push(contingent);
		return contingent;
	},
	
	canAddContingents: function() {
		if ( ! this.json())
			return false;
		
		return -1 !== $.inArray('AGILO_CONTINGENT_ADMIN', this.json().permissions);
	},
	
	showError: function(someErrorText) {
		if (this.errorSink)
			this.errorSink(someErrorText);
		else
			alert(someErrorText);
	},
	
	registerErrorSink: function(someCallback) {
		this.errorSink = someCallback;
	},
	

	
	missingLastCommaErrorPreventer:''
});

function Contingent(model, aContingentJSON) {
	this.setJSON(aContingentJSON);
	this.model = model;
}

$.extend(Contingent.prototype, {
	
	setJSON: function(someJSON) {
		// Do some basic sanity checks
		if ( ! someJSON || ! someJSON.content)
			return;
		
		this.json = someJSON;
		this.contingent = this.json.content;
	},
	
	name: function() {
		return this.contingent.name;
	},
	
	sprintName: function() {
		return this.contingent.sprint;
	},
	
	availableTime: function() {
		if (null === this.contingent.amount)
			return 0;
		return this.contingent.amount;
	},
	
	spentTime: function() {
		return this.contingent.actual;
	},
	
	delta: function() {
		return this.contingent.delta;
	},
	
	addOrRemoveTimeFromContingent: function(burnValue) {
		if (this.isInvalidBurnValue(burnValue))
			throw "Invalid burn value - can only burn time within the contingent boundaries";
		this.contingent.delta = parseFloat(burnValue);
	},
	
	remainingTime: function() {
		return this.availableTime() - this.spentTime();
	},
	
	percentDone: function() {
		if (0 === this.availableTime())
			return 0;
		
		return this.spentTime() / this.availableTime() * 100;
	},
	
	canEdit: function() {
		return -1 !== $.inArray('AGILO_CONTINGENT_ADD_TIME', this.json.permissions);
	},
	
	isReadOnly: function() {
		return ! this.canEdit();
	},
	
	submitToServer: function(optionalCallbacks) {
		this.model.loader.postUpdateForContingent(this.contingent, function(newJSON) {
			this.setJSON(newJSON);
			
			$.each(optionalCallbacks, function(index, callback) {
				if($.isFunction(callback))
					callback();
			});
		}.bind(this));
	},
	
	didEndInlineEditing: function(burnValue, updateGUICallback, animationCallbacks) {
		if (this.isInvalidBurnValue(burnValue)) {
			var lowerBound = -this.spentTime();
			var upperBound = this.remainingTime();
			this.model.showError("Invalid value. Specify a number between " + lowerBound + " and " + upperBound + ".");
			return '';
		}
		
		var completeCallbacks = [updateGUICallback];
		if (animationCallbacks) {
			animationCallbacks.didStartSaving();
			completeCallbacks.push(animationCallbacks.didEndSaving);
		}
		this.addOrRemoveTimeFromContingent(burnValue);
		this.submitToServer(completeCallbacks);
		
		return burnValue;
	},
	
	isInvalidBurnValue: function(burnValue) {
		if ('' === burnValue)
			return true;
		
		var parsedValue = parseFloat(burnValue);
		if (isNaN(parsedValue))
			return true;
		if (this.spentTime() + parsedValue > this.availableTime())
			return true;
		if (this.spentTime() + parsedValue < 0)
			return true;
		
		return false;
	},
	
	missingLastCommaErrorPreventer:''
});



// --------------------------------------------------------------------




function ContingentsView(aContingentModel) {
	this.model = aContingentModel;
	this.hideMainOverflow();
}

$.extend(ContingentsView.prototype, {
	
	// Public API .............................................
	
	setIsEditable: function(isEditable) {
		if (isEditable) {
			this.enableInPlaceEditingOfContingents();
			this.enableAddContingentsButton();
		}
		else {
			this.disableInPlaceEditingOfContingents();
			this.disableAddContingentsButton();
		}
	},
	
	addContingentsView: function() {
		var header = ['<h1><div id="contingents-close"></div><span></span>Contingents</h1><div class="contingent-container"><table>',
			'<thead><tr>',
				'<td>Title</td>',
				'<td>Amount</td>',
				'<td>Spent</td>',
				'<td>Add / Remove</td>',
				'<td>Remaining</td>',
				'<td>Progress</td>',
			'</tr></thead>',
			'<tbody>'].join('');
		
		var table = $.map(this.model.contingents(), this.contingentRowHTML).join('');
		
		var footer = '</tbody></table></div>';
		var bottomToolbar = '<div class="bottom toolbar"></div>';
		var html = '<div id="contingent">' + header + table + footer + bottomToolbar + '</div>';
		$('#content').append(html);
		this.hookUpCloseButton();
		this.createAddContingentButton();
		this.setIsEditable(true);
		this.updateView();
		// REFACT: consider to instead add it to .top.toolbar
 		// Added the button specifically to the #toolbar, otherwise it would be added to anyhting with .toolbar
		this.addToolbarButton('#toolbar');
		// Firefox will allow the user to tab to this view if it is off view and not hidden!
		this.dom().hide();
	},
	
	// Toggle button .........................................
	
	dom: function(optionalSelector){
		var dom = $('#contingent');
		if (optionalSelector)
			return dom.find(optionalSelector);
		else
			return dom;
	},
	
	addToolbarButton: function() {
		var contingentsButtonOptions = {
				id : 'contingents-toggle',
				tooltip : 'Show or hide contingents',
				clickCallback: function(isActive){
					this.toggleContingentsDisplay(isActive);
				 }.bind(this)
			 };
		
		return agilo.createToolbarButtons([contingentsButtonOptions], {id : 'contingents-button-container'});
	},
	
	toolbarButtonDOM: function() {
		return $('#contingents-toggle');
	},
	
	toggleContingentsDisplay: function(shouldShow) {
		if (shouldShow)
			this.openContingentPanel();
		else
			this.closeContingentPanel();
	},
	
	openContingentPanel: function() {
		$(".backlog").animate({bottom: "144px"});
		$("#contingent").show().animate({bottom: "0px"});
	},
	
	closeContingentPanel: function() {
		$(".backlog").animate({bottom: "0px"});
		$("#contingent").animate({bottom: "-144px"}, function(){ $(this).hide(); });
	},
	
	contingentRowHTML: function() {
		return [
			'<tr>',
				'<td class="name"></td>',
				'<td class="availableTime"></td>',
				'<td class="spentTime"></td>',
				'<td class="burnTime"></td>',
				'<td class="remainingTime"></td>',
				'<td><div class="progressContainer"><div class="progress"><div class="bar" style="width:0%"></div></div></div>',
				'<span class="progressText"></span></td>',
			'</tr>'
		].join('');
	},
	
	hookUpCloseButton: function() {
		$('#contingents-close').click(function() {
			this.toolbarButtonDOM().removeClass('active');
			this.closeContingentPanel();
		}.bind(this));
	},
	
	updateView: function() {
		$.each(this.model.contingents(), function(index, contingent) {
			// Take care not to get the thead tr...
			var row = this.dom().find('tbody tr').eq(index);
			row.find('.name').text(contingent.name());
			row.find('.availableTime').text(contingent.availableTime());
			row.find('.spentTime').text(contingent.spentTime());
			row.find('.burnTime').text("");
			row.find('.remainingTime').text(contingent.remainingTime());
			row.find('.bar').css('width', contingent.percentDone() + '%');
			row.find('.progressText').text(contingent.percentDone() + '%');
		}.bind(this));
	},
	
	// Adding contingents .....................................
	
	createAddContingentButton: function() {
		var addContingentsButtonOptions = {
				id : 'buttonBottomAdd',
				tooltip : 'Add a contingent',
				isPushButton: true,
				isEnabled: this.model.canAddContingents(),
				clickCallback: function(){
					this.showAddNewContingentDialog();
				 }.bind(this)
			 };
		
		return agilo.createToolbarButtons([addContingentsButtonOptions], {
			destinationToolbar: 'bottom',
			id: 'contingents-add-button-container'
		});
	},
	
	showAddNewContingentDialog: function() {
		agilo.exposedDOM
			.show()
			.empty()
			.append(this.newContingentDialogHTML())
			.find(':input:first').focus();
		
		agilo.exposedDOM('#cancel').click(function() {
			this.handleCancelAddNewContingentsDialog();
			return false;
		}.bind(this));
		
		// allow canceling with escape
		agilo.exposedDOM().keydown(function(event) {
			if (27 === event.which) { // escape
				this.handleCancelAddNewContingentsDialog();
				return false;
			}
		}.bind(this));
		
		agilo.exposedDOM(':submit').click(function() {
			this.handleSubmitAddNewContingentsDialog();
			return false;
		}.bind(this));
	},
	
	newContingentDialogHTML: function() {
		return [
			'<form>',
				'<div class="add-contingent">',
				'<h1>Add a contingent</h1>',
				'<label>Contingent title</label>',
				'<input title="The name of your contingent" id="name" />',
				'<label>Total amount of time</label>',
				'<input title="The amount of hours you want to reserve for this contingent" id="amount" />',
				'</div>',
				'<div class="buttons">',
					'<input type="submit" value="Add Contingent" />',
					'<input type="button" value="Cancel" id="cancel" />',
				'</div>',
			'</form>'
		].join('');
	},
	
	handleCancelAddNewContingentsDialog: function() {
		agilo.exposedDOM.hide().empty();
	},
	
	handleSubmitAddNewContingentsDialog: function() {
		var contingent = {
			name: agilo.exposedDOM('#name').val(),
			amount: agilo.exposedDOM('#amount').val()
		};
		this.model.loader.putCreateContingent(contingent, function(json) {
			var contingent = this.model.addContingentFromJSON(json);
			this.addContingent(contingent);
		}.bind(this));
		this.handleCancelAddNewContingentsDialog();
	},
	
	addContingent: function(aContingent) {
		this.dom('tbody').append(this.contingentRowHTML());
		this.updateView();
		this.enableInPlaceEditingOfContingents();
	},
	
	enableInPlaceEditingOfContingents: function() {
		$.each(this.model.contingents(), function(index, contingent){
			if (contingent.isReadOnly())
				return;
			
			this.dom('.burnTime').eq(index).editInPlace({
				hover_class: 'inlineEditable',
				saving_animation_color: '#ECF2F8',
				default_text: '',
				// REFACT: consider to set the error callback to prevent showing an error after successful return
				callback: function(unusedElementID, newContent, oldContent, unusedSettings, animationCallbacks){
					return contingent.didEndInlineEditing(newContent, this.updateView.bind(this), animationCallbacks);
				}.bind(this)
			});
			
		}.bind(this));
	},
	
	disableInPlaceEditingOfContingents: function() {
		this.dom('*').unbind('.editInPlace');
	},
	
	enableAddContingentsButton: function() {
		if ( ! this.model.canAddContingents())
			return;
		
		this.dom('#buttonBottomAdd').removeClass('disabled');
	},
	
	disableAddContingentsButton: function() {
		this.dom('#buttonBottomAdd').addClass('disabled');
	},
	
	// Private helpers .....................................
	
	hideMainOverflow: function() {
		$(".main").css("overflow", "hidden");
	},
	
	missingLastCommaErrorPreventer:''
});
