$(document).ready(function() {
    $('#account-id').change(function() {

        var accountIdRaw = $('#account-id').val();
        console.log(accountId);
        var accountId = accountIdRaw.slice(0, 9);

        // Make Ajax Request and expect JSON-encoded data
        $.getJSON(
            '/get-properties' + '/' + accountId,
            function(data) {

                // Remove old options
                $('#property-id').find('option').remove();
                // Add new items
                $.each(data, function(key, val) {
                    var option_item = '<option value="' + val + '">' + val + '</option>'
                    $('#property-id').append(option_item);
                });
            }
        );
    });
});

$(document).ready(function() {
    $('#account-id').click(function() {

        var accountIdRaw = $('#account-id').val();
        console.log(accountId);
        var accountId = accountIdRaw.slice(0, 9);

        // Make Ajax Request and expect JSON-encoded data
        $.getJSON(
            '/get-properties' + '/' + accountId,
            function(data) {

                // Remove old options
                $('#property-id').find('option').remove();
                // Add new items
                $.each(data, function(key, val) {
                    var option_item = '<option value="' + val + '">' + val + '</option>'
                    $('#property-id').append(option_item);
                });
            }
        );
    });
});

$(document).ready(function() {
    $('#property-id').change(function() {

        var propertyIdRaw = $('#property-id').val();
        propertyIdRaws = propertyIdRaw.split(" ");
        console.log(propertyIdRaws[0].trim());
        var propertyId = propertyIdRaws[0].trim();
        console.log(propertyId);

        // Make Ajax Request and expect JSON-encoded data
        $.getJSON(
            '/get-views' + '/' + propertyId,
            function(data) {

                // Remove old options
                $('#view-id').find('option').remove();
                console.log(data)
                    // Add new items
                $.each(data, function(key, val) {
                    var option_item = '<option value="' + val + '">' + val + '</option>'
                    $('#view-id').append(option_item);
                });
            }
        );
    });
});

$(document).ready(function() {
    $('#property-id').click(function() {

        var propertyIdRaw = $('#property-id').val();
        propertyIdRaws = propertyIdRaw.split(" ");
        console.log(propertyIdRaws[0].trim());
        var propertyId = propertyIdRaws[0].trim();
        console.log(propertyId);

        // Make Ajax Request and expect JSON-encoded data
        $.getJSON(
            '/get-views' + '/' + propertyId,
            function(data) {

                // Remove old options
                $('#view-id').find('option').remove();
                console.log(data)
                    // Add new items
                $.each(data, function(key, val) {
                    var option_item = '<option value="' + val + '">' + val + '</option>'
                    $('#view-id').append(option_item);
                });
            }
        );
    });
});