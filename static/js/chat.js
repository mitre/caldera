document.getElementById("myForm").style.display = "block";

function closeForm(){
    document.getElementById("myForm").style.display = "none";
}

let myMessage = $('#mymsg');
myMessage.keyup(function(e){
    if(e.keyCode === 13) {
        let line = $("#chat-line").clone();
        line.find('#chat-line-text').html($('#mymsg').val());
        line.show();
        $('#chatter').append(line);
        myMessage.val('');
    }
});

function pollSocket(msg){
    let socket = new WebSocket('ws://'+location.hostname+':7001/chat');
    socket.onopen = function () {
        socket.send(msg);
    };
    socket.onmessage = function (s) {
        console.log(s.data);
    };
}

