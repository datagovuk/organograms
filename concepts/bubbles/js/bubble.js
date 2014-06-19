var dg = dg || {};

dg.BubbleLayer = function(config) {
  // Bubble layer object constructor

  this.config = config;

  // this.yScale = d3.scale.linear()
  //   .domain(config.yDomain)
  //   .range(config.yRange);
}

dg.BubbleLayer.prototype.appendValues = function(nodes) {
  // Set node values according to headcount (senior) or fte (junior)
  nodes = _.map(nodes, function(d) {
    d.value = d.senior ? d.headCount : +d.fte;
    return d;
  });
  return nodes;
}

dg.BubbleLayer.prototype.appendRadii = function(nodes) {
  var radiusScale = d3.scale.sqrt().domain([0, 2000]).range([2, 150]);
  nodes = _.map(nodes, function(d) {
    d.radius = radiusScale(d.value);
    return d;
  });
  return nodes;
}


// Interface
dg.BubbleLayer.prototype.construct = function(id) {
  // console.log('making bubble layer from ', id, this.config.lu[id]);

  var node = this.config.lu[id];

  var nodes = node.directReports;
  nodes = this.appendValues(nodes);
  nodes = this.appendRadii(nodes);

  var colorScale = d3.scale.category10();

  var force = d3.layout.force()
      .gravity(0.2)
      .nodes(nodes)
      .size([500, 500]);

  force.start();

  var circles = this.config.layer
    .selectAll('circle')
    .data(nodes)
    .enter()
    .append('circle')
    .attr('r', function(d) {
      return d.radius;
    })
    .style('fill', function(d, i) {
      return d.senior ? colorScale(i) : '#aaa';
    })
    .on('mouseover', this.config.mouseover)
    .on('click', this.config.click);

  var labels = this.config.layer
    .selectAll('text')
    .data(nodes)
    .enter()
    .append('text')
    .text(function(d) {return d.radius > 20 ? d.title : '';});


  force.on("tick", function(e) {
    var q = d3.geom.quadtree(nodes), // this constructs a quadtree from the circles (nodes). Each circle has .x and .y values
        i = 0,
        n = nodes.length;

    while (++i < n) q.visit(collide(nodes[i]));

    circles
      .attr("cx", function(d) { return d.x; })
      .attr("cy", function(d) { return d.y; });

    labels
      .attr("x", function(d) { return d.x; })
      .attr("y", function(d) { return d.y; });

  });

  function collide(node) {
    // Compare 'node' with other nodes
    var r = node.radius + 30,
        nx1 = node.x - r,
        nx2 = node.x + r,
        ny1 = node.y - r,
        ny2 = node.y + r;
    return function(quad, x1, y1, x2, y2) {
      if (quad.point && (quad.point !== node)) {
        var x = node.x - quad.point.x,
            y = node.y - quad.point.y,
            l = Math.sqrt(x * x + y * y),
            r = node.radius + quad.point.radius;
        if (l < r) {
          l = ((l - r) / l) * .5;
          x *= l;
          y *= l;
          node.x -= x;
          node.y -= y;
          quad.point.x += x;
          quad.point.y += y;
        }
      }
      return x1 > nx2 || x2 < nx1 || y1 > ny2 || y2 < ny1;
    };
  }



  // console.log(nodes);
}

// dg.BubbleLayer.prototype.update = function(data) {
// }

// dg.BubbleLayer.prototype.highlightDatum = function(i, on) {
// }
