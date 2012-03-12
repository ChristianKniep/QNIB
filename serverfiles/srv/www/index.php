<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"
   "http://www.w3.org/TR/html4/frameset.dtd">
<html>
<head>
  <link rel="stylesheet" href="css/index.css"/>
  <script>
    function timedRefresh(timeoutPeriod) {
        setTimeout("location.reload(true);",timeoutPeriod);
    }
  </script>
<title>Frameset mit Sitemap</title>
</head>
<body onload="JavaScript:timedRefresh(5000);"> 
    <div id="map">
      <?php include '/srv/www/qnib/root_plain.svg' ; ?>
    </div>
      <?php include '/srv/www/qnib/'.$_GET['node_details'].'.html' ; ?>
    <div id="node_details"></div>
    <div id="clear"></div>
    <div id="legend">
      Legende
    </div>
</body>
</html>