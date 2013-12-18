
// uses http://docs.jquery.com/Plugins/Autocomplete

// ...............................................
// This function was copied from jquery.autocomplete.js because I could not 
// find an easier way to call the original parsing function.
function parse(data) {
    var parsed = [];
    var rows = data.split("\n");
    for (var i=0; i < rows.length; i++) {
        var row = $.trim(rows[i]);
        if (row) {
            row = row.split("|");
            parsed[parsed.length] = {
                data: row,
                value: row[0],
                result: row[0]
            };
        }
    }
    return parsed;
};
// ...............................................

function parse_results(data) {
    /*
     * The autocomplete widget expects the input data as "foo|bar" with one 
     * item per line. The agilo search plugin returns HTML so some 
     * preprocessing will transform the data into the expected format.
     */
    var raw_html = data.replace(/^<!DOCTYPE[^>]+>/, "");
    var data_splitter = /<li\s+id="(\d+)"\s*>(.*?)<\/li>/g;
    var resultstring = "";
    var results = new Array();
    var match;
    while ((match = data_splitter.exec(raw_html))) {
        resultstring += match[2] + "|" + match[1] + "\n";
    }
    return parse(resultstring);
}

function get_form_token(form) {
    for (var i=0; i<form.elements.length; i++) {
        if (form.elements[i].name == '__FORM_TOKEN') {
            return form.elements[i].value;
        }
    }
    return null;
}

function get_url_parameters() {
    return {"__FORM_TOKEN": get_form_token(document.forms.create_link), 
            "id": ticket_id
           };
}

