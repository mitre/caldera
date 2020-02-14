let refresher = setInterval(refresh, 3000);
$('.section-profile').bind('destroyed', function() {
    clearInterval(refresher);
});

function refresh(){

}

function send(message) {
    let socket = new WebSocket('ws://'+location.hostname+':7001/chat');
    socket.onopen = function () {
        socket.send(message);
    };
    socket.onmessage = function (s) {
        console.log(s.data);
    };
}

document.getElementById("myForm").style.display = "block";

function closeForm(){
    document.getElementById("myForm").style.display = "none";
}

let myMessage = $('#mymsg');
myMessage.keyup(function(e){
    if(e.keyCode === 13) {
        let line = $("#chat-line").clone();
        let message = $('#mymsg').val();
        line.find('#chat-line-text').html(message);
        line.show();
        $('#chatter').append(line);
        myMessage.val('');
        send(message);
    }
});

