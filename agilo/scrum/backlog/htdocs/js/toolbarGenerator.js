(function(){
	
	window.agilo = window.agilo || {};
	/* ......... PUBLIC API ........................... */
	
	$.extend(agilo, {
		createToolbarButton: function(options) {
			var defaults = {
				clickCallback: function(){},
				tooltip: "",
				href: "#",
				text: "&nbsp;", // REFACT: if unset, should default to tooltip
				id: "",
				isEnabled: true,
				isActive: false,
				isPushButton: false,
				allowDefaultAction: false
				/*  TODO: We may need these
				image: "", // allow the overlay image to be specified in code
				contentHTML: "", // allow arbitrary content to replace the generated stuff (e.g. bring in a select into the toolbar)
				*/
			};
			var settings = $.extend({}, defaults, options);
			var buttonDOM = createToolbarButtonDOM(settings);
		
			if (settings.isEnabled)
				attachClickCallback(buttonDOM, settings);
			
			if ($.browser.msie)
				attachIEMouseEventsToButton(buttonDOM, settings);
			
			return buttonDOM;
		},
		
		createToolbarButtons: function(buttonOptions, options){
			var defaults = {
				id: "",
				isComposed: false,
				destinationToolbar: "top"
			};
			var settings = $.extend({}, defaults, options);
			
			var group = createToolbarButtonGroupHTML(settings);
			group.appendTo('.toolbar.' + settings.destinationToolbar);
			
			$.each(buttonOptions, function(index, buttonOption) {
				group.append(agilo.createToolbarButton(buttonOption));
			});
			
			if ($.browser.msie)
				fixIEChildProperties(group);
			
			return group;
		}
	});
	
	
	/* ......... PRIVATE HELPERS  ....................... */
	
	function createToolbarButtonGroupHTML(settings) {
		var group = $('<ul class="buttons"></ul>');
		group.attr("id", settings.id);
		if (settings.isComposed)
			group.addClass('composed');
		
		return group;
	}
	
	function createToolbarButtonDOM(settings) {
		// REFACT: this could be done so much nicer with jquery 1.4...
		var li = $("<li />");
		if ( ! settings.isEnabled)
			li.addClass('disabled');
		if (settings.isActive)
			li.addClass('active');
		
		li.attr('id', settings.id);
		var a = $("<a />");
		a.attr('href', settings.href);
		a.attr('title', settings.tooltip);
		a.text(settings.text);
		li.append(a);
		
		return li;
	}
	
	function attachClickCallback(buttonDOM, settings) {
		buttonDOM.click(function(anEvent){
			anEvent.stopPropagation();
			
			if ( ! settings.allowDefaultAction)
				anEvent.preventDefault();
			
			if ($(this).is('.disabled'))
				return;
			
			if ( ! settings.isPushButton)
				$(this).toggleClass('active');
			
			var isActive = $(this).hasClass('active');
			settings.clickCallback(isActive, anEvent);
		});
	}
	
	function attachIEMouseEventsToButton(buttonDOM, settings) {
		var wasButtonActiveBeforeDown = settings.isActive;
		if (settings.isEnabled) {
			buttonDOM.mousedown(function(){
				if ($(this).is('.disabled'))
					return;
				
				wasButtonActiveBeforeDown = $(this).hasClass('active');
				$(this).addClass('active');
			});
			buttonDOM.mouseup(function(){
				if ($(this).is('.disabled'))
					return;
				
				if ( ! wasButtonActiveBeforeDown)
					$(this).removeClass('active');
			});
		}
	}
	
	function fixIEChildProperties(buttonGroup) {
		buttonGroup.find('li:first-child').addClass('first-child');
		buttonGroup.find('li:only-child').addClass('only-child');
		buttonGroup.find('li:last-child').addClass('last-child');
	}
	
})();

