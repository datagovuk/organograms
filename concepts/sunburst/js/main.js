(function() {

  var radius = 300;

  var x = d3.scale.linear()
    .range([0, 2 * Math.PI]);

  var y = d3.scale.linear()
    .range([0, radius]);

  var partitionLayout = d3.layout.partition()
    .value(function(d) { return d.FTE; });

  var color = d3.scale.category20c();

  var arc = d3.svg.arc()
    .startAngle(function(d) { return Math.max(0, Math.min(2 * Math.PI, x(d.x))); })
    .endAngle(function(d) { return Math.max(0, Math.min(2 * Math.PI, x(d.x + d.dx))); })
    .innerRadius(function(d) { return Math.max(0, y(d.y)); })
    .outerRadius(function(d) { return Math.max(0, y(d.y + d.dy)); });

  function arcTween(d) {
    var xd = d3.interpolate(x.domain(), [d.x, d.x + d.dx]),
        yd = d3.interpolate(y.domain(), [d.y, 1]),
        yr = d3.interpolate(y.range(), [d.y ? 20 : 0, radius]);
    return function(d, i) {
      return i
          ? function(t) { return arc(d); }
          : function(t) { x.domain(xd(t)); y.domain(yd(t)).range(yr(t)); return arc(d); };
    };
  }

  var toolTip = animdata.d3.toolTip()
    .templateFunc(function(d) {
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
    })
    .width(400)
    .element('.node');


  function ready() {
  }

  /*----
  UPDATE
  ----*/
  function updateTooltip() {
    d3.select('.chart')
      .call(toolTip);
  }

  function update(root) {
    d3.select('.chart svg .nodes').remove();
    d3.select('.chart svg .wrapper').append('g').classed('nodes', true);

    var nodes = partitionLayout.nodes(root);
    // console.log(nodes);

    var sunburst = d3.select('.chart svg .nodes')
      .selectAll('path')
      .data(nodes)
      .enter()
      .append('path')
      .classed('node', true)
      .attr('d', arc)
      .style('fill', function(d) { return color((d.children ? d : d.parent).name); })
      .on('click', click);
    // outputChildren([root], d3.select('.chart .nodes')[0][0]);

    function click(d) {
      sunburst.transition()
        .duration(750)
        .attrTween("d", arcTween(d));
    }

    // Reset click
    click(d3.selectAll('.chart svg .node')[0][0].__data__);

    updateTooltip();
  }

  function orgSelect(file) {
    d3.json('../wrangling/output/orgs/' + file + '.json', function(err, json) {
      update(json);
    });
    // console.log('load', file);
  }

  dgvis.menu.init(ready, orgSelect);


})();