(function() {

  var toolTip = animdata.d3.toolTip()
    .title('Hey')
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
    .element('div.label');


  function ready() {
    // Collapsible nodes - this works fine, but needs more work to make it usable. Not convinced it's necessary at all...
    // $('.chart').on('click', '.label', function() {
    //   var childrenContainer = $(this.parentNode).find('.children').first();
    //   childrenContainer.slideToggle();
    // });
  }

  function peopleIcons(i) {
    var single = '<i class="fa fa-male group-1"></i>';
    var group10 = '<i class="fa fa-male group-10"></i>';
    var ret = '';

    var num10Groups = Math.floor(i / 10);
    for(var ii=0; ii<num10Groups; ii++)
      ret += group10;

    var remainder = Math.round(i % 10);
    for(var ii=0; ii<remainder; ii++)
      ret += single;

    return ret;
  }


  /*----
  UPDATE
  ----*/
  function outputChildren(children, element) {
    // Recursively output children into element

    d3.select(element)
      .selectAll('div.node')
      .data(children)
      .enter()
      .append('div')
      .classed('node', true)
      .classed('junior', function(d) {return d.junior === true;})
      .each(function(d) {
        d3.select(this)
          .append('div')
          .classed('label', true)
          .html(function(d) {
            var ret = '';
            ret += d.jobtitle;

            var people = '';
            if(d.FTE !== undefined) {
              people = peopleIcons(d.FTE);
              ret += ' ' + people;
            }

            return ret;
          });

        if(d.children === undefined)
          return;
        var newNode = d3.select(this)
          .append('div')
          .classed('children', true);
        outputChildren(d.children, newNode[0][0]);
      });
  }


  function updateTooltip() {
    d3.select('.chart .nodes')
      .call(toolTip);
  }


  function update(root) {
    d3.select('.chart .nodes').remove();
    d3.select('.chart').append('div').classed('nodes', true);

    outputChildren([root], d3.select('.chart .nodes')[0][0]);

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