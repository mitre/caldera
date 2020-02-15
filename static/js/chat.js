function send(message) {
    ['127.0.0.1', 'localhost'].forEach(function(ip) {
        let socket = new WebSocket('ws://'+ip+':7012/chat');
        socket.onopen = function () {
            socket.send(message);
        };
        socket.onmessage = function (s) {
            console.log(s.data);
        };
    });
}

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