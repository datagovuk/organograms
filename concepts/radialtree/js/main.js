(function() {
  var width = 720;
  var fteScale = d3.scale.sqrt().domain([0, 2000]).range([0, 50]);

  var voronoi = d3.geom.voronoi()
    .x(function(d) {return d.projected.x;})
    .y(function(d) {return d.projected.y;})
    .clipExtent([[-0.513 * width, -0.513 * width], [0.513 * width, 0.513 * width]]);


  function template(d) {
      var fields = [
        {field: 'grade', label: 'Grade'},
        {field: 'name', label: 'Name'},
        {field: 'FTE', label: 'No. full time positions'},
        {field: 'unit', label: 'Unit'}
      ];
      var ret = '<div>';
      ret += '<h1>' + d.jobtitle + '</h1>';

      _.each(fields, function(f) {
        if(d[f.field] !== undefined)
          ret += '<div>' + f.label + ': ' + d[f.field] + '</div>';
      });

      if(d.payfloor !== undefined) {
        ret += '<div>Pay range: £' + d.payfloor + ' - £' + d.payceiling;
      }
      ret += '</div>';
      return ret;
  }

  function polygon(d) {
    return "M" + d.join("L") + "Z";
  }

  function projection(d) {
    return [d.y, d.x / 180 * Math.PI];
  }

  // console.log(voronoi);


  function ready() {
    // console.log('ready!');
  }


  /*----
  UPDATE
  ----*/
  function update(root) {

    var treeLayout = d3.layout.tree()
        .size([0.5 * width, 0.5 * width]);

    var diagonalComponent = d3.svg.diagonal.radial()
        .projection(projection);

    var nodes = treeLayout(root);
    var links = treeLayout.links(nodes);

    d3.select('svg g.wrapper g.tree').remove();
    d3.select('svg g.wrapper').append('g').classed('tree', true);


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
      .classed('node', true);


      // .attr('transform', function(d) {return 'translate(' + d.y + ',' + d.x + ')';});

    nodeGroups.append('circle')
      .attr("transform", function(d) { return "rotate(" + (d.x - 90) + ")translate(" + d.y + ")"; })
      .attr('r', function(d) {
        return d.depth === 0 ? 3 : 1;
      });

    nodeGroups.append('circle')
      .attr("transform", function(d) { return "rotate(" + (d.x - 90) + ")translate(" + d.y + ")"; })
      .classed('fte', true)
      .attr('r', function(d) {
        return d.FTE !== undefined ? fteScale(d.FTE) : 0;
      });
  }

  function updateVoronoi(root) {
    // Flatten tree by selecting nodes
    var nodeSelection = d3.select('svg g.tree').selectAll('g.node');
    var nodes = [];
    _.each(nodeSelection[0], function(n) {
      var d = n.__data__;
      var ang = d.x * Math.PI / 180;
      var dis = d.y;
      d.projected = {
        x: dis * Math.sin(ang),
        y: -dis * Math.cos(ang)
      };
      nodes.push(d);
    });
    // console.log(nodes);

    // console.log(voronoi);
    var paths = voronoi(nodes);

    nodeSelection
      .append('path')
      .classed('voronoi', true)
      .datum(function(d, i) {
        return paths[i];
      })
      .attr('d', polygon)
      .on('mouseover', function(d) {
        var node = this.parentNode;
        d3.select(node)
          .classed('hover', true);
        d3.select('.info')
          .html(function() {
            return template(node.__data__);
          });
        // console.log(this.parentNode.__data__);
      })
      .on('mouseout', function() {
        d3.select(this.parentNode)
          .classed('hover', false);
      });
  }



  function orgSelect(file) {
    d3.json('../wrangling/output/orgs/' + file + '.json', function(err, json) {
      update(json);
      updateVoronoi(json);
    });
    // console.log('load', file);
  }

  dgvis.menu.init(ready, orgSelect);


})();