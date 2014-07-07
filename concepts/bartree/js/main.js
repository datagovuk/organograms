(function() {

  var orgData;
  var layerStack = [];

  var d3elements = {
    layers: d3.select('div.layers')
  }






  /*----
  UPDATE
  ----*/
  function update() {
    console.log(layerStack);

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
        return d.Name;
      });

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
      });

    enteringChildren
      .text(function(d) {
      return d.Name;
      })
      .on('click', function(d) {
        layerStack.push(d);
        update();
      });

  }


  d3.json('wrangling/out.json', function(err, data) {
    console.log(data);
    orgData = data;

    layerStack.push(orgData);

    update();
  });


})();
