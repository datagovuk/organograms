(function() {
  var width = 1000, height = 1000, fontSize = 9;


  function ready() {
    // console.log('ready!');
  }


  function getClosestDistanceBetweenChildren(node, dx) {
    // console.log(node, dx);
    var children = node.children;
    if(children === undefined)
      return dx;


    if(children.length > 1) {
      // Not exhaustive (we should compare all nodes) but seems to work fine
      if(dx > children[1].x - children[0].x)
        dx = children[1].x - children[0].x;
    }

    _.each(children, function(c) {
      dx = getClosestDistanceBetweenChildren(c, dx);
    });

    return dx;
  }

  /*----
  UPDATE
  ----*/
  function update(root) {

    // NB We're reversing x and y so that tree is laid out left to right

    var treeLayout = d3.layout.tree()
        .size([height, width]);

    var nodes = treeLayout(root);
    var links = treeLayout.links(nodes);

    // Compute scale such that text isn't overlapping
    var dis = getClosestDistanceBetweenChildren(root, 1000);
    console.log(dis);
    yScale = fontSize / dis;

    var fteScale = d3.scale.linear().domain([0, 500]).range([0, 100]);

    d3.select('svg g.tree').remove();
    d3.select('svg').append('g').classed('tree', true);

    var diagonalComponent = d3.svg.diagonal()
      .projection(function(d) {
        return [d.y, d.x * yScale];
      });
    var linkPaths = d3.select('svg g.tree')
      .selectAll('path.link')
      .data(links)
      .enter()
      .append('path')
      .classed('link', true)
      .attr('d', diagonalComponent);


    var nodeGroups = d3.select('svg g.tree')
      .selectAll('g.node')
      .data(nodes)
      .enter()
      .append('g')
      .classed('node', true)
      .attr('transform', function(d) {return 'translate(' + d.y + ',' + d.x * yScale + ')';});

    nodeGroups.append('circle')
      .attr('r', 2);

    nodeGroups.append('text')
      .attr('x', 3)
      .attr('y', 3)
      .style('font-size', fontSize + 'px')
      .text(function(d) {
        var ret = d.jobtitle;
        return ret.length > 40 ? ret.substring(0, 40) + '...' : ret;
      });

    nodeGroups.append('rect')
      .classed('count', true  )
      .attr('x', 3)
      .attr('y', -4)
      .attr('width', function(d) {
        if(d.FTE === undefined)
          return 0;
        return fteScale(d.FTE);
      })
      .attr('height', 8);

    // nodeGroups
    //   .append('use')
    //   .attr('xlink:href', '#person-icon');
  }



  function orgSelect(file) {
    d3.json('../wrangling/output/orgs/' + file + '.json', function(err, json) {
      update(json);
    });
    // console.log('load', file);
  }

  dgvis.menu.init(ready, orgSelect);


})();