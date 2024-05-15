if(!window.dash_clientside) {window.dash_clientside = {};}
window.dash_clientside.clientside = {
    scroll_to_bottom: function(value) {
        setTimeout(function() {
            var element = document.getElementById('uart');
            if (element) {
                element.scrollTop = element.scrollHeight;
            }
            element = document.getElementById('commander');
            if (element) {
                element.scrollTop = element.scrollHeight;
            }
            element = document.getElementById('cdi');
            if (element) {
                element.scrollTop = element.scrollHeight;
            }
        }, 0);
        return null;
    }
}
