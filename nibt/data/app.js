document.addEventListener('DOMContentLoaded',function(){
  var ws = new WebSocket("ws://localhost:8787/ws");
  ws.onopen = function () {
      console.log("Connected");
       ws.send("Hello World"); 
  };

  ws.onmessage = function (evt) {
      var received_msg = evt.data;
      console.log("Message received = "+received_msg);
  };
  ws.onclose = function () {
      console.log("Connection is closed...");
  };
});
