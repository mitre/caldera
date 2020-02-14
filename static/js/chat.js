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