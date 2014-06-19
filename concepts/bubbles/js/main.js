(function() {

  var lu, layers = [];


  /*----
  EVENTS
  ----*/
  function statusTemplate(d) {
    function wrap(t) {
      return '<div>' + t + '</div>';
    }
    var ret = wrap(d.title + (d.senior ? ' (Senior)' : ' (Junior)'));
    ret += d.senior ? wrap(' Total headcount: ' + (+d.headCount.toFixed(1))) : '';
    ret += wrap(' FTE: ' + d.fte);
    return ret;
  }

  function updateStatus(d) {
    d3.select('.hover.status')
      .html(statusTemplate(d));
  }

  function updateLayerStatus() {
    var topLayer = layers[layers.length - 1];
    title = topLayer.title;

    d3.select('.layer.status')
      .text('You are viewing headcount of ' + title + ' (Natural England)');

  }

  function clickCircle(d) {
    d3.event.stopPropagation();

    if(!d.senior)
      return;
    pushLayer(d.id);

    updateLayerStatus();
    // console.log(d);
  }


  /*--------------
  LAYER MANAGEMENT
  --------------*/
  function pushLayer(id) {
    // Fade current layer

    console.log('pushing');

    if(layers.length > 0) {
      var topLayer = layers[layers.length - 1];
      topLayer.layer
        .transition()
        .duration(500)
        .style('opacity', 0)
        .each('end', function() {
          d3.select(this)
            .style('display', 'none');
        });
    }

    var newLayer = d3.select('.layers')
      .append('g')
      .classed('layer ' + layers.length, true);


    var bubble = new dg.BubbleLayer({
      lu: lu,
      layer: newLayer,
      mouseover: updateStatus,
      click: clickCircle
    });

    bubble.construct(id);

    layers.push({
      title: lu[id].title,
      layer: newLayer
    });
  }

  function popLayer() {
    if(layers.length < 2)
      return;

    var topLayer = layers.pop()
    topLayer.layer.remove();

    topLayer = layers[layers.length - 1];
    topLayer.layer
      .transition()
      .style('display', 'block')
      .duration(500)
      .style('opacity', 1);
  }



  // Rough and ready loading
  d3.csv('data/300913-Natural-England-Organogram-junior.csv', function(err, csvJ) {
    d3.csv('data/300913-Natural-England-Organogram-senior.csv', function(err, csvS) {
      dg.data.init(csvJ, csvS);

      lu = dg.data.lookup("1");

      pushLayer("1");
      updateLayerStatus();

      d3.select('svg')
        .on('click', function() {
          popLayer();
          updateLayerStatus();
        });

    });
  });


})();


// (function(){
//   d3.select('#chart')
//   .append('svg')
// 	.append('line')
// 	.attr({x0: 10, y0: 10, x1: 50, y1: 50});
// })();