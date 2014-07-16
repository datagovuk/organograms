(function() {
  function ready() {
    // console.log('ready!');
  }


  // function personIcons(i) {
  //   var single = '<i class="fa fa-male group-1"></i>';
  //   var group10 = '<i class="fa fa-male group-10"></i>';
  //   var group100 = '<i class="fa fa-male group-100"></i>';
  //   ret = '';
  //   if(i <= 10) {
  //     for(var ii=0; ii<i; ii++)
  //       ret += single;
  //   } else if(i <= 100) {
  //     var numGroups = Math.floor(i / 10);
  //     var numSingle = i % 10;
  //     for(var ii=0; ii<numGroups; ii++)
  //       ret += group10;
  //     for(var ii=0; ii<numSingle; ii++)
  //       ret += single;
  //   } else {
  //     var num100Groups = Math.floor(i / 100);
  //     for(var ii=0; ii<num100Groups; ii++)
  //       ret += group100;

  //     var remainder = i % 100;
  //     var num10Groups = Math.floor(remainder / 10);
  //     for(var ii=0; ii<num10Groups; ii++)
  //       ret += group10;

  //     remainder = remainder % 10;
  //     for(var ii=0; ii<remainder; ii++)
  //       ret += single;
  //   }

  //   return ret;
  // }


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

  function outputNode(node, element) {
    // Recursively output node into element

    var people = '';
    if(node.FTE !== undefined)
      people = peopleIcons(node.FTE);

    var newNode = d3.select(element)
      .append('div')
      .classed('node', true)
      .html(node.name + ' ' + people);

    if(node.children !== undefined) {
      var children = newNode.append('div')
        .classed('children', true);
      _.each(node.children, function(c) {
        outputNode(c, children[0][0]);
      });
    }


  }

  function update(root) {
    d3.select('.chart .nodes').remove();
    d3.select('.chart').append('div').classed('nodes', true);

    outputNode(root, d3.select('.chart .nodes')[0][0]);
  }



  function orgSelect(file) {
    d3.json('../wrangling/output/orgs/' + file + '.json', function(err, json) {
      update(json);
    });
    // console.log('load', file);
  }

  dgvis.menu.init(ready, orgSelect);


})();