module('url helpers', {
	setup: function() {
		BASE_URL = '';
	}
});

test("url method concatenates arguments to paths", function() {
	equals(encodedURLFromComponents('foo', 'bar', 'baz'), '/foo/bar/baz');
});

test("url method can encode special characters correctly", function() {
	equals(encodedURLFromComponents('fnord'), '/fnord');
	equals(encodedURLFromComponents('these.are_non!probl', 'ematic-characters'), '/these.are_non!probl/ematic-characters');
	
	equals(encodedURLFromComponents('/'), '/%2F');
	equals(encodedURLFromComponents('#'), '/%23');
	equals(encodedURLFromComponents(':'), '/%3A');
	equals(encodedURLFromComponents('%'), '/%25');
	equals(encodedURLFromComponents('$'), '/%24');
	equals(encodedURLFromComponents('?'), '/%3F');
	equals(encodedURLFromComponents(' '), '/%20');
	equals(encodedURLFromComponents(','), '/%2C');
	equals(encodedURLFromComponents('+'), '/%2B');
});

test("url method respects base path", function() {
	BASE_URL = 'fnord';
	equals(encodedURLFromComponents(), 'fnord');
	equals(encodedURLFromComponents('foo', 'bar'), 'fnord/foo/bar');
});

test("url method can cope with extra slashes in the base url", function() {
	BASE_URL = 'fnord/';
	equals(encodedURLFromComponents(), 'fnord');
	equals(encodedURLFromComponents('foo'), 'fnord/foo');
	
});

test("can encode dictionary to query parameters", function() {
	equals(encodedQueryParametersFromDict({}), '');
	equals(encodedQueryParametersFromDict({foo:'bar'}), '?foo=bar');
	equals(encodedQueryParametersFromDict({foo:'bar', baz:'quux'}), '?foo=bar&baz=quux');
	equals(encodedQueryParametersFromDict({foo:'bar baz'}), '?foo=bar%20baz');
});

test("encodedURLFromComponents supports dictionary to query string as last parameter", function() {
	equals(encodedURLFromComponents({}), '');
	equals(encodedURLFromComponents('fnord', {}), '/fnord');
	equals(encodedURLFromComponents('fnord', {foo:'bar'}), '/fnord?foo=bar');
});

test("url encoding doesn't confuse number with dictionary", function() {
	equals(encodedURLFromComponents('ticket', 23), '/ticket/23');
});

module('jquery extensions');

test("extend sets displayName on methods in dict", function() {
	var dict = $.extend({}, { foo: function(){}, bar: function(){} });
	equals(dict.foo.displayName, 'foo');
	equals(dict.bar.displayName, 'bar');
});

test("extend doesn't do anything with non functions", function() {
	var dict = $.extend({}, { foo: 'fnord', bar: 42 });
	equals(dict.foo.displayName, undefined);
	equals(dict.bar.displayName, undefined);
});

module("generic helpers");

test("can unique entries in array for strings", function() {
	var actual = uniquedArrayFromArray(['foo', 'foo', 'foo']);
	same(actual, ['foo']);
	
	actual = uniquedArrayFromArray(['foo', 'bar', 'bar']);
	same(actual, ['foo', 'bar']);
});

test("isEmpty", function() {
	ok(isEmpty(undefined));
	ok(isEmpty(""));
	ok(isEmpty([]));
	
	ok( ! isEmpty('foo'));
	ok( ! isEmpty(['foo']));
});



module("html generation helpers");

test("basic escapeing of html characters", function() {
	equals('', agilo.escape.html(''));
	equals('&amp;', agilo.escape.html('&'));
	equals('&lt;', agilo.escape.html('<'));
	equals('&gt;', agilo.escape.html('>'));
});

test("escaping works on longer string", function() {
	equals('foo&lt;bar&amp;baz&gt;quux', agilo.escape.html('foo<bar&baz>quux'));
});

test("can escape non string things", function() {
	equals('23', agilo.escape.html(23));
});

test("can escape field contents", function() {
	equals("&quot;", agilo.escape.html('"'));
});





module('callback extractor');

test("can extract closure", function() {
	expect(1);
	$.extractCallbackFromArguments(0, [function(){ ok(true); }])();
});

test("can extract closure with fixed this pointer", function() {
	expect(1);
	$.extractCallbackFromArguments(0, ['fnord', function(){ equals('fnord', this); }])();
});

test("can extract object with key", function() {
	expect(1);
	var object = { fnord: function(){ same(object, this); } };
	$.extractCallbackFromArguments(0, [object, 'fnord'])();
});

test("can extract object with ley even when first object is a function", function() {
	expect(1);
	var object = function(){};
	object.fnord = function(){ same(object, this); };
	$.extractCallbackFromArguments(0, [object, 'fnord'])();
});

test("can specify first callbackspec argument instead of index", function() {
	expect(1);
	var callback = function(){ ok(true); };
	$.extractCallbackFromArguments(callback, [callback])();
});

test("can extract from real arguments array", function() {
	expect(1);
	var array = (function(){ return arguments; })(function(){ ok(true); });
	$.extractCallbackFromArguments(0, array)();
});

