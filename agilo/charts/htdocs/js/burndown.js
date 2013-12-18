function Burndown(aBacklogLoader) {
	// TODO: add window check
	// Burndown chart view
	this.loader = aBacklogLoader;
	this.registerForDataChangeNotification();
	this.registerForBacklogFilteringChanges();
	this.burndownValues = null;
	
	this.lastAttributeValue = undefined;
}

$.extend(Burndown.prototype, {
	
	toHTML: function() {
		return '<div id="burndown" class="panel">'
			+	'<h1>Burndown chart</h1>'
			+	'<p class="close"></p>'
			+	'<div id="chart-container" style="background-color:white; padding-top:20px;"></div>'
			+ '</div>';
	},
	
	addToDOM: function() {
		$("body").append(this.toHTML());
		this.addToggleButton();
		this.connectCloseButton();
		this.enableDrag();
	},
	
	addToggleButton: function() {
		var that = this;

		var toggleOptions = {
				id : 'burndown-button',
				tooltip : 'Show or hide the Burndown chart',
				clickCallback: function(isActive){
					that.toggleBurndown();
				}
			 };

		agilo.createToolbarButtons(
				[toggleOptions],
				{id: "burndown-button-container"});
	},
	
	connectCloseButton: function() {
		var that = this;
		$("#burndown .close").click(function(anEvent) {
		    anEvent.preventDefault();
			$('#burndown-button').toggleClass('active');
			that.toggleBurndown();
		});
	},
	
	enableDrag: function() {
		this.dom().draggable({ stack: { group: '.panel', min: 999 }, containment: 'window' });
	},
	
	dom: function() {
		return $("#burndown");
	},
	
	chartContainerSelector: function() {
		return '#chart-container';
	},
	
	rewirePlotBurndown: function() {
		this.plotBurndown = window.plotBurndown;
		
		window.plotBurndown = function(unusedSelector, values) {
			this.updateBurndownWithValues(values);
		}.bind(this);
	},
	
	plotBurndown: function(){
		throw Error("Need to call rewirePlotBurndown before this object can plot burndown charts.");
	},
	
	plotBurndownChartIfNecessary: function() {
		if (this.hasPlottedBurndownChart)
			return;
		
		$(this.chartContainerSelector())
			.empty()
			.append('<div id="burndownchart" style="height:350px; width:750px; position:relative;" />');
		this.plotBurndown(this.chartContainerSelector() + ' #burndownchart', this.burndownValues);

		// Somehow the problem doesn't happen by itself anymore, but instead 
		// the overdraw is actually triggered by the redraw of .main. ????
		// Leaving the force redraws as comments as we don't know what triggered the change in behaviour
		
		// ie 7 collapses the main view on showing the burndown
		// and lower rows are drawn on top of other rows
		// forceIE7Redraw('.main', 100);
		
		// ie 7 overdraws the lower part of the backlog on top of the upper one 
		// only happens (for me) if the previous redraw takes place...
		// forceIE7Redraw('[id^=ticketID] .id', 200);
		
		this.hasPlottedBurndownChart = true;
	},
	
	toggleBurndown: function() {
		this.dom().toggle();
		this.plotBurndownChartIfNecessary();
	},
	
	// Reloading the burndown chart .............................................
	
	registerForBacklogFilteringChanges: function() {
		if ( ! this.loader.shouldReloadBurndownFilteredByComponent())
			return;
		$.observer.addObserver(BacklogFiltering.DID_CHANGE_FILTER_SETTINGS, 
			this, this.reloadBurndownChartFilteredByComponent);
	},
	
	registerForDataChangeNotification: function() {
		$.observer.addObserver('DID_CHANGE_BURNDOWN_DATA',
			this, this.reloadBurndownChart);
	},

	reloadBurndownChartFilteredByComponent: function(aFilter) {
		if ( ! this.didChangeAttributeValue(aFilter))
			return;
		this.reloadBurndownChart(aFilter);
	},
	
	reloadBurndownChart: function(optionalFilter) {
		if ( ! this.shouldLoadBurndownValues())
			return;
		
		var loader = this.loader.burndownValuesLoader;
		if (optionalFilter)
			loader.setFilterBy(optionalFilter.attributeFilteringValue());

		loader.startLoading(this.updateBurndownWithValues.bind(this));
	},
	
	shouldLoadBurndownValues: function() {
		return 'sprint' === this.loader.info().type;
	},
	
	didChangeAttributeValue: function(aFilter) {
		if (aFilter.attributeFilteringValue() === this.lastAttributeValue)
			return false;
		
		this.lastAttributeValue = aFilter.attributeFilteringValue();
		return true;
	},
	
	updateBurndownWithValues: function(burndownValues) {
		this.burndownValues = burndownValues;
		
		
		this.hasPlottedBurndownChart = false;
		if (this.dom().is(':visible'))
			this.plotBurndownChartIfNecessary();
	},
	
	missingCommaErrorPreventer:''
});

function plotBurndown(selector, data) {
	function buildDayBands(weekends, color) {
		var markings = [];
		for (var i = 0; i < weekends.length; i=i+1) {
			var weekend_day = weekends[i];
			var start = weekend_day[0];
			var end = weekend_day[1];
			markings.push({ xaxis: { from: start, to: end }, color: color });
		}
		return markings;
	}

	function drawMarkings() {
		var weekendMarkings = buildDayBands(data.weekend_data, "#eee");
		// today bar should overlay the weekend so it must be rendered afterwards
		var todayMarkings = buildDayBands(data.today_data, data.today_color);
		return weekendMarkings.concat(todayMarkings);
	}
	
	/// max value of all series - except the trendline
	function maxGraphValueWithoutTrends() {
		function max(series) {
			var data = $.map(series, function(each) { return each[1]; });
			return Math.max.apply(Math, data);
		}
		return Math.max(
			max(data.capacity_data),
			max(data.ideal_data),
			max(data.remaining_times)
		);
	}
	
	var options = {
			xaxis: { ticks: data.ticks },
			yaxis: { min: 0, max: 20 + maxGraphValueWithoutTrends() }, // 20: arbitrary head room above the graph
			grid: { markings: drawMarkings }
		};

  var plotData = [
    // trend data comes first so it is drawn on the lowest layer
    {
      data: data.trend_data,
      color: "orange",
      label: "Trend",
      lines: { show: true, lineWidth: 1},
      shadowSize: 0
    }
  ];

  var hasCapacity = data.capacity_data && data.capacity_data.length;
  if ( hasCapacity ) {
    plotData.push({
      data: data.capacity_data,
      color: "#5c7bbe",
      label: "Capacity",
      lines: { show: true, lineWidth: 1},
      shadowSize: 0
    });
  }

  plotData.push(
    {
      data: data.ideal_data,
      color: "navy",
      label: "Ideal Burndown",
      lines: { show: true, lineWidth: 2},
      shadowSize: 3
    },
    {
      data: data.remaining_times,
      color: "#4BAAFF",
      label: "Actual Burndown",
      lines: { show: true, lineWidth: 3 },
      shadowSize: 5
    });

	var plot = jQuery.plot(jQuery(selector), plotData, options);
	if (data.remaining_times.length > 0) {
    var index_series_to_highlight = hasCapacity ? 3 : 2;
		var index_current_point = data.remaining_times.length - 1;
		plot.highlight(index_series_to_highlight, index_current_point);
	}
	
	return plot;
}
