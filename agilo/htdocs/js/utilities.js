//
// This is meant to be a container of js functions of general purpose utility.
//
// It is included in theme.html so we can use them anywhere.
//

// REFACT: consider to move these to agilo.escape.url
/// Encodes all arguments, concatenates them with slashes and prepends the base url if it is set
/// if the last argument is a dictionary, it is used to create a query string
function encodedURLFromComponents() {
	function shouldEncodeParameterAsQueryString(index, arguments) {
		var isLastArgument = index === arguments.length - 1;
		var isNotString = 'object' === typeof(arguments[index]);
		return isLastArgument && isNotString;
	}
	
	var url = BASE_URL;
	
	// if query parameters are undefined -> ignore them
	var arguments = $.makeArray(arguments);
	if (undefined === arguments[arguments.length-1])
		arguments = arguments.slice(0, arguments.length - 1);
	
	// defend against evil extra slashes that give mod_python so much trouble
	if ((/\/$/).test(url))
		url = url.slice(0,-1);
	
	for (var i = 0; i < arguments.length; i++) {
		if (shouldEncodeParameterAsQueryString(i, arguments))
			url += encodedQueryParametersFromDict(arguments[i]);
		else
			url += '/' + encodeURIComponent(arguments[i]);
	}
	return url;
}

function encodedQueryParametersFromDict(aDictionary) {
	var queryComponents = [];
	for (var key in aDictionary)
		queryComponents.push(encodeURIComponent(key) + '=' + encodeURIComponent(aDictionary[key]));
	
	if (0 === queryComponents.length)
		return '';
	
	return '?' + queryComponents.join('&');
}

/**
 Use this like someCallback.bind(this) to bind a specific this inside that callback.
 Especially useful in jquery callbacks to retain an easy reference to the object 
 the callback was defined in. This should relieve us from having to do the 
 'var that = this;' dance most of the time.

 Here's an example usage:
 $('someSelector').click(function(){
 	this.doSomething();
 }.bind(this));

 Since ECMAScript 5, this is part of the Javascript core
 but IE complies to ECMAScript 5 only since version 9
 http://kangax.github.io/es5-compat-table/
 */

if ($.browser.msie && $.browser.version <= 8) {
    Function.prototype.bind = function(thisReplacement) {
    	var targetFunction = this;
    	return function() {
    		return targetFunction.apply(thisReplacement, arguments);
    	};
    };
}
// This monkey-patch provides me with method names in the debugger, instead of the always present 'anonymous'
// See http://dev.jquery.com/ticket/5275
(function() {
	var oldExtend = $.extend;
	
	function isSecondArgumentDictionary(arguments) {
		var methodDict = arguments[1];
		return (2 === arguments.length)
			&& (null !== methodDict || 'object' === typeof(methodDict));
	}
	
	function addMethodNamesOnMethodsInDict(methodDict) {
		for (var key in methodDict) {
			if ($.isFunction(methodDict[key]) 
				&& ! methodDict[key].displayName)
				methodDict[key].displayName = key;
		}
	}
	
	$.extend = function namingExtend() {
		if (isSecondArgumentDictionary(arguments))
			addMethodNamesOnMethodsInDict(arguments[1]);
		
		return oldExtend.apply(this, arguments);
	};
	
	// TODO: add tests for this and make it a patch to jquery proper
	
}());

function forceIE7Redraw(domOrJQuery, optionalTimeout) {
	// $.browser.version is a string - but because of the wonderful js feature of auto conversion this comparison works
	if ( ! $.browser.msie)
		return;
	
	if ($.browser.version >= 8)
		return;
	
	forceIERedraw(domOrJQuery, optionalTimeout);
}

function forceIERedraw(domOrJQuery, optionalTimeout) {
	if ( ! $.browser.msie)
		return;
	
	var timeout = optionalTimeout || 0;
	// having a timeout of 0 was not enough to fix all redraw issues - so we go with a standard of 10 now
	setTimeout(function(){
		$(domOrJQuery).toggleClass('force-ie-redraw').toggleClass('force-ie-redraw');
	}, timeout);
}


function fixIESubmitFunctionOnEnter(aSubmitFunction, form) {
	if (! $.browser.msie)
		return;
	/* IE does not submit certain forms when pressing enter so we need to
	 * add a custom key handler which 'restores' this functionality.
	 * There is a blog post related to that - however I (fs) was not able
	 * to reproduce the conditions mentioned in the post:
	 * http://www.thefutureoftheweb.com/blog/submit-a-form-in-ie-with-enter  
	 */
	var performSubmitOnEnter = function(anEvent) {
		if (anEvent.keyCode == 13) {
			anEvent.preventDefault();
			// fs: We can not use form().submit() because all browsers 
			// (FF 3.5, IE8) will send two POST requests - strange...
			//form.submit();
			aSubmitFunction(anEvent);
		}
	};
	// do not use ':input' here - we need enter in the textfields
	form.find('input').keydown(performSubmitOnEnter);
}