test("throws if first argument is neither number nor from arguments", function() {
	expect(1);
	try {
		$.extractCallbackFromArguments('fnord', ['foo', function(){}]);
	}
	catch (error) {
		assertMatches(error, /need to provide a valid callback/);
	}
});


test("throws when argspec index bigger than function arguments is chosen", function() {
	expect(1);
	try {
		$.extractCallbackFromArguments(100, ['foo', function(){}]);
	}
	catch (error) {
		assertMatches(error, /need to provide a valid callback/);
	}
});


test("throw when no callback could be extracted", function() {
	expect(1);
	try {
		$.extractCallbackFromArguments('test', 'foo');
	} 
	catch (error) {
		assertMatches(error, /need to provide a valid callback/);
	}
});



module('publish / subscribe', {
	teardown: function(){
		$.observer.removeObserver();
	}
});

test("can subscribe method on object", function() {
	expect(1);
	var object = {
		method: function() { ok(true); }
	};
	$.observer.addObserver('test', object, 'method');
	$.observer.postNotification('test');
});

test("can publish with arguments", function() {
	expect(2);
	var object = {
		method: function(first, second) {
			equals(first, 'foo');
			equals(second, 'bar');
		}
	};
	$.observer.addObserver('test', object, 'method');
	$.observer.postNotification('test', 'foo', 'bar');
});

test("can subscribe with closure", function() {
	expect(1);
	$.observer.addObserver('test', function(){ ok(true); });
	$.observer.postNotification('test');
});

test("can subscribe with closure and publish arguments", function() {
	expect(1);
	$.observer.addObserver('test', function(arg){ equals('fnord', arg); });
	$.observer.postNotification('test', 'fnord');
});


test("can subscribe with closure and bound this", function() {
	expect(1);
	$.observer.addObserver('test', 'thisReplacement', function(){ equals(this, 'thisReplacement'); });
	$.observer.postNotification('test');
});

test("can unsubscribe event", function() {
	expect(1); // expect(0) disables expectations...
	$.observer.addObserver('test', function(){ ok(true); });
	$.observer.postNotification('test');
	$.observer.removeObserver('test');
	$.observer.postNotification('test');
});

test("can unsubscribe namespaced events by namespace", function() {
	expect(1); // expect(0) disables expectations...
	$.observer.addObserver('test.foo', function(){ ok(true); });
	$.observer.postNotification('test.foo');
	$.observer.removeObserver('.foo');
	$.observer.postNotification('test.foo');
});

// not yet possible
// test("can unsubscribe by basename", function() {
// 	expect(1); // expect(0) disables expectations...
// 	$.observer.addObserver('test.foo', function(){ ok(true); });
// 	$.observer.postNotification('test.foo');
// 	$.observer.removeObserver('test');
// 	$.observer.postNotification('test.foo');
// });


test("throws if no valid callback was provided", function() {
	expect(1);
	try {
		$.observer.addObserver('test', 'foo');
	} 
	catch (error) {
		assertMatches(error, /need to provide a valid callback/);
	}
});

test("can register only for scoped callbacks", function() {
	expect(1);
	$.observer.addObserver('test.foo', function() { ok(true); });
	$.observer.addObserver('test.bar', function() { ok(false); });
	$.observer.postNotification('test.foo');
});

test("can unregister all callbacks that where registered", function() {
	expect(1);
	$.observer.addObserver('test', function(){ ok(true); });
	$.observer.postNotification('test');
	// Currently unbinds everything - bound to window. Not Nice, but works well for unittests
	$.observer.removeObserver();
	$.observer.postNotification('test');
});





module("exposed dom elements", {
	setup: function() {
	},
	teardown: function() {
		$('#exposed').remove();
	}
});

test("throws if tools.expose is not loaded", function() {
	expect(1);
	var originalExpose = $.fn.expose;
	$.fn.expose = undefined;
	
	try {
		agilo.exposedDOM();
	} catch (e) {
		assertMatches(e, /agilo\.exposedDOM\(\) requires tools\.expose.js to be loaded\./);
	}
	
	$.fn.expose = originalExpose;
});


test("can expose div for focused operations", function() {
	equals($('#exposed').length, 0);
	equals(agilo.exposedDOM().length, 0);

	agilo.exposedDOM.show();
	ok($('#exposed').is(':visible'));
	equals(agilo.exposedDOM().length, 1);

	agilo.exposedDOM.hide();
	equals(agilo.exposedDOM().length, 1);
	ok($('#exposed').is(':hidden'));
});

test("showing exposed shows loading indicator", function() {
	agilo.exposedDOM.show();
	equals(agilo.exposedDOM().text(), 'Loading…');
	agilo.exposedDOM().html('<div>Some blabla</div>');
	agilo.exposedDOM.hide();
	agilo.exposedDOM.show();
	equals(agilo.exposedDOM().text(), 'Loading…');
});

test("show and hide return the dom object for chaining", function() {
	ok(agilo.exposedDOM.show().is('#exposed'));
	ok(agilo.exposedDOM.hide().is('#exposed'));
});
