(function() {

  var orgData;
  var layerStack = [];

  var d3elements = {
    layers: d3.select('div.layers')
  }

  var xScale = d3.scale.linear().domain([0, 200000]).range([0, 1000]);
  var colorScale = d3.scale.category10();




  /*----
  UPDATE
  ----*/
  function updateLayerStack(layerData, layerDepth) {
    // console.log('updating stack: ', layerData, layerDepth);
    // Remove layers
    var stackDepth = layerStack.length;
    for(var i = layerDepth; i < stackDepth - 1; i++) {
      layerStack.pop();
    }

    layerData.depth = layerDepth;
    layerStack[layerDepth] = layerData;
  }

  function update() {
    // console.log(layerStack);

    // Layers
    var uLayers = d3elements.layers
      .selectAll('.layer')
      .data(layerStack, function(d) {return d.Name + d.Subtotal;});

    var enteringLayers = uLayers.enter()
      .append('div')
      .classed('layer', true);

    enteringLayers
      .append('h2')
      .text(function(d) {
        var ret = d.Name;
        if(_.has(d, 'FTE'))
          ret += ' (' + d.FTE + ')';
        return ret;
      });

    uLayers.exit().remove();

    // Children
    var uChildren = enteringLayers
      .append('div')
      .classed('children', true)
      .selectAll('div.child')
      .data(function(d) {
        return _.has(d, 'Children') ? d.Children : [];
      });

    var enteringChildren = uChildren.enter()
      .append('div')
      .classed('child', true)
      .classed('junior', function(d) {
        return _.has(d, 'Junior');
      })
      .style('width', function(d) {
        return xScale(d.Subtotal) + 'px';
      })
      .style('background-color', function(d, i) {
        return colorScale(i);
      });

    enteringChildren
      .text(function(d) {
        var ret = d.Name;
        if(_.has(d, 'FTE'))
          ret += ' (' + d.FTE + ')';
        return ret;
      })
      .on('click', function(d, i, j) {
        var layerDepth = d3.select(this.parentNode.parentNode).datum().depth;
        updateLayerStack(d, layerDepth + 1);
        update();
      });

  }


  d3.json('wrangling/out.json', function(err, data) {
    // console.log(data);
    orgData = data;

    updateLayerStack(orgData, 0);
    // layerStack.push(orgData);

    update();
  });


})();