/// Does _NOT_ preserve the order of items! (Actually it does on most browsers - but as far as I know its not guaranteed)
function uniquedArrayFromArray(anArray) {
	var hash = {};
	$.each(anArray, function(index, entry){
		hash[entry] = '';
	});
	var uniquedArray = [];
	for (var key in hash)
		uniquedArray.push(key);
	return uniquedArray;
}

function copyJSON(json) {
	return JSON.parse(JSON.stringify(json));
}

function isEmpty(something) {
	if (undefined === something)
		return true;
	
	if (0 === something.length)
		return true;
	
	// I would like to check for empty dictionaries, but apart from '{}' === JSON.stringify(something) I haven't found a way yet to test this...
	
	return false;
}

// TODO: if possible defer resolving the function to call to make it easier to stub things
(function($){
	
	/// positionSpec: either a number
	function startIndexFromPositionSpec(positionSpec, originalArguments) {
		if ('number' === typeof(positionSpec)) {
			if (positionSpec >= originalArguments.length)
				throwCallbackExtractionError(positionSpec, originalArguments);
			
			return positionSpec;
		}
		
		for (var i = originalArguments.length; i >= 0; i--) {
			if (undefined !== originalArguments[i] 
				&& positionSpec === originalArguments[i])
				return i;
		}
		throwCallbackExtractionError(positionSpec, originalArguments);
	}
	
	function isJustClosure(startIndex, originalArguments) {
		return $.isFunction(originalArguments[startIndex])
			&& undefined === originalArguments[startIndex+1];
	}
	
	function isThisFixerWithClosure(startIndex, originalArguments) {
		return undefined !== originalArguments[startIndex]
			&& $.isFunction(originalArguments[startIndex+1]);
	}
	
	function isObjectWithStringKey(startIndex, originalArguments) {
		return originalArguments[startIndex]
			&& $.isFunction(originalArguments[startIndex][originalArguments[startIndex+1]]);
	}
	
	function throwCallbackExtractionError(positionSpec, originalArguments) {
		throw "You need to provide a valid callback. Supported are (anObject, aStringKey), (aClosure) or (fixedThis, aClosure). You provided: " + positionSpec + ', ' + originalArguments;
	}
	
	/// callback needs to be the last-argument in the function
	$.extractCallbackFromArguments = function(positionSpec, originalArguments) {
		var startIndex = startIndexFromPositionSpec(positionSpec, originalArguments);
		if (isJustClosure(startIndex, originalArguments))
			return originalArguments[startIndex];
		else if (isThisFixerWithClosure(startIndex, originalArguments))
			return originalArguments[startIndex+1].bind(originalArguments[startIndex]);
		else if (isObjectWithStringKey(startIndex, originalArguments)) {
			var callback = originalArguments[startIndex][originalArguments[startIndex+1]];
			return callback.bind(originalArguments[startIndex]);
		}
		else
			throwCallbackExtractionError(positionSpec, originalArguments);
	};
})(jQuery);

/**
 * Easy publish / subscribe api for jquery
 * 
 * Use event-names with namespaces like 'update.ticketID-10' 
 * so you can trigger specific handlers directly.
 * 
 * Inspired by 
 * http://stackoverflow.com/questions/528648/how-to-structure-my-javascript-jquery-code
 * http://plugins.jquery.com/files/jquery.subscribe.1.1.js_0.txt
 * 
 * REFACT: consider to register all bindings on a custom dom-object so they can easily 
 *         be rmoved all together by removing that dom-object
 * TODO: add an easy way to see if specific callbacks are set
 */
(function($, window, slice) {
	// support closure as alternative or closure with bound object
	// Can call in three ways
	// $.observer.addObserver(anEventName, anObject, instanceMethodName)
	// $.observer.addObserver(anEventName, aClosure)
	// $.observer.addObserver(anEventName, thisReplacement, aClosure)
	$.observer = {

		ensureNotificationContainer: function() {
			if (0 !== this.notificationContainer().length)
				return;

			$('body')
				.append('<div id="jquery-observer-notification-container" style="display:none" />');
		},

		notificationContainer: function() {
			return $('#jquery-observer-notification-container');
		},

		addObserver: function(eventName, callbackSpec) {
			this.ensureNotificationContainer();

			var callback = $.extractCallbackFromArguments(callbackSpec, arguments);
			var handler = function() {
				// first argument is the event object - we don't want that
				callback.apply(document, slice.call(arguments, 1));
			};

			this.notificationContainer().bind(eventName, handler);
			return $;
		},

		/// Call without arguments to remove all notifications
		removeObserver: function(eventName) {
			if (undefined === eventName) {
				// remove all notifications
				return this.notificationContainer().remove();
			}
			this.notificationContainer().unbind(eventName);
			return $;
		},

		/// Any extra arguments will be handed to the triggered function
		postNotification: function(eventName) {
			this.notificationContainer().trigger(eventName, slice.call(arguments, 1));
			return $;
		}
	};
})(jQuery, window, Array.prototype.slice);


