var validInitialForm = function() {
	
	var isValid = true;
	
	var mt = $('#mediatype').val();
	var zip = $('#zipcode').val();
	
	if (!zip.match(/\d{5}/)) {
		alert('A valid 5 digit zipcode is required');
		isValid = false;
	}
	
	if (!mt) {
		alert('Media Type is required');
		isValid = false;
	}
	
	return isValid;
	
};

var validFinalForm = function() {
	
	var isValid = true;
	
	var mt = $('#mediatype').val();
	
	
	if (mt == 'television') {
		
		var channel = $('#tv_channel').val();
		var provider = $('#tv_provider').val();

		if (provider == '---' || !provider) {
			alert('Television provider is required');
			isValid = false;
		}
		
		if (!channel) {
			alert('Television channel is required');
			isValid = false;
		}
		
	} else if (mt == 'radio') {
		
		var callsign = $('#radio_callsign').val();

		if (!callsign) {
			alert('Radio station is required');
			isValid = false;
		}
		
	}
	
	return isValid;
	
};

var zipcodeChange = function() {

	var zip = $('#zipcode').val();

	if (zip.match(/\d{5}/)) {
		
		$.getJSON('/stations/tv?zipcode=' + zip, function(data) {
		
			var sel = $('#tv_channel');
			var html = '';
			for (var i = 0; i < data.length; i++) {
				html += '<option value="' + data[i].id + '">' + data[i].name + '</option>';
			}
			html += '<option value="other">Other</option>';
			sel.html(html);
		
		});
		
	}
	
};

var mediatypeChange = function() {
	var mt = $('#mediatype').val();
	$('form#reportAd fieldset.final fieldset').slideUp();
	$('form#reportAd fieldset.final fieldset.' + mt).slideDown();
};

$().ready(function() {
	
	$('form#reportAd input#zipcode').bind('change', zipcodeChange);
	
	$('form#reportAd fieldset.initial button').click(function() {
		
		if (validInitialForm()) {
				
			$('fieldset.initial .continueBtn').slideUp();
			$('fieldset.final').slideDown();
			
		}
		
		return false;
		
	});
	
	$('form#reportAd select#tv_channel').bind('change', function() {
		var channel = $(this).val();
		if (channel == 'other') {
			$('#tv_channel_other').show();
		} else {
			$('#tv_channel_other').hide();
		}
	});
	
	$('form#reportAd select#mediatype').bind('change', mediatypeChange);
	
	$('form#reportAd').submit(function() {
		return validInitialForm() && validFinalForm();
	});
	
	zipcodeChange();
	mediatypeChange();
	
});