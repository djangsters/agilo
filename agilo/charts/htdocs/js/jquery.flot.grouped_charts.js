(function ($) {
    function init(plot) {
        plot.hooks.barOffsets.push(modifyOffsets);
    }
    
    function modifyOffsets(flot, series, barOffsets) {
        // TODO: we assumed here that all bar charts should be grouped.
        if ( ! series.bars.group)
            return;
        
        // TODO: currently we assume that we only have bars in our charts
        var numberOfBars = flot.getData().length;
        var widthOfGap = 0.1;
        var widthOfOneBar = (1 - 2 * widthOfGap) / numberOfBars;
        var index = $.inArray(series, flot.getData());
        var newBarLeft = index * widthOfOneBar + barOffsets[0];
        if (series.bars.align !== 'left')
            newBarLeft += widthOfGap;
        var newBarRight = newBarLeft + widthOfOneBar;
        
        barOffsets[0] = newBarLeft;
        barOffsets[1] = newBarRight;
    }
    
    $.plot.plugins.push({
        init: init,
        options: {},
        name: 'grouped-bar-charts',
        version: '0.1'
    });
})(jQuery);