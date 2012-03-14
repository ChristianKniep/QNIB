<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Frameset//EN"
   "http://www.w3.org/TR/html4/frameset.dtd">
<html>
<head>
  <link rel="stylesheet" href="css/combined.css"/> 
  <script>
    function timedRefresh(timeoutPeriod) {
        setTimeout("location.reload(true);",timeoutPeriod);
    }
  </script>
<title>Frameset mit Sitemap</title>
</head>
<body id="index" onload="JavaScript:timedRefresh(10000);"> 
    <div id="mainheader">
        <!-- QNIB - <b>Q</b>ualified <b>N</b>etworking with <b>I</b>nfini<b>B</b>and -->
        IBPM - <b>I</b>nfini<b>B</b>and <b>P</b>erformance <b>M</b>onitoring
    </div>
    <div id="map">
      <ul id="simple-navi">
        <li <?php if (($_GET['map']=="root_plain") OR (empty ($_GET['map']))) { echo 'class="active"'; } ?>><a href="index.php?map=root_plain">TOPOLOGY MAP</a></li>
        <li <?php if ($_GET['map']=="root_perf") { echo 'class="active"'; } ?>><a href="index.php?map=root_perf">PERFORMANCE MAP</a></li>
      </ul>
      <?php
      if ( empty ($_GET['map']) ) {
        include '/srv/www/qnib/root_plain.svg' ;
      } else {
        include '/srv/www/qnib/'.$_GET['map'].'.svg' ;
        }
      ?>
    </div>
    <div id="node_details">
      <?php
      if ( empty ($_GET['node_details']) ) {
        include '/srv/www/qnib/node104.html' ;
      } else {
        include '/srv/www/qnib/'.$_GET['node_details'].'.html' ;
      }
      ?>
    </div>
    <div id="clear"></div>
    <div id="legend">
      <div id="legend_body">
            <table id=legend>
                <tr>
                    <td id=legend>
                        <table id=logs>
                            <tr id="logs_header">
                                <th>Time</th>
                                <th>Target</th>
                                <th>Type</th>
                                <th>Status</th>
                                <th>Description</th>
                            </tr>
                            <?php include 'logs.html'; ?>
                        </table>
                    </td>
                    <td id=legend_desc>
                        The colors indicates how utilized the link / local the switchtraffic is.
                    </td>
                    <td id=legend_space></td>
                    <td id=legend>
                        <table id=legend_color>
                            <tr>
                                <td bgcolor="#8080ff" id="legend_color"></td>
                                <td id="legend_color">0-9%</td>
                            </tr>
                            <tr>
                                <td bgcolor="#ae80ff"></td>
                                <td>10-19%</td>
                            </tr>
                            <tr>
                                <td bgcolor="#c580ff"></td>
                                <td>20-29%</td>
                            </tr>        
                            <tr>
                                <td bgcolor="#dc80ff"></td>
                                <td>30-39%</td>
                            </tr>        
            
                            <tr>
                                <td bgcolor="#f380ff"></td>
                                <td>40-49%</td>
                            </tr>        
                        </table>
                    </td>
                    <td>
                        <table id=legend_color>
                            <tr>
                                <td bgcolor="#ff80f3" id="legend_color"></td>
                                <td id="legend_color">50-59%</td>
                            </tr>        
            
                            <tr>
                                <td bgcolor="#ff80dc"></td>
                                <td>60-69%</td>
                            </tr>        
                            <tr>
                                <td bgcolor="#ff80c5"></td>
                                <td>70-79%</td>
                            </tr>        
                            <tr>
                                <td bgcolor="#ff80ae"></td>
                                <td>80-89%</td>
                            </tr>        
                            <tr>
                                <td bgcolor="#ff8097"></td>
                                <td>90-99%</td>
                            </tr>        
                            <tr>
                                <td bgcolor="#ff8080"></td>
                                <td>100%</td>
                            </tr>        
                        </table>
                    </td>
                </tr>
            </table>
      </div>
    </div>
</body>
</html>