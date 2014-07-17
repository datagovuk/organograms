(function() {
  var width = 200, layoutWidth = 720; // the layout arrangement is dependent on the size! So let's scale down ourselves.
  var layoutScale = width / layoutWidth;
  var fteScale = d3.scale.sqrt().domain([0, 2000]).range([0, 10]);

  var treeLayout = d3.layout.tree()
      .size([0.5 * layoutWidth, 0.5 * layoutWidth]);

  var diagonalComponent = d3.svg.diagonal.radial()
      .projection(function(d) { return [d.y, d.x / 180 * Math.PI]; });

  function ready() {
    // console.log('ready!');
  }


  /*----
  UPDATE
  ----*/
  function makeTree(root, container) {
    var nodes = treeLayout(root);
    var links = treeLayout.links(nodes);

    // container = d3.select(container);

    var linkPaths = container
      .selectAll('path.link')
      .data(links)
      .enter()
      .append('path')
      .classed('link', true)
      .attr('d', diagonalComponent);

    var nodeGroups = container
      .selectAll('g.node')
      .data(nodes)
      .enter()
      .append('g')
      .classed('node', true)
      .attr("transform", function(d) { return "rotate(" + (d.x - 90) + ")translate(" + d.y + ")"; });
      // .attr('transform', function(d) {return 'translate(' + d.y + ',' + d.x + ')';});

    nodeGroups.append('circle')
      .attr('r', 1);

    nodeGroups.append('circle')
      .classed('fte', true)
      .attr('r', function(d) {
        return d.FTE !== undefined ? fteScale(d.FTE) : 0;
      });
  }



  function orgPush(file) {
    d3.json('../wrangling/output/orgs/' + file + '.json', function(err, json) {
      // console.log(json);

      var container = d3.select('.chart')
        .append('svg')
        .attr('width', width)
        .attr('height', width);

      treeContainer = container
        .append('g')
        .attr('transform', 'translate(' + 0.5 * width + ',' + 0.5 * width + ')scale(0.18)');

      container
        .append('text')
        .classed('title', true)
        .text(json.jobtitle)
        .attr('y', 10);

      makeTree(json, treeContainer);

    });
    // console.log('load', file);
  }

  d3.json('../wrangling/output/depts_and_orgs.json', function(err, data) {
    // console.log(data);
    departments = data;

    _.each(departments, function(dept) {
      _.each(dept.organisations, function(org) {
        // console.log(org.filename);
        orgPush(org.filename);
      });
    });
  });


})();