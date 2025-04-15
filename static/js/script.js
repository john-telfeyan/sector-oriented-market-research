// Ensure the DOM is fully loaded before execution
$(document).ready(function() {
    // Auto-dismiss flash messages after 5 seconds
    setTimeout(function() {
      $(".alert-dismissible").fadeOut("slow");
    }, 5000);
  
    // Adjust Plotly chart on window resize
    function resizePlot() {
      var containerWidth = $("#plotly-chart").parent().width();
      if (containerWidth && typeof Plotly !== 'undefined' && $("#plotly-chart").data("plotly")) {
        Plotly.relayout("plotly-chart", { width: containerWidth });
      }
    }
    
    $(window).resize(function() {
      resizePlot();
    });
    resizePlot();
  
    // Add click event listener to the Plotly chart element (if present)
    var plotDiv = document.getElementById('plotly-chart');
    if (plotDiv) {
      plotDiv.on('plotly_click', function(data) {
        // Get the first clicked point (if multiple exist)
        var point = data.points[0];
        var ticker = point.customdata;  // customdata holds the ticker symbol
        if (ticker) {
          // Open the corresponding Yahoo Finance page in a new tab
          window.open("https://finance.yahoo.com/quote/" + ticker + "/", '_blank');
        }
      });
    }
  });
  