howmany_polygons = 0
colors = ['#f5725b77', '#7593e077']
polygons = []

function closePolygon() {
  svg.select('g.drawPoly').remove();
  var g = svg.append('g');
  g.append('polygon')
    .attr('points', points)
    .style('fill', getRandomColor());
  for (var i = 0; i < points.length; i++) {
    var circle = g.selectAll('circles')
      .data([points[i]])
      .enter()
      .append('circle')
      .attr('cx', points[i][0])
      .attr('cy', points[i][1])
      .attr('r', 4)
      .attr('fill', '#FDBC07')
      .attr('stroke', '#000')
      .attr('is-handle', 'true')
      .style({
        cursor: 'move'
      })
      .call(dragger);
  }
  polygons.push([])
  p = polygons[polygons.length - 1]
  for (var i = 0; i < points.length; i++) {
    p.push(points[i]);
  }

  points.splice(0);
  drawing = false;
  howmany_polygons += 1;
}

function handleDrag() {
  if (drawing) return;
  var dragCircle = d3.select(this),
    newPoints = [],
    circle;
  dragging = true;
  var poly = d3.select(this.parentNode).select('polygon');
  var circles = d3.select(this.parentNode).selectAll('circle');
  dragCircle
    .attr('cx', d3.event.x)
    .attr('cy', d3.event.y);
  for (var i = 0; i < circles[0].length; i++) {
    circle = d3.select(circles[0][i]);
    newPoints.push([circle.attr('cx'), circle.attr('cy')]);
  }
  poly.attr('points', newPoints);
}

function getRandomColor() {
  console.log(howmany_polygons)
  if (howmany_polygons < colors.length) {
    return colors[howmany_polygons];
  } else {
    var letters = '0123456789ABCDEF'.split('');
    var color = '#';
    for (var i = 0; i < 6; i++) {
      color += letters[Math.floor(Math.random() * 16)];
    }
    color += '77';
    return color;
  }
}

function drawPoly(polygons) {
  for (var j = 0; j < polygons.length; j++) {
    points = polygons[j];
    g = svg.append('g').attr('class', 'drawPoly');
    var polyline = g.append('polyline').attr('points', points)
      .style('fill', 'none')
      .attr('stroke', '#000');
    for (var i = 0; i < points.length; i++) {
      g.append('circle')
        .attr('cx', points[i][0])
        .attr('cy', points[i][1])
        .attr('r', 4)
        .attr('fill', 'yellow')
        .attr('stroke', '#000')
        .attr('is-handle', 'true')
        .style({
          cursor: 'pointer'
        });
    }
    var g = svg.append('g');
    g.append('polygon')
      .attr('points', points)
      .style('fill', getRandomColor());
    for (var i = 0; i < points.length; i++) {
      var circle = g.selectAll('circles')
        .data([points[i]])
        .enter()
        .append('circle')
        .attr('cx', points[i][0])
        .attr('cy', points[i][1])
        .attr('r', 4)
        .attr('fill', '#FDBC07')
        .attr('stroke', '#000')
        .attr('is-handle', 'true')
        .style({
          cursor: 'move'
        })
    }
    howmany_polygons += 1;

  }
}
