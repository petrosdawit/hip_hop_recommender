$( document ).ready(function() {
  $('inputField').keyup(function() {
    if(keycode!=38 || keycode!=40){
      $('.song_class').empty();
      suggestions = {{trie}}.autocomplete($('inputField').val())[:10]
      string = '<datalist id='song_names'>'
      for (var song_info in suggestions){
        string += '<option value= "'
        string += song_info[1]
        string += ' by '
        string += song_info[2]
        string += '">'
      }
      string += '</datalist>'
      $('.song_class').append(string)
    }
  });
});