// Helps prevent crashes due to msie not having a console.log function that is callable
// Also Firefox without Firebug does not have a console symbol available
if (! (window.console && window.console.log))
	window.console = { log: function(){} };



(function(){
	window.agilo = window.agilo || {};
	agilo.toString = function toString() {
		return '#<agilo>';
	};
})();

/// This is intended to be used as a modal dialog box that requires user input to continue
/// Depends on tool.expose.js in htdocs/lib
(function(){
	window.agilo = window.agilo || {};
	agilo.exposedDOM = function exposedDOM(optionalChildSelector) {
		if ( ! $.fn.expose)
			throw "agilo.exposedDOM() requires tools.expose.js to be loaded.";
		
		if (optionalChildSelector)
			return $('#exposed').find(optionalChildSelector);
		else
			return $('#exposed');
	};
	agilo.exposedDOM.show = function show() {
		if (0 === agilo.exposedDOM().length) {
			$('body').append('<div id="exposed" />');
			agilo.exposedDOM().draggable();
		
			// bug 1201: right of exposed dom is pinned to right window border
			if ($.browser.msie && $.browser.version < 8)
				agilo.exposedDOM().width(497);
		}
		agilo.exposedDOM()
			.empty()
			.prepend('<div class="loading">Loading…</div>')
			.show()
			.expose({
				closeOnClick:false, 
				closeOnEsc:false, 
				api:true, 
				maskId:'expose-mask'
			})
			.load();
		return agilo.exposedDOM();
	};

	agilo.exposedDOM.hide = function hide() {
		agilo.exposedDOM().hide().expose().close();
		return agilo.exposedDOM();
	};
})();


// Escaping html made easy
(function(){
	window.agilo = window.agilo || {};
	agilo.escape = {};
	
	agilo.escape.html = function(something) {
		return String(something)
			.replace(/&/g,"&amp;")
			.replace(/</g,"&lt;")
			.replace(/>/g,"&gt;")
			.replace(/"/g,"&quot;");
	};
	
})();

agilo.titleize = function (aString) {
	return aString
		.replace('-', ' ')
		.replace('_', ' ')
		.replace(/(?:^|\W)(\w)/g, function(each) { return each.toUpperCase(); });
};

// Dirty Hacks - perhaps find a better place for them somewhere else?
$(document).ready(manipulateInterface);

function manipulateInterface() {
    var metanav = $('.button.group.metanav');
    metanav.addClass('ready');
    $('.button.group.mainnav').addClass('ready');

    // Get the Buttons
    var login = metanav.find('li:contains("logged in as")');
    var prefs = metanav.find('li a.iconPrefs');
    var session = metanav.find('li a.iconLogin,li a.iconLogout');
    var help = metanav.find('li a:contains("Help/Guide")');

    // Change some of the labels and classes
    login.text(login.text().replace('logged in as','Logged in as'));
    metanav.find('li a.iconLogout').text('Sign out');
    help.text("HELP");
    help.addClass('labelHelp');

    if (window.RUNNING_UNIT_TESTS)
        return;

    var admin = $('.button.group.mainnav li a.iconAdmin');
    var adminURL = admin.attr('href');
    admin.parent().remove();

    // Remove 'About Trac'
    metanav.find('li a.iconAbout').remove();

    // Remove the Search icon and replace the href of the Advanced Search label
    var search = $('.button.group.mainnav li a.iconSearch');
    $('#search_form label a').attr('href', search.attr('href'));
    search.parent().remove();

    // Reorder Metanav Menu
    if ( prefs.parent().detach ) {
        // Prefer the jquery 1.4 method
        metanav.append(prefs.parent().detach());
        if ( admin && admin.length > 0 )
            metanav.append('<li><a href='+adminURL+'>Admin</a></li>');
        metanav.append(session.parent().detach());
        metanav.append(help.parent().detach());
    }
    else {
        // Fall back to the broken jquery 1.2 method
        metanav.append(prefs.parent().clone()); prefs.parent().remove();
        if ( admin && admin.length > 0 )
            metanav.append('<li><a href='+adminURL+'>Admin</a></li>');
        metanav.append(session.parent().clone()); session.parent().remove();
        metanav.append(help.parent().clone()); help.parent().remove();

        // Call this again since cloning the node will lose it
        addPreferenceLinkBehaviour();
    }
};
