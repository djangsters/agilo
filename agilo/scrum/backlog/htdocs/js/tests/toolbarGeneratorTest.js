module("toolbar generator", {
	setup: function() {
		this.button1options = { id: 'id1', tooltip: 'mytext 1' };
		this.button1 = agilo.createToolbarButton(this.button1options);
		this.button2options = { id: 'id2', tooltip: 'mytext 2', isActive : true };
		this.button2 = agilo.createToolbarButton(this.button2options);
	},
	teardown: function() {
		$('#test-container')[0].innerHTML = '';
	 }
});

test("can create default single button", function() {
	ok(this.button1.is("li#id1:has(a)"));
	equals(this.button1.find("a").length, 1);
	ok( ! this.button1.is("li.disabled"));
	ok( ! this.button1.is("li.active"));
});

test("can create disabled button", function() {
	var buttonDOM = window.agilo.createToolbarButton({
		id: 'myid',
		isEnabled: false
	});
	ok(buttonDOM.is("li#myid.disabled"));
	ok( ! buttonDOM.is("li#myid.active"));
});

test("can create disabled but active button", function() {
	var buttonDOM = window.agilo.createToolbarButton({
		id: 'myid',
		isEnabled: false,
		isActive: true
	});
	ok(buttonDOM.is("li#myid.disabled"));
	ok(buttonDOM.is("li#myid.active"));
});

test("can create button with callback", function() {
	var sensedDown = undefined;
	var buttonDOM = window.agilo.createToolbarButton({
		clickCallback: function(isDown) {
			sensedDown = isDown;
		},
		id: 'myid'
	});
	equals(sensedDown, undefined);
	buttonDOM.click();
	equals(sensedDown, true);
	buttonDOM.click();
	equals(sensedDown, false);
});

if ($.browser.msie) {
	test("can create button with callback that works in IE", function() {
		// special because we emulate :active with javascript
	
		var sensedDown = undefined;
		var buttonDOM = window.agilo.createToolbarButton({
			clickCallback: function(isDown) {
				sensedDown = isDown;
			},
			id: 'myid'
		});
		equals(sensedDown, undefined);
		buttonDOM.mousedown();
		buttonDOM.mouseup();
		buttonDOM.click();
		equals(sensedDown, true);
		buttonDOM.mousedown();
		buttonDOM.mouseup();
		buttonDOM.click();
		equals(sensedDown, false);
	});

	test("can create disabled with no hover in IE", function() {
		var buttonDOM = window.agilo.createToolbarButton({
			id: 'myid',
			isEnabled: false
		});
		ok( ! buttonDOM.hasClass('active'));
		ok(buttonDOM.hasClass('disabled'));
		buttonDOM.mousedown();
		ok( ! buttonDOM.hasClass('active'));
	});

}

test("can create disabled button with callback that is not called", function() {
	var sensedDown = undefined;
	var buttonDOM = window.agilo.createToolbarButton({
		clickCallback: function(isDown) {
			sensedDown = isDown;
		},
		id: 'myid',
		isEnabled: false
	});
	equals(sensedDown, undefined);
	buttonDOM.click();
	equals(sensedDown, undefined);
});

test("can create button group with multiple buttons", function() {
	var buttonGroup = agilo.createToolbarButtons( [this.button1options, this.button2options] , { id : "fnord"});
	ok(buttonGroup.is("ul#fnord:has(li#id1)"));
	ok(buttonGroup.children("#id1").is(":first-child"));
	ok(buttonGroup.is("ul#fnord:has(li#id2)"));
});

test("can attach button group to toolbar", function() {
	$('#test-container').append("<div class='toolbar top'></div>");

	ok( ! $(".toolbar").is("div:has(ul#fnord)"));
	var buttonGroup = agilo.createToolbarButtons( [this.button1options, this.button2options] , { id : "fnord"});
	ok($(".toolbar").is("div:has(ul#fnord)"));

});

test("can create push button", function() {
	var button = agilo.createToolbarButton({
		isPushButton: true
	});
	button.click();
	ok( ! button.hasClass('active'));
});

test("can disable buttons by adding the '.disabled' class to their li", function() {
	var buttonDOM = window.agilo.createToolbarButton({
		id: 'fnord',
		clickCallback: function() {
			ok(false, "Shouldn't listen to clicks");
		}
	});
	ok( ! buttonDOM.is("li#fnord.disabled"));
	ok( ! buttonDOM.is("li#fnord.active"));
	
	var fnord = buttonDOM.addClass('disabled');
	
	fnord.find('a').click();
	ok(buttonDOM.is("li#fnord.disabled"), "should stay disabled");
	ok( ! buttonDOM.is("li#fnord.active"), "should not be able to be pushed");
});

test("can disable event bubbling when clicking on a button", function() {
	var buttonDOM = window.agilo.createToolbarButton({
		id: 'fnord',
		clickCallback: function(isActive, anEvent) {
			ok (anEvent.isPropagationStopped());
		}
	});
	expect(1);
	buttonDOM.click();
});

test("can disable default action when clicking on a button", function() {
	var buttonDOM = window.agilo.createToolbarButton({
		id: 'fnord',
		clickCallback: function(isActive, anEvent) {
			ok (anEvent.isDefaultPrevented());
		}
	});
	expect(1);
	buttonDOM.click();
});

test("can enable default action when clicking on a button", function() {
	var buttonDOM = window.agilo.createToolbarButton({
		id: 'fnord',
		allowDefaultAction: true,
		clickCallback: function(isActive, anEvent) {
			ok ( ! anEvent.isDefaultPrevented());
		}
	});
	expect(1);
	buttonDOM.click();
});

